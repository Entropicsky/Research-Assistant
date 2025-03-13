#!/usr/bin/env python3
"""
OpenAI File Search Test Script

This script demonstrates how to use OpenAI's File Search capability with research output files
from the research_orchestrator.py script.

It performs the following steps:
1. Creates a directory to find/store the files for testing
2. Uploads files to OpenAI's File API
3. Creates a vector store
4. Adds the files to the vector store
5. Performs semantic searches against the files

Usage:
    python filesearchtest.py [directory_path]

If directory_path is not provided, it will look for files in ./filesearchtest/
"""

import os
import sys
import time
import glob
import requests
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_file(client, file_path):
    """
    Upload a file to OpenAI's File API.
    
    Args:
        client: The OpenAI client
        file_path: Path to the file to upload
        
    Returns:
        The file ID
    """
    print(f"Uploading file: {file_path}")
    
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Download the file content from the URL
        response = requests.get(file_path)
        file_content = BytesIO(response.content)
        file_name = file_path.split("/")[-1]
        file_tuple = (file_name, file_content)
        result = client.files.create(
            file=file_tuple,
            purpose="assistants"
        )
    else:
        # Handle local file path
        try:
            with open(file_path, "rb") as file_content:
                result = client.files.create(
                    file=file_content,
                    purpose="assistants"
                )
        except Exception as e:
            print(f"Error uploading file {file_path}: {str(e)}")
            return None
            
    print(f"Successfully uploaded file: {file_path}, File ID: {result.id}")
    return result.id

def create_vector_store(client, name="research_vector_store"):
    """
    Create a vector store with OpenAI.
    
    Args:
        client: The OpenAI client
        name: Name for the vector store
        
    Returns:
        The vector store object
    """
    print(f"Creating vector store: {name}")
    try:
        vector_store = client.vector_stores.create(
            name=name
        )
        print(f"Vector store created with ID: {vector_store.id}")
        return vector_store
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        return None

def add_file_to_vector_store(client, vector_store_id, file_id):
    """
    Add a file to a vector store.
    
    Args:
        client: The OpenAI client
        vector_store_id: ID of the vector store
        file_id: ID of the file to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        result = client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
        print(f"Added file {file_id} to vector store {vector_store_id}")
        return True
    except Exception as e:
        print(f"Error adding file {file_id} to vector store: {str(e)}")
        return False

def check_file_status(client, vector_store_id):
    """
    Check the status of files in the vector store.
    
    Args:
        client: The OpenAI client
        vector_store_id: ID of the vector store
        
    Returns:
        True if all files are processed, False otherwise
    """
    try:
        result = client.vector_stores.files.list(
            vector_store_id=vector_store_id
        )
        
        all_completed = True
        for file in result.data:
            print(f"File {file.id} status: {file.status}")
            if file.status != "completed":
                all_completed = False
                
        return all_completed
    except Exception as e:
        print(f"Error checking file status: {str(e)}")
        return False

def search_files(client, vector_store_id, query, max_results=5):
    """
    Search the vector store with a query.
    
    Args:
        client: The OpenAI client
        vector_store_id: ID of the vector store
        query: The search query
        max_results: Maximum number of results to return
        
    Returns:
        The response object
    """
    print(f"Searching for: '{query}'")
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=query,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": max_results
            }],
            include=["output[*].file_search_call.search_results"]
        )
        return response
    except Exception as e:
        print(f"Error searching files: {str(e)}")
        return None

def main():
    # Get directory path from command line or use default
    if len(sys.argv) > 1:
        dir_path = sys.argv[1]
    else:
        dir_path = "./filesearchtest"
    
    # Create directory if it doesn't exist
    os.makedirs(dir_path, exist_ok=True)
    
    # Check if there are any markdown files in the directory
    markdown_files = glob.glob(os.path.join(dir_path, "*.md"))
    if not markdown_files:
        print(f"No markdown files found in {dir_path}. Please add some files before running.")
        print("You can copy consolidated summary files from a research_orchestrator run.")
        print("Example command to copy files:")
        print("cp research_output/your_topic_*/summaries/*.md filesearchtest/")
        return
    
    print(f"Found {len(markdown_files)} markdown files in {dir_path}")
    
    # Upload each file and collect file IDs
    file_ids = []
    for file_path in markdown_files:
        file_id = create_file(client, file_path)
        if file_id:
            file_ids.append(file_id)
    
    if not file_ids:
        print("No files were successfully uploaded. Exiting.")
        return
    
    # Create a vector store
    vector_store = create_vector_store(client)
    if not vector_store:
        print("Failed to create vector store. Exiting.")
        return
    
    # Add each file to the vector store
    for file_id in file_ids:
        add_file_to_vector_store(client, vector_store.id, file_id)
    
    # Wait for files to be processed
    print("Waiting for files to be processed...")
    all_completed = False
    max_checks = 20  # Prevent infinite loop
    check_count = 0
    
    while not all_completed and check_count < max_checks:
        check_count += 1
        all_completed = check_file_status(client, vector_store.id)
        if not all_completed:
            print(f"Files still processing. Checking again in 10 seconds... (Check {check_count}/{max_checks})")
            time.sleep(10)
    
    if not all_completed:
        print("Some files are still not processed after maximum wait time. Continuing anyway.")
    else:
        print("All files have been processed successfully!")
    
    # Perform searches
    search_queries = [
        "What are the main topics covered in this research?",
        "Summarize the key findings from the research",
        "What are the limitations mentioned in the research?",
        "What methodology was used in this research?",
        # Add your own custom queries here
    ]
    
    for query in search_queries:
        response = search_files(client, vector_store.id, query)
        if response:
            # Extract the message content
            for output in response.output:
                if output.type == "message":
                    print("\n-----------------------------------------------------------")
                    print(f"QUERY: {query}")
                    print("-----------------------------------------------------------")
                    
                    # Extract and print the text content
                    for content_item in output.content:
                        if content_item.type == "output_text":
                            print(content_item.text)
                            
                            # Print any file citations
                            if hasattr(content_item, 'annotations') and content_item.annotations:
                                print("\nCitations:")
                                citation_files = set()
                                for annotation in content_item.annotations:
                                    if annotation.type == "file_citation":
                                        citation_files.add(annotation.filename)
                                
                                for filename in citation_files:
                                    print(f"- {filename}")
                    
                    print("-----------------------------------------------------------\n")
    
    print("File search test complete!")

if __name__ == "__main__":
    main()
