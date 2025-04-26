import os
import random
import warnings
import streamlit as st
from langchain import hub
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_astradb import AstraDBVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain

warnings.filterwarnings("ignore")
load_dotenv()
st.set_page_config(page_title="Nugget AI Assistant", layout="wide")

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
            st.session_state.sample_query = query
            st.rerun()
    if st.button("Clear Chat History", type="primary"):
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()

st.markdown("## Your own Restro Buddy!")
st.markdown("Ask about restaurants, cuisines, dishes, dietary options, and more!")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

groq_api_key = os.getenv("GROQ_API_KEY")
astra_db_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
astra_db_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
model_name = "llama-3.3-70b-versatile"
collection_name = "nugget_ai"

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


def initialize_rag_system(groq_key, astra_token, astra_endpoint, collection, model):
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    searcher = AstraDBVectorStore(
        embedding=embeddings,
        collection_name=collection,
        api_endpoint=astra_endpoint,
        token=astra_token,
    )
    llm = ChatGroq(api_key=groq_key, model=model)
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
    retriever = searcher.as_retriever()
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
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
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def search_wikipedia(query):
        try:
            from wikipedia import summary

            return summary(query, sentences=2)
        except:
            return "I couldn't find any information on that."

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
    react_docstore_prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_docstore_prompt,
    )
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        handle_parsing_errors=True,
        verbose=False,
    )
    return agent_executor


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

if "sample_query" in st.session_state:
    user_query = st.session_state.sample_query
    del st.session_state.sample_query
else:
    user_query = st.chat_input("Ask about restaurants, food, or dining...")

if user_query:
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
                agent_executor = initialize_rag_system(
                    groq_api_key,
                    astra_db_token,
                    astra_db_endpoint,
                    collection_name,
                    model_name,
                )
                response = agent_executor.invoke(
                    {"input": user_query, "chat_history": formatted_history}
                )
                assistant_response = response["output"]
                st.write(assistant_response)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": assistant_response}
                )
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": error_message}
                )
