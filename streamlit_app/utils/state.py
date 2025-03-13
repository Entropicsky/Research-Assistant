"""
State management utilities for the Streamlit app.

This module provides functions for managing session state, including
conversation history, project selection, and UI state.
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Union
import json
from datetime import datetime
from .logger import get_logger

# Get module logger
logger = get_logger("state")

def init_session_state():
    """
    Initialize all required session state variables if they don't exist.
    Should be called at the start of the app.
    """
    # Core app state
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
    
    # Chat state
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    if "selected_project" not in st.session_state:
        st.session_state.selected_project = None
    
    if "last_selected_project_index" not in st.session_state:
        st.session_state.last_selected_project_index = None
    
    # UI state
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    
    if "show_sources" not in st.session_state:
        st.session_state.show_sources = True
    
    if "show_inactive_projects" not in st.session_state:
        st.session_state.show_inactive_projects = False
    
    # Model settings
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "gpt-4o-mini"
    
    if "web_search_enabled" not in st.session_state:
        st.session_state.web_search_enabled = False
    
    # Real-time state
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    
    if "log_history" not in st.session_state:
        st.session_state.log_history = []

# Conversation History Management
def add_user_message(content: str):
    """Add a user message to the conversation history."""
    st.session_state.conversation_history.append({
        "role": "user",
        "content": content,
        "timestamp": datetime.now().isoformat()
    })

def add_assistant_message(content: str, citations: List[str] = None):
    """Add an assistant message to the conversation history."""
    st.session_state.conversation_history.append({
        "role": "assistant",
        "content": content,
        "citations": citations or [],
        "timestamp": datetime.now().isoformat()
    })

def get_conversation_messages():
    """Get the current conversation history."""
    return st.session_state.conversation_history

def clear_conversation():
    """Clear the conversation history."""
    st.session_state.conversation_history = []

def get_openai_messages():
    """Format conversation history for OpenAI API calls."""
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.conversation_history
    ]

# Project Management
def set_selected_project(project: Dict[str, Any], index: int = None):
    """Set the selected project and reset conversation."""
    st.session_state.selected_project = project
    st.session_state.last_selected_project_index = index
    clear_conversation()

def get_selected_project():
    """Get the currently selected project."""
    return st.session_state.selected_project

def get_vector_store_id():
    """Get the vector store ID of the selected project."""
    if st.session_state.selected_project:
        return st.session_state.selected_project.get("openai_integration", {}).get("vector_store", {}).get("id")
    return None

# UI State Management
def toggle_debug_mode():
    """Toggle debug mode on/off."""
    st.session_state.debug_mode = not st.session_state.debug_mode

def is_debug_mode():
    """Check if debug mode is enabled."""
    return st.session_state.debug_mode

def toggle_show_sources():
    """Toggle show sources on/off."""
    st.session_state.show_sources = not st.session_state.show_sources

def should_show_sources():
    """Check if sources should be shown."""
    return st.session_state.show_sources

def set_show_sources(value: bool):
    """Set whether sources should be shown."""
    st.session_state.show_sources = value

def toggle_show_inactive_projects():
    """Toggle show inactive projects on/off."""
    st.session_state.show_inactive_projects = not st.session_state.show_inactive_projects

def should_show_inactive_projects():
    """Check if inactive projects should be shown."""
    return st.session_state.show_inactive_projects

def set_show_inactive_projects(value: bool):
    """Set whether inactive projects should be shown."""
    st.session_state.show_inactive_projects = value

# Model Settings Management
def set_model(model_name: str) -> None:
    """Set the selected model."""
    st.session_state.model = model_name

def get_model() -> str:
    """Get the currently selected OpenAI model."""
    if "model" not in st.session_state:
        from .openai_client import get_available_models
        
        # Set default model, preferring gpt-4o-mini or the first available model
        models = get_available_models()
        model_ids = [m["id"] for m in models]
        
        if "gpt-4o-mini" in model_ids:
            default_model = "gpt-4o-mini"
        elif len(model_ids) > 0:
            default_model = model_ids[0]  # Use first available model
        else:
            default_model = "gpt-4o-mini"  # Fallback if no models available (shouldn't happen)
            
        st.session_state.model = default_model
    
    return st.session_state.model

def toggle_web_search():
    """Toggle web search on/off."""
    st.session_state.web_search_enabled = not st.session_state.web_search_enabled

def is_web_search_enabled():
    """Check if web search is enabled."""
    return st.session_state.web_search_enabled

# Generation State Management
def set_generating(is_generating: bool):
    """Set the generation state."""
    st.session_state.is_generating = is_generating

def is_generating():
    """Check if a response is currently being generated."""
    return st.session_state.is_generating

# Export/Import Functionality
def export_conversation(filename: Optional[str] = None):
    """Export the current conversation to a JSON file."""
    data = {
        "conversation": st.session_state.conversation_history,
        "project": st.session_state.selected_project,
        "model": st.session_state.selected_model,
        "timestamp": datetime.now().isoformat()
    }
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = "unknown"
        if st.session_state.selected_project:
            project_name = st.session_state.selected_project.get("parameters", {}).get("topic", "unknown")
            project_name = project_name.replace(" ", "_").lower()[:20]
        filename = f"conversation_{project_name}_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    return filename

def import_conversation(data: Dict[str, Any]):
    """Import a conversation from a data dictionary."""
    if "conversation" in data:
        st.session_state.conversation_history = data["conversation"]
    
    if "project" in data:
        st.session_state.selected_project = data["project"]
    
    if "model" in data:
        st.session_state.selected_model = data["model"] 