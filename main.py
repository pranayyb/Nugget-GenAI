import os
import sys
import json
import time
import random
import logging
import warnings
import traceback
import streamlit as st
from langchain import hub
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("nugget_assistant.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("nugget_assistant")

warnings.filterwarnings("ignore")
load_dotenv()


class RateLimitException(Exception):
    pass


class APIConnectionException(Exception):
    pass


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RateLimitException),
    reraise=True,
)
def call_groq_with_retry(llm, *args, **kwargs):
    try:
        return llm(*args, **kwargs)
    except Exception as e:
        error_str = str(e).lower()
        if (
            "rate limit" in error_str
            or "too many requests" in error_str
            or "429" in error_str
        ):
            logger.warning(f"Rate limit hit, retrying: {str(e)}")
            raise RateLimitException(f"Rate limit exceeded: {str(e)}")
        else:
            raise


try:
    logger.info("Starting Nugget AI Assistant")
    st.set_page_config(page_title="Nugget AI Assistant", layout="wide")
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY environment variable not found")
        st.error(
            "Missing GROQ_API_KEY environment variable. Please set it and restart the application."
        )
    model_name = "llama-3.3-70b-versatile"
    persist_directory = "./chroma_db"
    collection_name = "restaurants"

    if not os.path.exists(persist_directory):
        logger.warning(f"ChromaDB directory not found at {persist_directory}")
        st.warning(
            f"ChromaDB directory not found at {persist_directory}. Make sure your database is properly initialized."
        )

    logger.info(f"Using model: {model_name}")
    logger.info(f"Using ChromaDB collection: {collection_name}")

except Exception as e:
    logger.critical(f"Error during app initialization: {str(e)}")
    logger.critical(traceback.format_exc())
    st.error(f"Failed to initialize application: {str(e)}")
    st.stop()

with st.sidebar:
    st.title("Nugget AI Assistant")
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""
    sample_queries = [
        "What Italian restaurants are nearby?",
        "Tell me about vegan options at local cafes",
        "What's the price range for sushi restaurants?",
        "Best brunch spots open on weekends?",
    ]

    for query in sample_queries:
        if st.button(f"{query}", use_container_width=True):
            logger.info(f"Sample query selected: {query}")
            st.session_state.sample_query = query
            st.rerun()
    if st.button("Clear Chat History", type="primary"):
        logger.info("Chat history cleared by user")
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()

    # # Add a rate limit info box
    # st.sidebar.markdown("---")
    # st.sidebar.markdown("### API Status")
    # if "rate_limit_hits" not in st.session_state:
    #     st.session_state.rate_limit_hits = 0
    # st.sidebar.metric("Rate Limit Events", st.session_state.rate_limit_hits)
    # if st.sidebar.button("Reset API Stats"):
    #     st.session_state.rate_limit_hits = 0
    #     st.rerun()

st.markdown("## Your own Restro Buddy!")
st.markdown("Ask about restaurants, cuisines, dishes, dietary options, and more!")

if "chat_history" not in st.session_state:
    logger.info("Initializing chat history")
    st.session_state.chat_history = []

chat_container = st.container()
with chat_container:
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])

    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            welcome_name = (
                f", {st.session_state.user_name}" if st.session_state.user_name else ""
            )
            st.write(
                f"Hello{welcome_name}! I'm your Nugget AI Assistant. How may I help you with your dining questions today?"
            )


class RateLimitAwareGroq(ChatGroq):
    def __call__(self, *args, **kwargs):
        try:
            return call_groq_with_retry(super().__call__, *args, **kwargs)
        except RateLimitException as e:
            st.session_state.rate_limit_hits += 1
            logger.error(f"Rate limit hit after retries: {str(e)}")
            raise


