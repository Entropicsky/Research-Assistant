"""
Model Selector Component for the Streamlit app.

This module provides a visual interface for selecting OpenAI models.
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from streamlit_app.utils import get_available_models, get_model, set_model

def model_option_card(
    model: Dict[str, str],
    is_selected: bool = False,
    on_click: Optional[Callable] = None
) -> None:
    """
    Display a single model option card.
    
    Args:
        model: Model info dictionary
        is_selected: Whether this model is currently selected
        on_click: Function to call when the card is clicked
    """
    model_id = model["id"]
    model_name = model["name"]
    model_desc = model["description"]
    
    # Card styling
    card_class = "model-option selected" if is_selected else "model-option"
    
    with st.container():
        # Using html for the card styling
        st.markdown(f"""
        <div class="{card_class}">
            <div class="model-name" style="color: #000000;">{model_name}</div>
            <div class="model-description" style="color: #555555;">{model_desc}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Hidden button to handle the click
        if st.button(f"Select {model_name}", key=f"select_model_{model_id}"):
            if on_click:
                on_click(model_id)

def model_selector(
    on_model_selected: Optional[Callable] = None,
    show_description: bool = True
) -> str:
    """
    Display a model selector with visual cards.
    
    Args:
        on_model_selected: Function to call when a model is selected
        show_description: Whether to show model descriptions
        
    Returns:
        Currently selected model ID
    """
    # Get available models
    models = get_available_models()
    current_model = get_model()
    
    # If no callback is provided, use default state handler
    if on_model_selected is None:
        on_model_selected = set_model
    
    # Create container with styling
    with st.container(border=True):
        # Add header in a single column
        st.subheader("Select AI Model")
        
        # Display model options
        for model in models:
            model_option_card(
                model=model,
                is_selected=(model["id"] == current_model),
                on_click=on_model_selected
            )
            
        # Show selected model info
        if show_description:
            st.divider()
            st.caption(f"Currently using: {current_model}")
    
    return current_model

def compact_model_selector(
    on_model_selected: Optional[Callable] = None
) -> str:
    """
    Display a compact model selector (dropdown).
    
    Args:
        on_model_selected: Function to call when a model is selected
        
    Returns:
        Currently selected model ID
    """
    # Get available models
    models = get_available_models()
    current_model = get_model()
    
    # If no callback is provided, use default state handler
    if on_model_selected is None:
        on_model_selected = set_model
    
    # Model options
    model_options = [model["id"] for model in models]
    model_names = {model["id"]: model["name"] for model in models}
    
    # Simple dropdown selector
    selected_model = st.selectbox(
        "AI model:",
        model_options,
        format_func=lambda x: model_names.get(x, x),
        key="compact_model_selector",
        index=model_options.index(current_model) if current_model in model_options else 0
    )
    
    # Apply the model selection immediately when changed
    if selected_model != current_model:
        on_model_selected(selected_model)
    
    return selected_model

def web_search_toggle() -> bool:
    """
    Display a toggle for enabling/disabling web search without using columns.
    
    Returns:
        Whether web search is enabled
    """
    from streamlit_app.utils import toggle_web_search, is_web_search_enabled
    
    enabled = is_web_search_enabled()
    
    # Simplified toggle without columns
    if st.toggle("Enable web search", value=enabled, key="web_search_toggle", help="Allow the AI to search the web for current information"):
        if not enabled:  # Only toggle if the state has changed
            toggle_web_search()
            enabled = True
    else:
        if enabled:  # Only toggle if the state has changed
            toggle_web_search()
            enabled = False
    
    return enabled

def model_settings_panel():
    """Display a panel with model settings in a compact layout without nested columns."""
    with st.container():
        # Model selector
        current_model = compact_model_selector()
        
        # Web search toggle with compact styling
        web_enabled = web_search_toggle()
        
        # Use a small, subtle caption for current settings with explicit color
        st.markdown(f"<div style='color: #444444; font-size: 0.8em;'>Using {current_model} {'+ web search' if web_enabled else ''}</div>", unsafe_allow_html=True)
    
    return current_model, web_enabled 