"""
Project Selector Component for the Streamlit app.

This module provides visual interfaces for selecting research projects.
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

def format_date(date_str: str) -> str:
    """Format date string for display."""
    try:
        if "T" in date_str:
            # ISO format
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%B %d, %Y")
        else:
            # Just date part
            return date_str
    except:
        return date_str

def project_card(
    project: Dict[str, Any],
    index: int,
    is_selected: bool = False,
    on_click: Optional[Callable] = None,
    include_stats: bool = True
) -> None:
    """
    Display a project card with details and selection capability.
    
    Args:
        project: Project dictionary
        index: Index of this project in the list
        is_selected: Whether this project is currently selected
        on_click: Function to call when the card is clicked
        include_stats: Whether to include project stats in the card
    """
    project_topic = project.get("parameters", {}).get("topic", "Untitled Project")
    timestamp = project.get("timestamp", "")
    questions = project.get("parameters", {}).get("questions", [])
    status = project.get("status", "unknown")
    is_active = project.get("active", True)  # Default to active if not set
    
    # Format the date for display
    formatted_date = "Unknown date"
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%Y-%m-%d")
        except:
            formatted_date = timestamp
    
    # Card styling
    card_class = "project-card selected" if is_selected else "project-card"
    
    # Add visual indication for inactive projects
    card_style = ""
    status_text = ""
    if not is_active:
        card_style = "opacity: 0.6; background-color: #f0f0f0;"
        status_text = "📴 INACTIVE"
    
    with st.container():
        # Using html for the card styling with optional inactive styling
        st.markdown(f"""
        <div class="{card_class}" style="{card_style}">
            <div class="project-card-title">{project_topic}</div>
            <div class="project-card-info">
                <div>Date: {formatted_date}</div>
                <div>Status: {status.upper()}</div>
                <div style="color: {'#888' if not is_active else '#000'};">{status_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Hidden button to handle the click
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button(f"Select Project", key=f"select_project_{index}"):
                if on_click:
                    on_click(project, index)
        
        # Add a button to toggle active status
        with col2:
            from streamlit_app.utils import update_project_active_status
            
            button_text = "Activate" if not is_active else "Deactivate"
            if st.button(button_text, key=f"toggle_active_{index}"):
                project_id = project.get("id")
                if project_id:
                    success = update_project_active_status(project_id, not is_active)
                    if success:
                        st.rerun()
                    else:
                        st.error("Failed to update project status")
                else:
                    st.error("Project ID not found")

def project_selector(
    projects: List[Dict[str, Any]],
    on_project_selected: Callable,
    currently_selected_index: Optional[int] = None,
    use_cards: bool = True,
    include_stats: bool = True
) -> None:
    """
    Display a project selector with options for card or dropdown view.
    
    Args:
        projects: List of project dictionaries
        on_project_selected: Function to call when a project is selected
        currently_selected_index: Index of currently selected project
        use_cards: Whether to use card view (True) or dropdown (False)
        include_stats: Whether to include project statistics
    """
    if not projects:
        st.warning("No research projects available. Create a new project first.")
        return
    
    # Create container with styling
    with st.container(border=True):
        st.subheader("Select a Research Project")
        
        # Toggle between card and dropdown view
        col1, col2 = st.columns([3, 1])
        with col1:
            view_mode = "Card View" if use_cards else "Dropdown"
            st.caption(f"Showing {len(projects)} projects in {view_mode}")
        
        with col2:
            if st.toggle("Card View", value=use_cards, key="toggle_card_view"):
                use_cards = True
            else:
                use_cards = False
        
        # Display projects based on view mode
        if use_cards:
            # Card view
            for i, project in enumerate(projects):
                project_card(
                    project=project,
                    index=i,
                    is_selected=(i == currently_selected_index),
                    on_click=on_project_selected
                )
        else:
            # Dropdown view
            project_options = [
                f"{p.get('parameters', {}).get('topic', 'Research Project')} ({p.get('timestamp', '').split('T')[0]})"
                for p in projects
            ]
            
            selected_index = st.selectbox(
                "Select a research project to chat with:",
                range(len(project_options)),
                format_func=lambda i: project_options[i],
                key="project_dropdown_selector",
                index=currently_selected_index if currently_selected_index is not None else 0
            )
            
            if st.button("Select Project", key="select_project_from_dropdown"):
                on_project_selected(projects[selected_index], selected_index)
        
        # Add stats if requested
        if include_stats and currently_selected_index is not None:
            selected_project = projects[currently_selected_index]
            vector_store = selected_project.get("openai_integration", {}).get("vector_store", {})
            vector_store_id = vector_store.get("id", "")
            vector_store_name = vector_store.get("name", "")
            file_count = len(selected_project.get("openai_integration", {}).get("files", []))
            
            st.divider()
            st.caption("Selected Project Details")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Vector Store:** {vector_store_name}")
                st.markdown(f"**ID:** `{vector_store_id[:10]}...`")
            with col2:
                st.markdown(f"**Files:** {file_count}")
                st.markdown(f"**Status:** {selected_project.get('status', 'unknown')}")

def compact_project_selector(
    projects: List[Dict[str, Any]],
    on_project_selected: Callable,
    currently_selected_index: Optional[int] = None
) -> None:
    """
    Display a compact project selector (dropdown only).
    
    Args:
        projects: List of project dictionaries
        on_project_selected: Function to call when a project is selected
        currently_selected_index: Index of currently selected project
    """
    if not projects:
        st.warning("No research projects available. Create a new project first.")
        return
    
    # Project options
    project_options = [
        f"{p.get('parameters', {}).get('topic', 'Research Project')} ({p.get('timestamp', '').split('T')[0]})"
        for p in projects
    ]
    
    # Dropdown selector
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_index = st.selectbox(
            "Select project:",
            range(len(project_options)),
            format_func=lambda i: project_options[i],
            key="compact_project_selector",
            index=currently_selected_index if currently_selected_index is not None else 0
        )
    
    with col2:
        if st.button("Select", key="select_compact_project"):
            on_project_selected(projects[selected_index], selected_index) 