def initialize_rag_system(groq_key, persist_dir, collection, model):
    try:
        logger.info("Initializing RAG system")
        logger.info(f"Loading embeddings model")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        logger.info(f"Connecting to ChromaDB at {persist_dir}")
        try:
            searcher = Chroma(
                persist_directory=persist_dir,
                collection_name=collection,
                embedding_function=embeddings,
            )
            logger.info(f"Successfully connected to ChromaDB collection: {collection}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"ChromaDB connection failed: {str(e)}")

        logger.info(f"Initializing Groq LLM with model {model}")
        try:
            llm = RateLimitAwareGroq(api_key=groq_key, model=model)
            logger.info("Successfully initialized Groq LLM")
        except Exception as e:
            logger.error(f"Failed to initialize Groq LLM: {str(e)}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Groq LLM initialization failed: {str(e)}")

        logger.info("Setting up contextual question processing")
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, just "
            "reformulate it if needed and otherwise return it as is."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        logger.info("Setting up retriever")
        retriever = searcher.as_retriever()
        history_aware_retriever = create_history_aware_retriever(
            llm, retriever, contextualize_q_prompt
        )

        logger.info("Setting up question-answering chain")
        qa_system_prompt = (
            "You are a helpful restaurant assistant specializing in dining recommendations. "
            "Use the retrieved context and conversation history to guide users about restaurants, "
            "menus, prices, cuisines, dietary options, reservations, and dining experiences. "
            "Provide specific details about restaurant locations, popular dishes, price ranges, "
            "and special offerings when available in the context. "
            "If users share dietary restrictions or preferences, remember these and tailor your recommendations accordingly. "
            "If the user shares their name, remember it and personalize your responses. "
            "When information is not available in the context, acknowledge this and offer to help with related questions."
            "\n\n"
            "{context}"
        )
        qa_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", qa_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
        rag_chain = create_retrieval_chain(
            history_aware_retriever, question_answer_chain
        )

        def search_wikipedia(query):
            logger.info(f"Searching Wikipedia for: {query}")
            try:
                from wikipedia import summary

                result = summary(query, sentences=2)
                logger.info("Wikipedia search successful")
                return result
            except Exception as e:
                logger.warning(f"Wikipedia search failed: {str(e)}")
                return "I couldn't find any information on that."

        logger.info("Setting up tools")
        tools = [
            Tool(
                name="Answer Question through RAG",
                func=lambda input, **kwargs: rag_chain.invoke(
                    {
                        "input": input,
                        "chat_history": kwargs.get("chat_history", []),
                    }
                ),
                description="useful for when you need to answer questions about the context",
            ),
            Tool(
                name="wikipedia",
                func=search_wikipedia,
                description="useful when you cannot find answers about the context",
            ),
        ]

        logger.info("Setting up agent")
        react_docstore_prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=react_docstore_prompt,
        )

        logger.info("Setting up agent executor")
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=tools,
            handle_parsing_errors=True,
            verbose=False,
        )

        logger.info("RAG system initialization complete")
        return agent_executor

    except Exception as e:
        logger.error(f"RAG system initialization failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise


food_spinner_messages = [
    "Simmering thoughts...",
    "Kneading ideas...",
    "Sautéing information...",
    "Marinating knowledge...",
    "Whisking up answers...",
    "Dicing data...",
    "Stirring insights...",
    "Blending expertise...",
    "Grilling facts...",
    "Sprinkling wisdom...",
    "Baking responses...",
    "Garnishing answers...",
    "Tasting possibilities...",
    "Seasoning replies...",
    "Caramelizing concepts...",
    "Brewing intelligence...",
    "Braising knowledge...",
    "Flambéing ideas...",
    "Plating insights...",
    "Chef's special coming up...",
]


def save_chat_history():
    """Save chat history to a file."""
    try:
        with open("chat_history.json", "w") as f:
            json.dump(st.session_state.chat_history, f)
        logger.info("Chat history saved successfully")
    except Exception as e:
        logger.error(f"Failed to save chat history: {str(e)}")


def load_chat_history():
    try:
        if os.path.exists("chat_history.json"):
            with open("chat_history.json", "r") as f:
                st.session_state.chat_history = json.load(f)
            logger.info("Chat history loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load chat history: {str(e)}")
        st.session_state.chat_history = []


if "chat_history_loaded" not in st.session_state:
    load_chat_history()
    st.session_state.chat_history_loaded = True


def generate_fallback_response(user_query):
    generic_responses = [
        "I'm having trouble connecting to my knowledge base right now. Could you try asking again in a moment?",
        "It seems like we're experiencing some technical difficulties. Let me try to help with what I know: restaurants generally offer a variety of cuisines and price points. Could you provide more details about what you're looking for?",
        "I apologize, but I'm having trouble accessing the restaurant database at the moment. Is there something specific about dining options you'd like to know?",
        "We're experiencing a high volume of requests right now. Would you mind trying your question again in a few moments?",
    ]
    if any(word in user_query.lower() for word in ["italian", "pasta", "pizza"]):
        return "I'm having trouble connecting to my knowledge base, but I can tell you're interested in Italian cuisine. Italian restaurants typically offer dishes like pasta, pizza, risotto, and many feature antipasti appetizers. Would you like me to try finding specific information once the connection is restored?"
    if any(word in user_query.lower() for word in ["vegan", "vegetarian", "plant"]):
        return "While I'm experiencing connection issues, I notice you're interested in plant-based options. Many restaurants now offer dedicated vegan/vegetarian menus or can modify dishes to accommodate dietary preferences. Would you like to know about specific plant-based dishes once I'm back online?"
    if any(
        word in user_query.lower()
        for word in ["price", "expensive", "cheap", "cost", "budget"]
    ):
        return "I see you're asking about pricing. While I can't access specific restaurant prices right now due to connection issues, restaurants typically range from budget-friendly options to high-end dining experiences. I'd be happy to provide more specific information once the connection is restored."
    return random.choice(generic_responses)


if "sample_query" in st.session_state:
    user_query = st.session_state.sample_query
    logger.info(f"Processing sample query: {user_query}")
    del st.session_state.sample_query
else:
    user_query = st.chat_input("Ask about restaurants, food, or dining...")

if user_query:
    logger.info(f"User query: {user_query}")
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)
    with st.chat_message("assistant"):
        spinner_message = random.choice(food_spinner_messages)
        with st.spinner(spinner_message):
            formatted_history = []
            for msg in st.session_state.chat_history[:-1]:
                if msg["role"] == "user":
                    formatted_history.append(("human", msg["content"]))
                else:
                    formatted_history.append(("ai", msg["content"]))

            try:
                logger.info("Initializing agent executor")
                agent_executor = initialize_rag_system(
                    groq_api_key,
                    persist_directory,
                    collection_name,
                    model_name,
                )
                time.sleep(0.5)
                logger.info("Invoking agent executor")
                response = agent_executor.invoke(
                    {"input": user_query, "chat_history": formatted_history}
                )
                assistant_response = response["output"]
                logger.info("Successfully generated response")
                st.write(assistant_response)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": assistant_response}
                )
                save_chat_history()

            except RateLimitException as e:
                logger.error(f"Rate limit exceeded after retries: {str(e)}")
                st.session_state.rate_limit_hits += 1
                fallback_response = generate_fallback_response(user_query)
                fallback_response += "\n\n(Note: I'm currently experiencing rate limits with my AI service. Please try again in a minute.)"
                st.write(fallback_response)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": fallback_response}
                )

            except Exception as e:
                logger.error(f"Error while processing query: {str(e)}")
                logger.error(traceback.format_exc())
                error_message = f"I encountered an error while processing your request. Please try again or rephrase your question. (Error: {str(e)})"
                st.error(error_message)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": error_message}
                )
