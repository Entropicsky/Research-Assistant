"""
Debug Panel Component for the Streamlit app.

This module provides a panel for displaying debug information and logs.
"""

import streamlit as st
import json
from typing import Dict, List, Any, Optional
from streamlit_app.utils import get_logger, is_debug_mode

logger = get_logger("debug_panel")

def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Format JSON data for display."""
    return json.dumps(data, indent=indent, default=str)

def display_debug_data(debug_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Display debug data in a collapsible section.
    
    Args:
        debug_data: Debug data dictionary to display
    """
    if not debug_data:
        st.info("No debug data available")
        return
    
    # Create tabs for different types of debug data
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Summary", "Request", "Response", "Models", "JSON"])
    
    with tab1:
        # Display summary information
        st.write("**Request Summary**")
        st.write(f"Model: `{debug_data.get('model', 'unknown')}`")
        st.write(f"Web Search: `{debug_data.get('web_search_enabled', False)}`")
        st.write(f"Vector Store ID: `{debug_data.get('vector_store_id', 'unknown')}`")
        
        st.write("**Response Summary**")
        st.write(f"Success: `{debug_data.get('success', False)}`")
        st.write(f"Response Length: `{debug_data.get('response_length', 0)}` chars")
        
        # Display which tools were used
        if debug_data.get('web_search_enabled', False):
            web_search_used = debug_data.get('used_web_search', False)
            file_search_used = debug_data.get('used_file_search', False)
            
            if web_search_used:
                st.write(f"✅ **Web search was used** with `{debug_data.get('web_citation_count', 0)}` citations")
            else:
                st.write("❌ **Web search was NOT used**")
                
            if file_search_used:
                st.write(f"✅ **File search was used** with `{debug_data.get('file_citation_count', 0)}` citations")
            else:
                st.write("❌ **File search was NOT used**")
        
        # Display timing information if available
        if debug_data.get('timing'):
            st.write("**Timing Information**")
            timing = debug_data.get('timing', {})
            st.write(f"Total Time: `{timing.get('total', 0):.2f}` seconds")
            st.write(f"API Time: `{timing.get('api', 0):.2f}` seconds")
            st.write(f"Processing Time: `{timing.get('processing', 0):.2f}` seconds")
    
    with tab2:
        # Display request information
        st.write("**Request Details**")
        st.write(f"Query: `{debug_data.get('query', '')}`")
        st.write(f"Model: `{debug_data.get('model', 'unknown')}`")
        st.write(f"Request Time: `{debug_data.get('request_time', 'unknown')}`")
        
        # Display message history if available
        if debug_data.get('messages'):
            st.write("**Message History**")
            for i, msg in enumerate(debug_data.get('messages', [])):
                role = msg.get('role', 'unknown')
                content_preview = (msg.get('content', '')[:100] + '...') if len(msg.get('content', '')) > 100 else msg.get('content', '')
                st.write(f"**{i+1}. {role.upper()}:** {content_preview}")
                with st.expander("View full message"):
                    st.write(msg.get('content', ''))
    
    with tab3:
        # Display response information
        st.write("**Response Details**")
        st.write(f"Success: `{debug_data.get('success', False)}`")
        st.write(f"Response Time: `{debug_data.get('response_time', 'unknown')}`")
        
        # Display error information if there was an error
        if not debug_data.get('success', False) and debug_data.get('error'):
            st.error(f"Error: {debug_data.get('error', 'Unknown error')}")
            if debug_data.get('error_details'):
                with st.expander("Error Details"):
                    st.write(debug_data.get('error_details', ''))
        
        # Display response content if available
        if debug_data.get('response_content'):
            st.write("**Response Content**")
            with st.expander("View response content"):
                st.write(debug_data.get('response_content', ''))
        
        # Display citation information if available
        if debug_data.get('citations'):
            st.write("**Citations**")
            for i, citation in enumerate(debug_data.get('citations', [])):
                st.write(f"**Citation {i+1}:** {citation.get('text', 'Unknown citation')}")
                st.write(f"Source: {citation.get('source', 'Unknown source')}")
                st.write("---")
    
    with tab4:
        # Display OpenAI models information
        st.write("**Available OpenAI Models**")
        
        # Import get_available_models inside the function to avoid circular imports
        from streamlit_app.utils import get_available_models
        
        # Get available models
        models = get_available_models()
        
        # Create a table of models
        data = []
        for model in models:
            data.append({
                "ID": model["id"],
                "Name": model["name"],
                "Description": model["description"]
            })
        
        # Display as a dataframe
        st.dataframe(data, use_container_width=True)
        
        # Add information about model usage
        st.info("These are the predefined models available for use with the Research Assistant. " +
                "Your OpenAI API key must have access to these models for them to work properly.")
    
    with tab5:
        # Display raw JSON data
        st.write("**Raw Debug Data (JSON)**")
        st.code(format_json(debug_data), language="json")

def display_logs(max_entries: int = 100) -> None:
    """
    Display log entries from session state.
    
    Args:
        max_entries: Maximum number of log entries to display
    """
    from streamlit_app.utils.logger import logger
    logger.display_logs(max_entries=max_entries)

def debug_panel(debug_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Display a comprehensive debug panel with logs and debug data.
    
    Args:
        debug_data: Debug data dictionary to display
    """
    with st.expander("Debug Panel", expanded=is_debug_mode()):
        tab1, tab2 = st.tabs(["Debug Data", "Logs"])
        
        with tab1:
            if debug_data:
                display_debug_data(debug_data)
            else:
                st.info("No debug data available")
        
        with tab2:
            log_filter = st.selectbox(
                "Log Level",
                ["All", "Debug", "Info", "Warning", "Error", "Critical"],
                index=0
            )
            
            level_filter = None
            if log_filter != "All":
                level_filter = log_filter.lower()
            
            max_logs = st.slider("Max Log Entries", 10, 500, 100)
            
            # Convert level_filter to match the case in log entries
            from streamlit_app.utils.logger import logger
            logger.display_logs(
                max_entries=max_logs,
                level_filter=level_filter
            )

def toggle_debug_mode() -> bool:
    """
    Toggle debug mode and return the new state.
    
    Returns:
        New debug mode state (True if enabled, False if disabled)
    """
    from streamlit_app.utils import toggle_debug_mode, is_debug_mode
    
    # Create two columns for the toggle and caption
    col1, col2 = st.columns([1, 3])
    
    with col1:
        enabled = is_debug_mode()
        if st.toggle("Debug Mode", value=enabled, key="debug_mode_toggle"):
            if not enabled:  # Only toggle if the state has changed
                toggle_debug_mode()
                enabled = True
        else:
            if enabled:  # Only toggle if the state has changed
                toggle_debug_mode()
                enabled = False
    
    with col2:
        if enabled:
            st.caption("Debug mode is enabled")
        else:
            st.caption("Debug mode is disabled")
    
    return enabled 