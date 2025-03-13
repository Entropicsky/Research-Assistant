"""
Components for the Streamlit app.

This package provides various UI components for the Streamlit app,
including the chat interface, project selector, and debug panel.
"""

# Export chat interface components
from .chat_interface import (
    chat_interface,
    display_message_history,
    display_citations,
    process_user_message,
    streaming_process_user_message,
    typing_animation
)

# Export project selector components
from .project_selector import (
    project_selector,
    compact_project_selector,
    project_card,
    format_date
)

# Export model selector components
from .model_selector import (
    model_selector,
    compact_model_selector,
    model_option_card,
    web_search_toggle,
    model_settings_panel
)

# Export debug panel components
from .debug_panel import (
    debug_panel,
    display_debug_data,
    display_logs,
    toggle_debug_mode,
    format_json
)

__all__ = [
    # Chat interface
    'chat_interface',
    'display_message_history',
    'display_citations',
    'process_user_message',
    'streaming_process_user_message',
    'typing_animation',
    
    # Project selector
    'project_selector',
    'compact_project_selector',
    'project_card',
    'format_date',
    
    # Model selector
    'model_selector',
    'compact_model_selector',
    'model_option_card',
    'web_search_toggle',
    'model_settings_panel',
    
    # Debug panel
    'debug_panel',
    'display_debug_data',
    'display_logs',
    'toggle_debug_mode',
    'format_json'
] 