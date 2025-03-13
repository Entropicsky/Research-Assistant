"""
OpenAI client utilities for the Streamlit app.

This module provides functions for interacting with the OpenAI API,
including creating clients, processing responses, and handling errors.
"""

import os
import time
import streamlit as st
from openai import OpenAI
from typing import Dict, List, Any, Optional, Union, Tuple
from .logger import get_logger
import json

logger = get_logger("openai_client")

# Hardcoded list of OpenAI models
AVAILABLE_MODELS = [
    {"id": "gpt-4o", "name": "GPT-4o", "description": "Most capable general-purpose model, best for complex tasks"},
    {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Smaller, faster, and more affordable version of GPT-4o"},
    {"id": "gpt-4.5-preview", "name": "GPT-4.5 Preview", "description": "Preview of the next-generation GPT model"},
    {"id": "o1", "name": "o1", "description": "Advanced reasoning model with step-by-step thinking"},
    {"id": "o3-mini", "name": "o3-mini", "description": "Smaller reasoning model optimized for efficiency"}
]

# Cached client creation
@st.cache_resource
def create_openai_client() -> Optional[OpenAI]:
    """
    Create and cache an OpenAI client.
    
    Returns:
        OpenAI client or None if an error occurs
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not set in environment")
            return None
            
        client = OpenAI(api_key=api_key)
        # Test the client with a simple request
        try:
            # Fetch the list of models to verify API key works
            models = client.models.list()
            logger.info(f"OpenAI client created successfully")
            return client
        except Exception as e:
            logger.error(f"Error testing OpenAI client: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {str(e)}")
        return None

def get_available_models() -> List[Dict[str, str]]:
    """Get the list of available models."""
    return AVAILABLE_MODELS

def get_model_by_id(model_id: str) -> Optional[Dict[str, str]]:
    """Get model information by ID."""
    for model in AVAILABLE_MODELS:
        if model["id"] == model_id:
            return model
    return None

def get_research_response(
    client: OpenAI, 
    query: str, 
    vector_store_id: str,
    model: str = "gpt-4o-mini",
    enable_web_search: bool = False,
    max_search_results: int = 5,
    debug: bool = False
) -> Tuple[Optional[str], List[str], Dict[str, Any]]:
    """
    Get a response from OpenAI using the Responses API with vector store search.
    
    Args:
        client: OpenAI client
        query: User query
        vector_store_id: ID of the vector store to search
        model: Model to use for generation
        enable_web_search: Whether to enable web search
        max_search_results: Maximum number of search results to return
        debug: Whether to include debug information in the response
        
    Returns:
        Tuple containing:
        - Response text or None if an error occurs
        - List of citation filenames
        - Debug data dictionary with timing and other information
    """
    if not client:
        logger.error("OpenAI client not available")
        return None, [], {"error": "OpenAI client not available"}
    
    if not vector_store_id:
        logger.error("Vector store ID not provided")
        return None, [], {"error": "Vector store ID not provided"}
    
    start_time = time.time()
    debug_data = {
        "query": query,
        "model": model,
        "vector_store_id": vector_store_id,
        "web_search_enabled": enable_web_search,
        "max_search_results": max_search_results,
        "start_time": start_time,
    }
    
    # Modify the input query if web search is enabled to provide explicit instructions
    user_input = query
    if enable_web_search:
        # Augment the query with instructions about tool usage
        user_input = (
            f"{query}\n\n"
            f"Note: If you don't find sufficient information in the research documents, "
            f"please use web search to look for up-to-date information on this topic. "
            f"For questions about current events, sports scores, or real-time data, web search is preferred."
        )
    
    # Build tools list
    tools = [{
        "type": "file_search",
        "vector_store_ids": [vector_store_id],
        "max_num_results": max_search_results
    }]
    
    # Add web search if enabled
    if enable_web_search:
        tools.append({
            "type": "web_search"
        })
    
    try:
        logger.info(f"Sending request to OpenAI with {len(tools)} tools")
        
        # Determine which outputs to include in the response
        include_outputs = ["output[*].file_search_call.search_results"]
        if enable_web_search:
            include_outputs.append("output[*].web_search_call.search_results")
            
        # Call OpenAI API
        response = client.responses.create(
            model=model,
            input=user_input,  # Use potentially modified input with instructions
            tools=tools,
            include=include_outputs,
            tool_choice="auto"  # The API doesn't support more complex tool_choice configurations
        )
        
        # Extract response text and citations
        response_text = ""
        citations = []
        web_citations = []
        used_web_search = False
        used_file_search = False
        
        debug_data["api_response_time"] = time.time() - start_time
        
        if response and response.output:
            for output in response.output:
                # Check if web search was used
                if output.type == "web_search_call":
                    used_web_search = True
                    logger.info("Web search was used in this response")
                
                # Check if file search was used
                if output.type == "file_search_call":
                    used_file_search = True
                    logger.info("File search was used in this response")
                
                if output.type == "message":
                    for content_item in output.content:
                        if content_item.type == "output_text":
                            response_text = content_item.text
                            
                            # Extract file citations
                            if hasattr(content_item, 'annotations') and content_item.annotations:
                                for annotation in content_item.annotations:
                                    if annotation.type == "file_citation":
                                        citations.append(annotation.filename)
                                    elif annotation.type == "web_search_citation":
                                        web_citations.append(f"Web: {annotation.url}")
                                        
                # Add file search details to debug data if available
                if debug and output.type == "file_search_call":
                    debug_data["file_search"] = {
                        "search_results": [{
                            "filename": result.filename,
                            "score": result.score
                        } for result in output.search_results] if hasattr(output, 'search_results') else []
                    }
                
                # Add web search details to debug data if available
                if debug and output.type == "web_search_call":
                    debug_data["web_search"] = {
                        "search_results": []
                    }
                    if hasattr(output, 'search_results'):
                        debug_data["web_search"]["search_results"] = [
                            {"title": result.title, "url": result.url}
                            for result in output.search_results
                        ]
        
        # Combine file and web citations
        all_citations = citations + web_citations
        
        debug_data["total_time"] = time.time() - start_time
        debug_data["success"] = True
        debug_data["response_length"] = len(response_text)
        debug_data["citation_count"] = len(all_citations)
        debug_data["file_citation_count"] = len(citations)
        debug_data["web_citation_count"] = len(web_citations)
        debug_data["used_web_search"] = used_web_search
        debug_data["used_file_search"] = used_file_search
        
        # Log detailed information about the response
        logger.info(f"Got response from OpenAI ({len(response_text)} chars, {len(all_citations)} citations) in {debug_data['total_time']:.2f}s")
        if enable_web_search:
            if used_web_search:
                logger.info(f"Web search was used with {len(web_citations)} citations")
            else:
                logger.info("Web search was enabled but not used by the model")
        
        return response_text, all_citations, debug_data
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error from OpenAI API: {error_message}")
        
        debug_data["success"] = False
        debug_data["error"] = error_message
        debug_data["total_time"] = time.time() - start_time
        
        return None, [], debug_data

def extract_citations_from_response(response, citations_map=None):
    """
    Extract and format citations from an OpenAI response.
    
    Args:
        response: OpenAI response object
        citations_map: Optional dictionary to map citation IDs to friendly names
        
    Returns:
        List of citation objects with id, text, and source fields
    """
    citations = []
    citations_map = citations_map or {}
    
    # Check if the response has the expected structure
    if not response or not hasattr(response, 'output'):
        return citations
    
    for output in response.output:
        if not hasattr(output, 'content'):
            continue
            
        for content_item in output.content:
            if not hasattr(content_item, 'annotations'):
                continue
                
            for i, annotation in enumerate(content_item.annotations):
                if annotation.type == "file_citation":
                    citation_id = f"citation_{i+1}"
                    source = annotation.filename
                    
                    # Use friendly name if available in map
                    friendly_name = citations_map.get(source, source)
                    
                    citations.append({
                        "id": citation_id,
                        "text": annotation.text,
                        "source": friendly_name
                    })
    
    return citations 