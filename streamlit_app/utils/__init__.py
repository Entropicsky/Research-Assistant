"""
Utilities for the Streamlit app.

This package provides various utility functions for the Streamlit app,
including logging, state management, and OpenAI API interactions.
"""

# Export logger functions
from .logger import (
    get_logger,
    logger,
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
)

# Export state management functions
from .state import (
    init_session_state,
    add_user_message,
    add_assistant_message,
    get_conversation_messages,
    clear_conversation,
    get_openai_messages,
    set_selected_project,
    get_selected_project,
    get_vector_store_id,
    toggle_debug_mode,
    is_debug_mode,
    toggle_show_sources,
    should_show_sources,
    set_show_sources,
    toggle_show_inactive_projects,
    should_show_inactive_projects,
    set_show_inactive_projects,
    set_model,
    get_model,
    toggle_web_search,
    is_web_search_enabled,
    set_generating,
    is_generating,
    export_conversation,
    import_conversation
)

# Export OpenAI client functions
from .openai_client import (
    create_openai_client,
    get_available_models,
    get_model_by_id,
    get_research_response,
    extract_citations_from_response
)

# Export project management functions
from .projects import (
    load_research_projects,
    filter_available_projects,
    get_project_info,
    get_formatted_project_list,
    get_project_display_options,
    update_projects_file,
    archive_project,
    update_project_active_status
)

__all__ = [
    # Logger
    'get_logger', 'logger', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
    
    # State management
    'init_session_state', 'add_user_message', 'add_assistant_message',
    'get_conversation_messages', 'clear_conversation', 'get_openai_messages',
    'set_selected_project', 'get_selected_project', 'get_vector_store_id',
    'toggle_debug_mode', 'is_debug_mode', 'toggle_show_sources', 'should_show_sources',
    'set_show_sources', 'toggle_show_inactive_projects', 'should_show_inactive_projects', 
    'set_show_inactive_projects', 'set_model', 'get_model', 'toggle_web_search', 
    'is_web_search_enabled', 'set_generating', 'is_generating', 'export_conversation', 
    'import_conversation',
    
    # OpenAI client
    'create_openai_client', 'get_available_models', 'get_model_by_id',
    'get_research_response', 'extract_citations_from_response',
    
    # Project management
    'load_research_projects', 'filter_available_projects', 'get_project_info',
    'get_formatted_project_list', 'get_project_display_options',
    'update_projects_file', 'archive_project', 'update_project_active_status'
] 