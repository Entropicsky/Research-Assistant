"""
Project management utilities for the Streamlit app.

This module provides functions for loading, filtering, and selecting research projects.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
from .logger import get_logger

logger = get_logger("projects")

# Cached project loading
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_research_projects(file_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load research projects from the JSON file.
    
    Args:
        file_path: Path to the JSON file (uses env var if not provided)
        
    Returns:
        List of projects or empty list if error occurs
    """
    file_path = file_path or os.getenv("RESEARCH_PROJECTS_FILE", "research_projects.json")
    
    start_time = time.time()
    try:
        if not os.path.exists(file_path):
            logger.error(f"Research projects file not found: {file_path}")
            return []
            
        with open(file_path, "r") as f:
            data = json.load(f)
            projects = data.get("projects", [])
            
        logger.info(f"Loaded {len(projects)} projects from {file_path} in {time.time() - start_time:.2f}s")
        return projects
    except Exception as e:
        logger.error(f"Error loading research projects: {str(e)}")
        return []

def filter_available_projects(projects: List[Dict[str, Any]], 
                             require_openai: bool = True,
                             require_vector_store: bool = True,
                             include_incomplete: bool = False,
                             include_inactive: bool = False) -> List[Dict[str, Any]]:
    """
    Filter projects based on various criteria.
    
    Args:
        projects: List of all projects
        require_openai: Whether to require OpenAI integration
        require_vector_store: Whether to require a vector store
        include_incomplete: Whether to include incomplete projects
        include_inactive: Whether to include inactive projects
        
    Returns:
        List of filtered projects
    """
    filtered_projects = []
    
    for project in projects:
        # Skip incomplete projects if not requested
        if not include_incomplete and project.get("status") != "completed":
            continue
        
        # Handle active status
        is_active = project.get("active", True)  # Default to active if not specified
        if not include_inactive and not is_active:
            continue
        
        # Handle OpenAI integration requirement
        openai_integration = project.get("openai_integration", {})
        if require_openai and openai_integration.get("status") != "success":
            continue
            
        # Handle vector store requirement
        vector_store = openai_integration.get("vector_store", {})
        if require_vector_store and not vector_store.get("id"):
            continue
            
        filtered_projects.append(project)
    
    logger.info(f"Filtered {len(filtered_projects)} projects from {len(projects)} total projects")
    return filtered_projects

def get_project_info(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format key information from a project.
    
    Args:
        project: Project dictionary
        
    Returns:
        Dictionary with formatted project information
    """
    # Extract basic project info
    params = project.get("parameters", {})
    timestamp = project.get("timestamp", "").split("T")[0]  # Just the date part
    topic = params.get("topic", "Research Project")
    perspective = params.get("perspective", "Researcher")
    
    # Extract questions if available
    questions = params.get("questions", [])
    question_count = len(questions)
    
    # Extract vector store info if available
    vector_store = project.get("openai_integration", {}).get("vector_store", {})
    vector_store_id = vector_store.get("id", "")
    vector_store_name = vector_store.get("name", "")
    
    # Extract file info if available
    files = project.get("openai_integration", {}).get("files", [])
    file_count = len(files)
    
    return {
        "topic": topic,
        "perspective": perspective,
        "timestamp": timestamp,
        "question_count": question_count,
        "questions": questions,
        "vector_store_id": vector_store_id,
        "vector_store_name": vector_store_name,
        "file_count": file_count,
        "display_name": f"{topic} ({timestamp})",
        "full_project": project
    }

def get_formatted_project_list(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert a list of projects to a list of formatted project info dictionaries.
    
    Args:
        projects: List of projects
        
    Returns:
        List of formatted project info dictionaries
    """
    return [get_project_info(project) for project in projects]

def get_project_display_options(projects: List[Dict[str, Any]]) -> List[str]:
    """
    Generate display options for a list of projects.
    
    Args:
        projects: List of projects
        
    Returns:
        List of formatted display strings for project selection
    """
    return [
        f"{p.get('parameters', {}).get('topic', 'Research Project')} ({p.get('timestamp', '').split('T')[0]})"
        for p in projects
    ]

def update_projects_file(projects: List[Dict[str, Any]], file_path: Optional[str] = None) -> bool:
    """
    Update the research projects JSON file with modified projects.
    
    Args:
        projects: List of all projects
        file_path: Path to the JSON file (uses env var if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    file_path = file_path or os.getenv("RESEARCH_PROJECTS_FILE", "research_projects.json")
    
    try:
        # First read the existing file to preserve structure
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Update projects
        data["projects"] = projects
        
        # Write back to file
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Updated {len(projects)} projects in {file_path}")
        
        # Clear the cache to ensure fresh data on next load
        load_research_projects.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error updating research projects file: {str(e)}")
        return False

def archive_project(project_id: str, file_path: Optional[str] = None) -> bool:
    """
    Archive a project by ID.
    
    Args:
        project_id: ID of the project to archive
        file_path: Path to the JSON file (uses env var if not provided)
        
    Returns:
        True if successful, False otherwise
    """
    projects = load_research_projects(file_path)
    
    # Find the project by ID
    for project in projects:
        if project.get("id") == project_id:
            project["archived"] = True
            return update_projects_file(projects, file_path)
    
    logger.error(f"Project with ID {project_id} not found")
    return False

def update_project_active_status(project_id: str, is_active: bool, file_path: Optional[str] = None) -> bool:
    """
    Update a project's active status in the research_projects.json file.
    
    Args:
        project_id: ID of the project to update
        is_active: New active status (True for active, False for inactive)
        file_path: Path to the research_projects.json file
        
    Returns:
        True if successful, False otherwise
    """
    file_path = file_path or os.getenv("RESEARCH_PROJECTS_FILE", "research_projects.json")
    
    try:
        if not os.path.exists(file_path):
            logger.error(f"Research projects file not found: {file_path}")
            return False
        
        # Load the entire file
        with open(file_path, "r") as f:
            data = json.load(f)
        
        # Find and update the project
        found = False
        for project in data.get("projects", []):
            if project.get("id") == project_id:
                project["active"] = is_active
                found = True
                break
        
        if not found:
            logger.error(f"Project with ID {project_id} not found")
            return False
        
        # Update the last_updated timestamp
        data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Save the updated file
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Clear the cache so the updated file will be reloaded
        load_research_projects.clear()
        
        logger.info(f"Updated active status of project {project_id} to {is_active}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating project active status: {str(e)}")
        return False 