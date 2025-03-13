"""
Chat Interface Component for the Streamlit app.

This module provides an enhanced chat interface with support for citations,
streaming, and better visual design.
"""

import streamlit as st
import time
import html
from typing import List, Dict, Any, Optional, Callable, Tuple
from streamlit_app.utils import (
    get_logger,
    get_conversation_messages,
    add_user_message,
    add_assistant_message,
    get_research_response,
    create_openai_client,
    get_model,
    is_web_search_enabled,
    get_vector_store_id,
    is_generating,
    set_generating,
    should_show_sources,
    set_show_sources,
    clear_conversation
)

logger = get_logger("chat_interface")

def typing_animation():
    """Display a typing animation for the assistant."""
    return st.markdown(
        """
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
        """,
        unsafe_allow_html=True
    )

def format_markdown(text: str) -> str:
    """Format markdown text for display, escaping HTML characters."""
    # Escape HTML characters to prevent injection
    text = html.escape(text)
    return text

def display_citation(citation: Dict[str, str]) -> None:
    """
    Display a citation with styling.
    
    Args:
        citation: Citation dictionary with 'id', 'text', and 'source' keys
    """
    # Determine if this is a web citation
    is_web_citation = citation.get('source', '').startswith('Web:')
    
    with st.container():
        if is_web_citation:
            # For web citations
            source = citation.get('source', 'Unknown source').replace('Web: ', '')
            st.markdown(f"""
            <div class="citation web-citation">
                <div class="citation-header">🌐 {citation.get('id', 'Web source')}</div>
                <div>{citation.get('text', '')}</div>
                <div class="citation-source">
                    <a href="{source}" target="_blank">{source}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # For file citations
            st.markdown(f"""
            <div class="citation">
                <div class="citation-header">📄 {citation.get('id', 'Source')}</div>
                <div>{citation.get('text', '')}</div>
                <div class="citation-source">{citation.get('source', 'Unknown source')}</div>
            </div>
            """, unsafe_allow_html=True)

def display_citations(citations: List[Dict[str, str]]) -> None:
    """
    Display a list of citations with an expandable section.
    
    Args:
        citations: List of citation dictionaries
    """
    if not citations:
        return
    
    with st.expander(f"📚 Sources ({len(citations)})", expanded=should_show_sources()):
        for citation in citations:
            display_citation(citation)

def display_message_history() -> None:
    """Display the conversation history from session state."""
    # Get message history
    messages = get_conversation_messages()
    
    # Create a container for the chat with appropriate styling
    chat_container = st.container()
    
    with chat_container:
        # Use a container with a CSS class for styling
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Iterate through messages and display them
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            citations = msg.get("citations", [])
            
            # Display the message in a chat bubble
            with st.chat_message(role):
                st.markdown(content)
                
                # Display citations if available and this is an assistant message
                if role == "assistant" and citations:
                    display_citations(citations)
        
        st.markdown('</div>', unsafe_allow_html=True)

def process_user_message(
    user_message: str,
    on_start: Optional[Callable] = None,
    on_complete: Optional[Callable] = None
) -> bool:
    """
    Process a user message and generate a response.
    
    Args:
        user_message: Message from the user
        on_start: Callback to execute when processing starts
        on_complete: Callback to execute when processing completes
        
    Returns:
        True if successful, False otherwise
    """
    # Check if already generating
    if is_generating():
        logger.warning("Already generating a response")
        return False
    
    # Set generating state to True
    set_generating(True)
    
    # Add user message to history
    add_user_message(user_message)
    
    # Call on_start callback if provided
    if on_start:
        on_start()
    
    try:
        # Get the OpenAI client
        client = create_openai_client()
        if not client:
            logger.error("OpenAI client not available")
            set_generating(False)
            return False
        
        # Get vector store ID from selected project
        vector_store_id = get_vector_store_id()
        if not vector_store_id:
            logger.error("No vector store ID available")
            set_generating(False)
            return False
        
        # Get model and web search settings
        model = get_model()
        web_search = is_web_search_enabled()
        
        logger.info(f"Getting response with model={model}, web_search={web_search}")
        
        # Get response from OpenAI
        response_text, citation_sources, debug_data = get_research_response(
            client=client,
            query=user_message,
            vector_store_id=vector_store_id,
            model=model,
            enable_web_search=web_search,
            debug=True
        )
        
        # Check if response was successful
        if not response_text:
            error_message = debug_data.get("error", "Unknown error")
            logger.error(f"Failed to get response: {error_message}")
            
            # Add error message to history
            add_assistant_message(
                f"❌ I'm sorry, I couldn't generate a response. Error: {error_message}",
                []
            )
            set_generating(False)
            return False
        
        # Format citations for display
        citations = []
        for i, source in enumerate(citation_sources):
            citations.append({
                "id": f"citation_{i+1}",
                "text": f"From document: {source}",
                "source": source
            })
        
        # Add response to history
        add_assistant_message(response_text, citations)
        
        # Call on_complete callback if provided
        if on_complete:
            on_complete(response_text, citations, debug_data)
        
        logger.info(f"Successfully generated response ({len(response_text)} chars, {len(citations)} citations)")
        set_generating(False)
        return True
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        
        # Add error message to history
        add_assistant_message(
            f"❌ I'm sorry, an error occurred while generating a response: {str(e)}",
            []
        )
        
        set_generating(False)
        return False

def streaming_process_user_message(
    user_message: str,
    placeholder: Any,
    on_start: Optional[Callable] = None,
    on_complete: Optional[Callable] = None
) -> bool:
    """
    Process a user message with streaming response.
    
    Args:
        user_message: Message from the user
        placeholder: Streamlit placeholder for displaying the streaming message
        on_start: Callback to execute when processing starts
        on_complete: Callback to execute when processing completes
        
    Returns:
        True if successful, False otherwise
    """
    # Check if already generating
    if is_generating():
        logger.warning("Already generating a response")
        return False
    
    # Set generating state to True
    set_generating(True)
    
    # Add user message to history
    add_user_message(user_message)
    
    # Call on_start callback if provided
    if on_start:
        on_start()
    
    # Show typing animation
    placeholder.markdown(
        """
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    try:
        # Get the OpenAI client
        client = create_openai_client()
        if not client:
            logger.error("OpenAI client not available")
            placeholder.error("OpenAI client not available")
            set_generating(False)
            return False
        
        # Get vector store ID from selected project
        vector_store_id = get_vector_store_id()
        if not vector_store_id:
            logger.error("No vector store ID available")
            placeholder.error("No vector store ID available")
            set_generating(False)
            return False
        
        # Get model and web search settings
        model = get_model()
        web_search = is_web_search_enabled()
        
        logger.info(f"Getting response with model={model}, web_search={web_search}")
        
        # Get response from OpenAI (non-streaming for now)
        # TODO: Implement actual streaming using st.write_stream when OpenAI supports it with file search
        response_text, citation_sources, debug_data = get_research_response(
            client=client,
            query=user_message,
            vector_store_id=vector_store_id,
            model=model,
            enable_web_search=web_search,
            debug=True
        )
        
        # Check if response was successful
        if not response_text:
            error_message = debug_data.get("error", "Unknown error")
            logger.error(f"Failed to get response: {error_message}")
            
            placeholder.error(f"I'm sorry, I couldn't generate a response. Error: {error_message}")
            
            # Add error message to history
            add_assistant_message(
                f"❌ I'm sorry, I couldn't generate a response. Error: {error_message}",
                []
            )
            set_generating(False)
            return False
        
        # Clear the placeholder with the typing animation
        placeholder.empty()
        
        # Format citations for display
        citations = []
        file_citations = 0
        web_citations = 0
        
        for i, source in enumerate(citation_sources):
            # Check if this is a web citation
            if source.startswith("Web:"):
                web_citations += 1
                citation_text = "From web search"
            else:
                file_citations += 1
                citation_text = f"From document: {source}"
                
            citations.append({
                "id": f"citation_{i+1}",
                "text": citation_text,
                "source": source
            })
        
        # First display the response text
        st.markdown(response_text)
        
        # Display citations if any
        if citations:
            citation_label = "Sources"
            if file_citations > 0 and web_citations > 0:
                citation_label = f"📚 Sources ({file_citations} files, {web_citations} web)"
            elif web_citations > 0:
                citation_label = f"🌐 Web Sources ({web_citations})"
            else:
                citation_label = f"📄 Document Sources ({file_citations})"
                
            with st.expander(citation_label, expanded=should_show_sources()):
                for citation in citations:
                    display_citation(citation)
        
        # Add response to history
        add_assistant_message(response_text, citations)
        
        # Call on_complete callback if provided
        if on_complete:
            on_complete(response_text, citations, debug_data)
        
        logger.info(f"Successfully generated response ({len(response_text)} chars, {len(citations)} citations)")
        set_generating(False)
        return True
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        
        placeholder.error(f"I'm sorry, an error occurred: {str(e)}")
        
        # Add error message to history
        add_assistant_message(
            f"❌ I'm sorry, an error occurred while generating a response: {str(e)}",
            []
        )
        
        set_generating(False)
        return False

def chat_interface(
    show_message_history: bool = True,
    chat_box_placeholder: str = "Ask about your research...",
    use_streaming: bool = True
) -> None:
    """
    Display a compact chat interface with message history and input.
    
    Args:
        show_message_history: Whether to display the conversation history
        chat_box_placeholder: Placeholder text for the chat input
        use_streaming: Whether to use streaming for responses
    """
    # Check if we have a vector store ID
    if not get_vector_store_id():
        st.warning("Please select a research project first")
        return
    
    # Display a compact info message when generating
    if is_generating():
        st.info("Generating response...", icon="⏳")
        
    # Display conversation history if requested (in a container to apply styling)
    if show_message_history:
        display_message_history()
    
    # Display a compact web search hint if enabled (using icon and inline style)
    if is_web_search_enabled() and not is_generating():
        st.info("💡 Web search is enabled - ask about current events or topics beyond your research documents", icon="🔍")
    
    # Chat input - use a more compact styling
    web_enabled = is_web_search_enabled()
    input_placeholder = "Ask about your research or current events..." if web_enabled else chat_box_placeholder
    
    # Add a small visual separator before the input (using CSS instead of spacing)
    st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
    
    user_input = st.chat_input(input_placeholder)
    
    if user_input:
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Create a placeholder for the assistant's message
        with st.chat_message("assistant"):
            if use_streaming:
                # Process with streaming
                streaming_process_user_message(
                    user_message=user_input,
                    placeholder=st.empty()
                )
            else:
                # Show an initial "thinking" message
                message_placeholder = st.empty()
                message_placeholder.info("Thinking...", icon="🤔")
                
                # Process user message
                success = process_user_message(user_input)
                
                if success:
                    # Update the placeholder with the actual response (from history)
                    message_placeholder.empty()
                    messages = get_conversation_messages()
                    if messages and len(messages) > 0:
                        last_message = messages[-1]
                        if last_message["role"] == "assistant":
                            st.markdown(last_message["content"])
                            
                            # Display citations if available
                            if "citations" in last_message and last_message["citations"]:
                                display_citations(last_message["citations"])
                else:
                    # Error already added to history and displayed
                    message_placeholder.empty()
                    
    # Add compact chat controls - clear chat, source toggle
    if get_conversation_messages():
        cols = st.columns([1, 1, 6])
        with cols[0]:
            if st.button("Clear Chat", key="clear_chat", use_container_width=True):
                clear_conversation()
                st.rerun()
        with cols[1]:
            expand = should_show_sources()
            if st.toggle("Show Sources", value=expand, key="toggle_sources"):
                set_show_sources(not expand)
                st.rerun() 