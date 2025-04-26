import random
import os
import streamlit as st
import logging
import json

logger = logging.getLogger("nugget_assistant")


def save_chat_history():
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
