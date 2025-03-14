#!/usr/bin/env python3
# research_orchestrator.py
"""
Research Orchestrator

This script provides advanced research automation with two modes of operation:

1. Topic-Based Research Mode:
   - Takes a topic, perspective, and depth as inputs
   - Generates multiple research questions using Perplexity
   - Processes each question with efficient citation handling
   - Organizes everything in a topic-based folder structure

2. Direct Question Mode:
   - Takes one or more specific research questions directly
   - Processes each question with efficient citation handling
   - Can also read questions from a file (one per line)

Key Features:
- Parallel processing with configurable worker threads
- Rate limit protection with smart retry logic
- Citation deduplication across questions
- Comprehensive markdown outputs and indexes
- OpenAI file search integration (optional)

OpenAI Integration:
- Automatically uploads research outputs to OpenAI
- Creates vector stores for semantic search
- Tracks research projects in a JSON database
- Enables future applications to search and interact with research

Usage (Topic Mode):
    python research_orchestrator.py --topic "Kahua, the Construction Software Management Company" --perspective "Chief Product Officer" --depth 5

Usage (Direct Question Mode):
    python research_orchestrator.py --questions "What is quantum computing?" "How do quantum computers work?"
    
Usage (Questions from File):
    python research_orchestrator.py --questions questions.txt

OpenAI Integration Options:
    python research_orchestrator.py --topic "AI Ethics" --openai-integration enable
    python research_orchestrator.py --questions "What is climate change?" --openai-integration disable

Run with --help for more options.
"""

import os
import re
import time
import json
import uuid
import queue
import random
import argparse
import threading
import traceback
import sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try importing OpenAI for file search functionality
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    pass

import requests

# Import functions from perplexityresearch.py
from perplexityresearch import (
    create_run_subfolders,
    query_perplexity,
    generate_executive_summary,
    clean_thinking_sections
)

# API Keys
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ENABLE_OPENAI_INTEGRATION = os.getenv("ENABLE_OPENAI_INTEGRATION", "false").lower() in ("true", "1", "yes")
OPENAI_PROCESSING_MAX_CHECKS = int(os.getenv("OPENAI_PROCESSING_MAX_CHECKS", "10"))
OPENAI_PROCESSING_CHECK_INTERVAL = float(os.getenv("OPENAI_PROCESSING_CHECK_INTERVAL", "5.0"))

# Models
PERPLEXITY_RESEARCH_MODEL = os.getenv("PERPLEXITY_RESEARCH_MODEL", "sonar-deep-research")
PERPLEXITY_CLEANUP_MODEL = os.getenv("PERPLEXITY_CLEANUP_MODEL", "sonar-pro")

# Rate Limiting and Retry Configuration
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_INITIAL_RETRY_DELAY = float(os.getenv("API_INITIAL_RETRY_DELAY", "5.0"))
API_MAX_RETRY_DELAY = float(os.getenv("API_MAX_RETRY_DELAY", "60.0"))

# Citation Processing
MAX_CITATIONS = int(os.getenv("MAX_CITATIONS", "50"))
CITATION_TIMEOUT = float(os.getenv("CITATION_TIMEOUT", "300.0"))  # 5 minutes by default

# Project tracking
RESEARCH_PROJECTS_FILE = os.getenv("RESEARCH_PROJECTS_FILE", "research_projects.json")
OPENAI_FILE_UPLOAD_TIMEOUT = int(os.getenv("OPENAI_FILE_UPLOAD_TIMEOUT", "60"))
OPENAI_VECTORSTORE_CREATION_TIMEOUT = int(os.getenv("OPENAI_VECTORSTORE_CREATION_TIMEOUT", "60"))

# Thread safety
print_lock = threading.Lock()

# Terminal colors
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"

# Thread-safe print function
def safe_print(message):
    """Thread-safe print function."""
    with print_lock:
        print(message, flush=True)

def with_retry(func, *args, prefix="", **kwargs):
    """
    Wrapper for API calls that implements exponential backoff retry logic.
    Handles rate limiting errors gracefully.
    
    Args:
        func: The function to call
        *args: Arguments to pass to the function
        prefix: Prefix for log messages (e.g., "[Q1]")
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
    """
    retry_count = 0
    delay = API_INITIAL_RETRY_DELAY
    
    while True:
        try:
            return func(*args, **kwargs)
        
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limiting related errors
            is_rate_limit = any(phrase in error_msg for phrase in [
                "rate limit", "too many requests", "429", "throttl", 
                "quota exceeded", "too frequent", "timeout"
            ])
            
            # If we've reached max retries or it's not a rate limit error, raise the exception
            if retry_count >= API_MAX_RETRIES or not is_rate_limit:
                raise
            
            # Exponential backoff for retries
            retry_count += 1
            safe_print(f"{Colors.YELLOW}{prefix} Rate limit detected. Retrying in {delay:.1f} seconds... (Attempt {retry_count}/{API_MAX_RETRIES}){Colors.RESET}")
            time.sleep(delay)
            
            # Increase delay for next retry (exponential backoff with jitter)
            delay = min(delay * 2 * (0.5 + random.random()), API_MAX_RETRY_DELAY)

def research_pipeline(question, master_folder, question_number, total_questions, topic=None, perspective=None):
    """
    Phase 1 of the research process: Get initial research response for a question.
    Modified to stop after getting the research response - does not process citations.
    
    Args:
        question: The research question to process
        master_folder: Path to the master folder for output
        question_number: The question number (for logging and file names)
        total_questions: Total number of questions (for progress reporting)
        topic: Optional overall research topic for context
        perspective: Optional professional perspective for context
    
    Returns:
        A tuple of (success_flag, research_response, citations)
    """
    safe_print(f"\n{Colors.BOLD}{Colors.MAGENTA}[{question_number}/{total_questions}] Researching: '{question}'{Colors.RESET}")
    
    try:
        # Set up paths for this question
        safe_question = re.sub(r'[^\w\s-]', '', question)
        safe_question = re.sub(r'[-\s]+', '_', safe_question).strip('-_')
        safe_question = safe_question[:30] if len(safe_question) > 30 else safe_question
        
        # Change prefix from Q to A to make files sort to the top
        question_prefix = f"A{question_number:02d}_"
        prefix = f"[Q{question_number}]"  # Keep this as Q for log messages for clarity
        
        # Timestamp not needed for individual questions as they're in the master folder
        response_dir = os.path.join(master_folder, "response")
        markdown_dir = os.path.join(master_folder, "markdown")
        
        # STEP 1: Call Perplexity with 'research' model for the initial research
        safe_print(f"{Colors.CYAN}{prefix} Starting research...{Colors.RESET}")
        
        # Create enhanced prompt with context if topic is provided
        if topic:
            context_prompt = f"""
Research Question: {question}

CONTEXT:
- Overall Research Topic: {topic}
- Professional Perspective: {perspective or "Researcher"}

Please perform comprehensive, detailed research on the question above, considering the overall research topic and professional perspective provided in the context. Your answer should be thorough, well-structured, and directly relevant to both the specific question and the broader research goals.
"""
        else:
            context_prompt = question
            
        research_response = with_retry(
            query_perplexity,
            prompt=context_prompt,
            model=PERPLEXITY_RESEARCH_MODEL,
            system_prompt="You are a professional researcher providing comprehensive, accurate information. Focus on delivering a thorough analysis that considers both the specific question and its context within the broader research topic.",
            is_research=True,
            prefix=prefix
        )
        
        # Dump the main research response JSON to file
        research_filename = os.path.join(response_dir, f"{question_prefix}research_response.json")
        with open(research_filename, "w", encoding="utf-8") as f:
            json.dump(research_response, f, indent=2)
        safe_print(f"{Colors.GREEN}{prefix} Saved main Perplexity research response.{Colors.RESET}")
        
        # STEP 2: Extract citations from the root level of the response
        citations = research_response.get("citations", [])
        safe_print(f"{Colors.BOLD}{Colors.CYAN}{prefix} Found {len(citations)} citation(s).{Colors.RESET}")

        # Get the main content and clean it of thinking sections
        main_content = ""
        if research_response.get("choices") and len(research_response["choices"]) > 0:
            raw_content = research_response["choices"][0]["message"].get("content", "")
            main_content = clean_thinking_sections(raw_content)
        
        # Save the cleaned research summary
        summary_md_path = os.path.join(markdown_dir, f"{question_prefix}research_summary.md")
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(f"# Research Summary: {question}\n\n")
            # Make sure the content is clean of thinking sections again before writing
            cleaned_content = clean_thinking_sections(main_content)
            f.write(cleaned_content)
            f.write("\n\n## Citation Links\n\n")
            for i, url in enumerate(citations, 1):
                f.write(f"{i}. [{url}]({url})\n")
        safe_print(f"{Colors.GREEN}{prefix} Saved research summary.{Colors.RESET}")

        # Generate executive summary
        safe_print(f"{Colors.CYAN}{prefix} Generating executive summary...{Colors.RESET}")
        exec_summary = with_retry(
            generate_executive_summary,
            question, main_content, PERPLEXITY_CLEANUP_MODEL,
            prefix=prefix
        )
        
        # Save the executive summary separately with new naming convention
        exec_summary_prefix = f"ES{question_number}_"
        exec_summary_path = os.path.join(markdown_dir, f"{exec_summary_prefix}executive_summary.md")
        with open(exec_summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Executive Summary: {question}\n\n")
            # Clean the executive summary of any thinking sections before writing
            cleaned_exec_summary = clean_thinking_sections(exec_summary)
            f.write(cleaned_exec_summary)
        safe_print(f"{Colors.GREEN}{prefix} Saved executive summary.{Colors.RESET}")

        # Create a question metadata file with citations
        metadata = {
            "question": question,
            "question_number": question_number,
            "citations": citations,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }
        metadata_path = os.path.join(response_dir, f"{question_prefix}metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        safe_print(f"\n{Colors.BOLD}{Colors.GREEN}{prefix} Question research phase completed successfully.{Colors.RESET}")
        return True, research_response, citations
    
    except Exception as e:
        safe_print(f"{Colors.RED}Error in research pipeline for question {question_number}: {str(e)}{Colors.RESET}")
        with print_lock:
            traceback.print_exc()
        return False, None, []

def create_master_index(master_folder, questions, results):
    """
    Create a master index of all questions and their research outputs.
    
    Args:
        master_folder: The master folder path
        questions: List of research questions
        results: List of (success_flag, research_response, citations) tuples
    
    Returns:
        Path to the created index file
    """
    markdown_dir = os.path.join(master_folder, "markdown")
    index_path = os.path.join(markdown_dir, "master_index.md")
    
    # Get timestamp for the report
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Research Project Results\n\n")
        f.write(f"Generated on: {timestamp}\n\n")
        
        # Count of successful questions
        successful_count = sum(1 for success, _, _ in results if success)
        f.write(f"Successfully processed {successful_count} out of {len(questions)} questions.\n\n")
        
        # Table of contents
        f.write("## Table of Contents\n\n")
        for i, question in enumerate(questions, 1):
            success = results[i-1][0] if i-1 < len(results) else False
            status = "✅" if success else "❌"
            # Clean any thinking sections from the question
            clean_question = clean_thinking_sections(question)
            f.write(f"{i}. {status} [Q{i:02d}: {clean_question[:80]}{'...' if len(clean_question) > 80 else ''}](#q{i:02d})\n")
        
        f.write("\n---\n\n")
        
        # Question details
        for i, question in enumerate(questions, 1):
            f.write(f"## Q{i:02d}\n\n")
            success, research_response, citations = results[i-1] if i-1 < len(results) else (False, None, [])
            
            # Clean any thinking sections from the question
            clean_question = clean_thinking_sections(question)
            f.write(f"**Question**: {clean_question}\n\n")
            
            if not success:
                f.write("**Status**: ❌ Processing failed\n\n")
                continue
                
            f.write("**Status**: ✅ Successfully processed\n\n")
            
            # Citations
            if citations:
                f.write(f"**Citations**: {len(citations)}\n\n")
                f.write("| # | Citation URL |\n")
                f.write("|---|-------------|\n")
                for j, citation in enumerate(citations, 1):
                    f.write(f"| {j} | [{citation[:60]}...]({citation}) |\n")
            else:
                f.write("**Citations**: None found\n\n")
                
            # Links to outputs - updated to use A prefix instead of Q
            question_prefix = f"A{i:02d}_"
            f.write("\n**Research Outputs**:\n\n")
            f.write(f"- [Research Summary]({question_prefix}research_summary.md)\n")
            f.write(f"- [Executive Summary]({question_prefix}executive_summary.md)\n")
            
            f.write("\n---\n\n")
    
    safe_print(f"{Colors.GREEN}Created master index at {index_path}{Colors.RESET}")
    return index_path

def intelligent_scrape(client, url):
    """
    Intelligently scrape content from a URL using Firecrawl.
    
    Args:
        client: FirecrawlApp instance
        url: URL to scrape
        
    Returns:
        Dictionary with scraped content or None if failed
    """
    try:
        # The new FirecrawlApp.scrape_url returns a dictionary with 'markdown' and 'metadata' keys
        result = client.scrape_url(url)
        
        # Check if result is a dictionary with 'markdown' key (this matches our expected format)
        if isinstance(result, dict) and "markdown" in result:
            return result
        
        # If no content was extracted, try with waitFor parameter
        try:
            # Try with a longer wait time for dynamic content
            result = client.scrape_url(url, waitFor=5000)
            
            # Check if the new attempt succeeded
            if isinstance(result, dict) and "markdown" in result:
                return result
        except Exception as inner_e:
            safe_print(f"Error with waitFor parameter: {str(inner_e)}")
        
        # If all else fails, attempt to salvage whatever content we got
        if result:
            if hasattr(result, 'data') and hasattr(result.data, 'content'):
                return {"markdown": result.data.content}
            elif isinstance(result, str):
                return {"markdown": result}
        
        return None
    except Exception as e:
        safe_print(f"{Colors.RED}Error scraping URL {url}: {str(e)}{Colors.RESET}")
        return None

def cleanup_citation_with_perplexity(content, citation_url, question_context):
    """
    Clean up citation content using Perplexity API.
    
    Args:
        content: The raw markdown content from the citation
        citation_url: URL of the citation for reference
        question_context: List of question data for context
    
    Returns:
        Formatted content as a string or None if formatting fails
    """
    try:
        safe_print(f"  ↳ Cleaning up citation content with Perplexity: {citation_url[:60]}...")
        
        # Prepare the list of questions for context
        questions_text = "\n".join([f"- Question {q.get('question_number', 0)}: {q.get('question', 'Unknown')}" 
                                  for q in question_context[:3]])  # Limit to first 3 for brevity
        
        # If there are more questions, add a note
        if len(question_context) > 3:
            questions_text += f"\n- Plus {len(question_context) - 3} more questions"
        
        # Create the prompt for Perplexity
        prompt = f"""
I have extracted content from a web page citation. Please clean up this content to make it more readable
and relevant to my research questions. Remove any boilerplate text, navigation elements, ads, or other
irrelevant content. Format the result as clean markdown.

Research questions I'm investigating:
{questions_text}

Citation URL: {citation_url}

CONTENT TO CLEAN UP:
{content[:15000]}  # Limit content length to avoid token limits
"""
        
        # Call Perplexity with the cleanup model
        response = with_retry(
            query_perplexity,
            prompt=prompt,
            model=PERPLEXITY_CLEANUP_MODEL,
            system_prompt="You are a professional content formatter. Clean up and format citation content to be well-structured, relevant, and readable. Remove boilerplate, ads, navigation elements, and irrelevant content.",
            is_research=False,
            prefix="[Citation Cleanup]"
        )
        
        # Extract the cleaned content
        if response and "choices" in response and len(response["choices"]) > 0:
            cleaned_content = response["choices"][0]["message"].get("content", "")
            # Clean any thinking sections from the response
            cleaned_content = clean_thinking_sections(cleaned_content)
            
            if cleaned_content:
                safe_print(f"  ↳ Successfully cleaned up citation content: {len(cleaned_content)} characters")
                return cleaned_content
        
        safe_print(f"  ↳ Failed to get a valid response from Perplexity for cleanup")
        return None
        
    except Exception as e:
        safe_print(f"  ↳ Error during citation cleanup: {str(e)}")
        return None

def process_citation(citation_url, question_context, master_folder, citation_id, total_citations, prefix=""):
    """
    Process a citation URL by scraping its content and formatting it with Perplexity.
    
    Args:
        citation_url: URL to process
        question_context: Context about the research question
        master_folder: Path to the master folder
        citation_id: Numeric ID of this citation
        total_citations: Total number of citations being processed
        prefix: Prefix for log messages
        
    Returns:
        Tuple of (success, citation_data, formatted_content)
    """
    # Validate citation URL
    if not citation_url or not isinstance(citation_url, str):
        safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] Invalid citation URL: {citation_url}")
        return False, None, None
    
    # Basic URL validation
    if not citation_url.startswith(('http://', 'https://')):
        safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] Invalid URL format: {citation_url}")
        return False, None, None
    
    try:
        # Progress tracking
        safe_print(f"{prefix}⏳ [Citation {citation_id}/{total_citations}] Processing: {citation_url}")
        
        # Step 0: Preliminary URL testing
        safe_print(f"{prefix}  ↳ Step 1/6: Testing URL accessibility...")
        is_accessible, status_code, content_type, message = test_citation_url(citation_url)
        
        if not is_accessible and status_code is not None:
            safe_print(f"{prefix}  ↳ ⚠️ URL test: {message} (Status: {status_code}, Content-Type: {content_type})")
            if status_code >= 400:  # Client or server error
                safe_print(f"{prefix}  ↳ ❌ URL returned error status {status_code}")
                return False, {"error": message, "status_code": status_code}, None
        elif not is_accessible:
            safe_print(f"{prefix}  ↳ ⚠️ URL test: {message}")
            # We'll still try to proceed with Firecrawl as it has more sophisticated scraping
        else:
            safe_print(f"{prefix}  ↳ ✅ URL test successful: {message}")
        
        # Phase 1: Web scraping with Firecrawl
        safe_print(f"{prefix}  ↳ Step 2/6: Preparing to scrape URL...")
        try:
            from firecrawl import FirecrawlApp
            api_key = os.getenv("FIRECRAWL_API_KEY")
            client = FirecrawlApp(api_key=api_key)
        except Exception as e:
            safe_print(f"{prefix}  ↳ ❌ Error initializing Firecrawl client: {str(e)}")
            return False, None, None
        
        # Perform the scraping
        safe_print(f"{prefix}  ↳ Step 3/6: Scraping web content...")
        try:
            citation_data = intelligent_scrape(client, citation_url)
            if not citation_data or not citation_data.get("markdown"):
                safe_print(f"{prefix}  ↳ ❌ Failed to extract content from URL")
                return False, citation_data or {"error": "No content extracted"}, None
            
            content_length = len(citation_data.get("markdown", ""))
            safe_print(f"{prefix}  ↳ ✅ Successfully scraped content: {content_length} characters")
            
            # If content is too short, it's likely not useful
            if content_length < 100:
                safe_print(f"{prefix}  ↳ ⚠️ Warning: Content is very short ({content_length} chars)")
        except Exception as e:
            safe_print(f"{prefix}  ↳ ❌ Error during web scraping: {str(e)}")
            return False, {"error": str(e)}, None
            
        # Phase 2: Content cleaning with Perplexity
        safe_print(f"{prefix}  ↳ Step 4/6: Preparing content for cleanup...")
        # Prepare content and context for Perplexity
        content = citation_data.get("markdown", "")
        if not content:
            safe_print(f"{prefix}  ↳ ❌ No content extracted from URL")
            return False, citation_data, None
            
        # Format the content
        safe_print(f"{prefix}  ↳ Step 5/6: Cleaning up content with Perplexity...")
        try:
            formatted_content = cleanup_citation_with_perplexity(content, citation_url, question_context)
            if not formatted_content:
                safe_print(f"{prefix}  ↳ ❌ Failed to format content")
                return False, citation_data, None
            safe_print(f"{prefix}  ↳ ✅ Successfully formatted content: {len(formatted_content)} characters")
        except Exception as e:
            safe_print(f"{prefix}  ↳ ❌ Error during content formatting: {str(e)}")
            return False, citation_data, None
            
        # Phase 3: File saving
        safe_print(f"{prefix}  ↳ Step 6/6: Saving citation content to files...")
        try:
            # Save the raw markdown
            markdown_path = os.path.join(master_folder, "markdown", f"C{citation_id:03d}_raw.md")
            os.makedirs(os.path.dirname(markdown_path), exist_ok=True)
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(f"# Citation {citation_id}: {citation_url}\n\n")
                f.write(content)
                
            # Save the formatted content
            formatted_path = os.path.join(master_folder, "markdown", f"C{citation_id:03d}_formatted.md")
            with open(formatted_path, "w", encoding="utf-8") as f:
                f.write(f"# Citation {citation_id}: {citation_url}\n\n")
                f.write(formatted_content)
                
            # Create citation metadata
            metadata_path = os.path.join(master_folder, "response", f"C{citation_id:03d}_metadata.json")
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            metadata = {
                "citation_id": citation_id,
                "url": citation_url,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "status_code": status_code,
                "content_type": content_type,
                "content_length": len(content),
                "formatted_length": len(formatted_content),
                "questions": [{'question': q.get('question', 'Unknown'), 
                              'question_number': q.get('question_number', 0)} 
                             for q in question_context]
            }
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
                
            safe_print(f"{prefix}✅ [Citation {citation_id}/{total_citations}] Successfully processed: {citation_url}")
            return True, citation_data, formatted_content
        except Exception as e:
            safe_print(f"{prefix}  ↳ ❌ Error saving files: {str(e)}")
            return False, citation_data, formatted_content
            
    except Exception as e:
        safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] Error: {str(e)}")
        return False, None, None

def extract_and_deduplicate_citations(all_questions_results):
    """
    Phase 2: Extract and deduplicate all citations from research responses.
    Also ranks citations by frequency of reference.
    
    Args:
        all_questions_results: List of tuples (success_flag, research_response, citations)
    
    Returns:
        Tuple of (citation_map, unique_citation_count)
    """
    citation_map = {}
    
    for idx, (success, response, citations) in enumerate(all_questions_results):
        if not success or not citations:
            continue
            
        question_number = idx + 1
        question = None
        
        # Extract the question from the response
        if response and "prompt" in response:
            question = response["prompt"]
        
        # If we couldn't extract the question, use a placeholder
        if not question:
            question = f"Question {question_number}"
            
        # Add each citation to the map
        # Handle both string citations and list/array citations
        if isinstance(citations, list):
            for citation in citations:
                # Ensure the citation is a string
                if not isinstance(citation, str):
                    safe_print(f"{Colors.YELLOW}Warning: Skipping non-string citation: {citation} (type: {type(citation)}){Colors.RESET}")
                    continue
                    
                if citation not in citation_map:
                    citation_map[citation] = []
                    
                citation_map[citation].append({
                    "question": question,
                    "question_number": question_number
                })
        elif isinstance(citations, str):
            # Handle a single citation string
            if citations not in citation_map:
                citation_map[citations] = []
                
            citation_map[citations].append({
                "question": question,
                "question_number": question_number
            })
        else:
            safe_print(f"{Colors.YELLOW}Warning: Unknown citation format: {type(citations)}{Colors.RESET}")
    
    unique_citation_count = len(citation_map)
    return citation_map, unique_citation_count

def prioritize_citations(citation_map, max_citations=50):
    """
    Prioritize citations based on frequency of reference and return top N.
    
    Args:
        citation_map: Dictionary mapping citations to list of referencing questions
        max_citations: Maximum number of citations to process
        
    Returns:
        Tuple of (prioritized_citations, skipped_count)
    """
    # Sort citations by number of references (descending)
    sorted_citations = sorted(
        citation_map.items(), 
        key=lambda item: len(item[1]), 
        reverse=True
    )
    
    # Take top N citations
    prioritized_citations = dict(sorted_citations[:max_citations])
    skipped_count = len(sorted_citations) - max_citations if len(sorted_citations) > max_citations else 0
    
    return prioritized_citations, skipped_count

def with_timeout(func, *args, **kwargs):
    """
    Execute a function with a timeout limit.
    
    Args:
        func: The function to call
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call or a timeout error result
    """
    import queue
    import threading
    
    # Extract timeout from kwargs or use default
    timeout = kwargs.pop('timeout', 300) if 'timeout' in kwargs else args[0]
    # Remove timeout from args if it's the first argument
    if len(args) > 0 and isinstance(args[0], (int, float)):
        args = args[1:]
    
    # Debug the arguments
    safe_print(f"{Colors.YELLOW}Debug - Inside with_timeout - func: {func.__name__}, timeout: {timeout}{Colors.RESET}")
    
    # For process_citation function, extract parameters for better debugging
    if func == process_citation and len(args) > 0:
        citation_url = args[0]
        citation_id = args[3] if len(args) > 3 else "unknown"
        total_citations = args[4] if len(args) > 4 else "unknown"
        prefix = kwargs.get("prefix", args[5] if len(args) > 5 else "")
        
        # Debug the citation URL
        safe_print(f"{Colors.YELLOW}Debug - Citation URL: {citation_url} (type: {type(citation_url)}){Colors.RESET}")
        
        # Validate citation URL type
        if not citation_url or not isinstance(citation_url, str):
            error_msg = f"Invalid citation URL type: {type(citation_url)}"
            safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] {error_msg}")
            return {
                "citation_id": citation_id,
                "url": str(citation_url),
                "success": False,
                "content": f"# Error Processing Citation\n\n**Error details**: {error_msg}\n\n",
                "error": error_msg
            }
        
        # Basic URL validation
        if not citation_url.startswith(('http://', 'https://')):
            error_msg = f"Invalid URL format: {citation_url}"
            safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] {error_msg}")
            return {
                "citation_id": citation_id,
                "url": citation_url,
                "success": False,
                "content": f"# Error Processing Citation\n\n**Error details**: {error_msg}\n\n",
                "error": error_msg
            }
        
        # Additional URL validation for common issues
        invalid_patterns = [
            'javascript:', 'mailto:', 'tel:', 'file:', 'data:',  # Non-web protocols
            'undefined', 'null', '[object', '127.0.0.1', 'localhost'  # Common invalid values
        ]
        
        for pattern in invalid_patterns:
            if pattern in citation_url.lower():
                error_msg = f"Invalid URL content: Contains '{pattern}'"
                safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] {error_msg}")
                return {
                    "citation_id": citation_id,
                    "url": citation_url,
                    "success": False,
                    "content": f"# Error Processing Citation\n\n**Error details**: {error_msg}\n\n",
                    "error": error_msg
                }
    
    safe_print(f"{prefix}⏱️ Starting function with {timeout}s timeout: {func.__name__}")
    result_queue = queue.Queue()
    
    # Worker function to execute the target function
    def worker():
        try:
            result = func(*args, **kwargs)
            result_queue.put(("success", result))
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            result_queue.put(("error", str(e), error_traceback))
    
    # Create and start the worker thread
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    try:
        # Wait for the result with timeout
        result_type, *result_data = result_queue.get(timeout=timeout)
        
        if result_type == "success":
            result = result_data[0]
            
            # Convert tuple result from process_citation to dictionary format
            if func == process_citation and isinstance(result, tuple) and len(result) == 3:
                success, citation_data, formatted_content = result
                citation_url = args[0]
                citation_id = args[3] if len(args) > 3 else "unknown"
                
                # Create a dictionary result
                return {
                    "citation_id": citation_id,
                    "url": str(citation_url),
                    "success": success,
                    "content": formatted_content or f"# Error Processing Citation\n\nNo content was extracted from this citation.",
                    "citation_data": citation_data,
                    "error": None if success else "Citation processing failed"
                }
            
            return result
        else:
            # Handle error case
            error_msg, error_traceback = result_data
            
            # For process_citation function, return structured error result
            if func == process_citation and len(args) > 0:
                citation_url = args[0]
                citation_id = args[3] if len(args) > 3 else "unknown"
                total_citations = args[4] if len(args) > 4 else "unknown"
                prefix = kwargs.get("prefix", args[5] if len(args) > 5 else "")
                
                safe_print(f"{prefix}❌ [Citation {citation_id}/{total_citations}] Error: {error_msg}")
                return {
                    "citation_id": citation_id,
                    "url": str(citation_url),
                    "success": False,
                    "content": f"# Error Processing Citation\n\n**Error details**: {error_msg}\n\n**Traceback**:\n```\n{error_traceback}\n```\n",
                    "error": error_msg
                }
            else:
                # For other functions, re-raise the exception
                raise Exception(f"Error in {func.__name__}: {error_msg}\n{error_traceback}")
    except queue.Empty:
        # Handle timeout case
        thread.join(0.1)  # Give the thread a moment to clean up
        
        # For process_citation function, return structured timeout result
        if func == process_citation and len(args) > 0:
            citation_url = args[0]
            citation_id = args[3] if len(args) > 3 else "unknown"
            total_citations = args[4] if len(args) > 4 else "unknown"
            prefix = kwargs.get("prefix", args[5] if len(args) > 5 else "")
            
            error_msg = f"Timeout after {timeout} seconds"
            safe_print(f"{prefix}⏱️ [Citation {citation_id}/{total_citations}] {error_msg}")
            return {
                "citation_id": citation_id,
                "url": str(citation_url),
                "success": False,
                "content": f"# Timeout Processing Citation\n\n**Error details**: {error_msg}\n\n",
                "error": error_msg,
                "timeout": True
            }
        else:
            # For other functions, raise a timeout exception
            raise TimeoutError(f"Function {func.__name__} timed out after {timeout} seconds")

def create_citation_index(master_folder, citation_map, citation_results, skipped_count=0):
    """
    Create an index of all citations in Markdown format.
    
    Args:
        master_folder: The master folder for output
        citation_map: Mapping of citations to questions (full map)
        citation_results: Results from processing citations (prioritized ones)
        skipped_count: Number of citations that were skipped due to prioritization
    """
    markdown_dir = os.path.join(master_folder, "markdown")
    citation_index_path = os.path.join(markdown_dir, "citation_index.md")
    
    # Count different types of failures
    timeout_count = 0
    http_error_count = 0
    scraping_error_count = 0
    other_error_count = 0
    
    for result in citation_results:
        # Handle both dictionary and tuple results for backward compatibility
        if isinstance(result, tuple) and len(result) == 3:
            success, _, _ = result
            if not success:
                other_error_count += 1
            continue
            
        # Handle dictionary results
        if not result.get("success", False):
            error_msg = result.get("error", "").lower()
            
            if result.get("timeout", False) or "timeout" in error_msg:
                timeout_count += 1
            elif "status" in error_msg and any(code in error_msg for code in ["403", "404", "429", "500"]):
                http_error_count += 1
            elif any(term in error_msg for term in ["scrape", "extract", "content"]):
                scraping_error_count += 1
            else:
                other_error_count += 1
    
    with open(citation_index_path, "w", encoding="utf-8") as f:
        f.write("# Citation Index\n\n")
        f.write("This document indexes all unique citations found during research.\n\n")
        
        # Add processing statistics
        # Handle both dictionary and tuple results for backward compatibility
        successful_count = sum(1 for r in citation_results if (
            isinstance(r, dict) and r.get("success", False) or
            isinstance(r, tuple) and len(r) == 3 and r[0]
        ))
        failed_count = len(citation_results) - successful_count
        
        f.write("## Processing Statistics\n\n")
        f.write(f"- **Total unique citations found**: {len(citation_map)}\n")
        f.write(f"- **Citations processed**: {len(citation_results)} ({skipped_count} skipped due to prioritization)\n")
        f.write(f"- **Successfully processed**: {successful_count} ({successful_count/max(1, len(citation_results))*100:.1f}%)\n")
        f.write(f"- **Failed processing**: {failed_count} ({failed_count/max(1, len(citation_results))*100:.1f}%)\n")
        
        if failed_count > 0:
            f.write("\n### Failure Categories\n\n")
            f.write(f"- **Timeouts**: {timeout_count} ({timeout_count/max(1, failed_count)*100:.1f}% of failures)\n")
            f.write(f"- **HTTP Errors**: {http_error_count} ({http_error_count/max(1, failed_count)*100:.1f}% of failures)\n")
            f.write(f"- **Scraping Errors**: {scraping_error_count} ({scraping_error_count/max(1, failed_count)*100:.1f}% of failures)\n")
            f.write(f"- **Other Errors**: {other_error_count} ({other_error_count/max(1, failed_count)*100:.1f}% of failures)\n")
        
        if skipped_count > 0:
            f.write(f"\n**Note**: {skipped_count} less referenced citations were not processed to optimize API usage and processing time.\n\n")
        
        # Create sections
        f.write("\n## Processed Citations\n\n")
        f.write("These citations were processed and have content available:\n\n")
        
        # Create a table of contents for processed citations
        for i, citation_result in enumerate(citation_results, 1):
            citation_url = citation_result["url"]
            success = citation_result.get("success", False)
            success_mark = "✅" if success else "❌"
            ref_count = len(citation_map.get(citation_url, []))
            
            # Add error type indicator for failed citations
            error_indicator = ""
            if not success:
                error_type = citation_result.get("error_type", "")
                error_msg = citation_result.get("error", "").lower()
                
                if error_type == "Timeout" or "timeout" in error_msg:
                    error_indicator = " [Timeout]"
                elif "status" in error_msg and any(code in error_msg for code in ["403", "404", "429", "500"]):
                    error_indicator = f" [HTTP Error]"
                elif any(term in error_msg for term in ["scrape", "extract", "content"]):
                    error_indicator = " [Scraping Error]"
                else:
                    error_indicator = " [Other Error]"
            
            f.write(f"{i}. {success_mark} [Citation {i}: {citation_url[:60]}...](#citation-{i}) (Referenced by {ref_count} questions){error_indicator}\n")
        
        f.write("\n---\n\n")
        
        # Add detailed entries for each processed citation
        for i, citation_result in enumerate(citation_results, 1):
            citation_url = citation_result["url"]
            success = citation_result.get("success", False)
            success_status = "Successfully processed" if success else "Processing failed"
            
            f.write(f"## Citation {i}\n\n")
            f.write(f"**URL**: [{citation_url}]({citation_url})\n\n")
            f.write(f"**Status**: {success_status}\n\n")
            
            # Add error details for failed citations
            if not success:
                error_msg = citation_result.get("error", "Unknown error")
                error_type = citation_result.get("error_type", "")
                status_code = citation_result.get("status_code")
                
                f.write(f"**Error**: {error_msg}\n\n")
                
                if error_type:
                    f.write(f"**Error Type**: {error_type}\n\n")
                
                if status_code:
                    f.write(f"**HTTP Status Code**: {status_code}\n\n")
                
                # Add troubleshooting suggestions based on error type
                f.write("**Troubleshooting Suggestions**:\n\n")
                
                if error_type == "Timeout" or "timeout" in error_msg.lower():
                    f.write("- Consider increasing the `CITATION_TIMEOUT` value in your .env file\n")
                    f.write("- The website might be slow to respond or have a lot of content\n")
                    f.write("- Try accessing the URL manually to check if it's responsive\n")
                elif status_code == 403:
                    f.write("- This website is blocking automated access (403 Forbidden)\n")
                    f.write("- The site may have anti-scraping measures in place\n")
                    f.write("- Try accessing manually to verify the content is accessible\n")
                elif status_code == 404:
                    f.write("- The page was not found (404 Not Found)\n")
                    f.write("- The URL might be incorrect or the content may have been removed\n")
                elif status_code == 429:
                    f.write("- The website is rate limiting requests (429 Too Many Requests)\n")
                    f.write("- Try increasing the `THREAD_STAGGER_DELAY` in your .env file\n")
                    f.write("- Reduce the number of worker threads to avoid rate limiting\n")
                elif "ssl" in error_msg.lower():
                    f.write("- SSL/TLS certificate validation failed\n")
                    f.write("- The website might have an invalid or expired certificate\n")
                elif any(term in error_msg.lower() for term in ["scrape", "extract", "content"]):
                    f.write("- Content extraction failed\n")
                    f.write("- The website might use complex JavaScript or have anti-scraping measures\n")
                    f.write("- Try accessing the URL manually to check the content\n")
                else:
                    f.write("- Check if the URL is accessible in a regular browser\n")
                    f.write("- The website might be temporarily unavailable\n")
                    f.write("- Consider retrying the citation processing later\n")
            
            # List referencing questions
            questions = citation_map.get(citation_url, [])
            f.write(f"**Referenced by {len(questions)} questions**:\n\n")
            for q in questions:
                # Clean any thinking sections from the question
                clean_question = clean_thinking_sections(q['question'])
                f.write(f"- Q{q['question_number']:02d}: {clean_question}\n")
            
            # Add links to the raw and formatted files if successful
            if success:
                raw_path = f"C{i:03d}_raw.md"
                formatted_path = f"C{i:03d}_formatted.md"
                
                f.write("\n**Files**:\n\n")
                f.write(f"- [Raw content]({raw_path})\n")
                f.write(f"- [Formatted content]({formatted_path})\n")
            
            f.write("\n---\n\n")
        
        # Create a section for skipped citations if any
        if skipped_count > 0:
            f.write("## Skipped Citations\n\n")
            f.write("These citations were found but not processed due to prioritization:\n\n")
            
            # Get URLs of processed citations
            processed_urls = [result["url"] for result in citation_results]
            
            # Find skipped citations
            skipped_citation_items = [
                (url, refs) for url, refs in citation_map.items() 
                if url not in processed_urls
            ]
            
            # Sort by reference count (descending)
            skipped_citation_items.sort(key=lambda x: len(x[1]), reverse=True)
            
            # List them
            for i, (url, refs) in enumerate(skipped_citation_items, 1):
                ref_count = len(refs)
                f.write(f"{i}. [{url[:60]}...]({url}) (Referenced by {ref_count} questions)\n")
    
    safe_print(f"{Colors.GREEN}Created citation index with all {len(citation_map)} citations.{Colors.RESET}")
    return citation_index_path

def consolidate_summary_files(master_folder, pattern, output_filename, title):
    """
    Consolidate all files matching a pattern in the markdown directory into a single file.
    
    Args:
        master_folder: The master folder for the research project
        pattern: Regex pattern to match filenames (e.g., "executive_summary")
        output_filename: Name of the output file
        title: Title for the consolidated file
    
    Returns:
        Path to the consolidated file
    """
    markdown_dir = os.path.join(master_folder, "markdown")
    summaries_dir = os.path.join(master_folder, "summaries")
    os.makedirs(summaries_dir, exist_ok=True)
    
    # Find all files matching the pattern
    summary_files = []
    for filename in os.listdir(markdown_dir):
        if pattern in filename.lower() and filename.endswith(".md"):
            summary_files.append(filename)
    
    # Sort files by question number (handling both A01_ and ES1_ formats)
    def extract_question_number(filename):
        # Try to match ES{number}_ format first (for executive summaries)
        es_match = re.search(r'ES(\d+)_', filename)
        if es_match:
            return int(es_match.group(1))
        
        # Try to match A{number}_ format next (for research summaries)
        a_match = re.search(r'A(\d+)_', filename)
        if a_match:
            return int(a_match.group(1))
            
        # If neither pattern matches, put at the end
        return 999
    
    summary_files.sort(key=extract_question_number)
    
    # Create a consolidated markdown file
    output_file = os.path.join(summaries_dir, output_filename)
    
    # Write a header for the consolidated file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# {title}\n\n")
        outfile.write(f"This document contains all {pattern} files from the research project.\n\n")
        outfile.write("---\n\n")
        
        # Read and append each summary file
        for i, filename in enumerate(summary_files, 1):
            file_path = os.path.join(markdown_dir, filename)
            
            # Extract question number if available (handle both formats)
            question_num = None
            es_match = re.search(r'ES(\d+)_', filename)
            if es_match:
                question_num = es_match.group(1)
            else:
                a_match = re.search(r'A(\d+)_', filename)
                if a_match:
                    question_num = a_match.group(1)
                    
            question_label = f"Question {question_num}" if question_num else f"Summary {i}"
            
            # Add a divider between summaries (except before the first one)
            if i > 1:
                outfile.write("\n\n---\n\n")
            
            outfile.write(f"## {question_label}\n\n")
            
            # Read and append the file content, skipping the original title
            with open(file_path, 'r', encoding='utf-8') as infile:
                content = infile.read()
                
                # Skip the original title (assumes first line is a markdown title)
                lines = content.split('\n')
                if lines and lines[0].startswith('# '):
                    content = '\n'.join(lines[1:])
                
                # Clean any thinking sections from the content
                content = clean_thinking_sections(content)
                
                outfile.write(content.strip())
    
    safe_print(f"{Colors.GREEN}Consolidated {len(summary_files)} {pattern} files into: {output_file}{Colors.RESET}")
    return output_file

def move_file(source_path, dest_dir):
    """
    Move a file from source path to destination directory.
    
    Args:
        source_path: Path to the source file
        dest_dir: Destination directory
        
    Returns:
        Path to the moved file
    """
    os.makedirs(dest_dir, exist_ok=True)
    filename = os.path.basename(source_path)
    dest_path = os.path.join(dest_dir, filename)
    
    # Read the original file
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Write to the new location
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # If write was successful, delete the original file (optional)
    # os.remove(source_path)
    
    safe_print(f"{Colors.GREEN}Moved {filename} to {dest_dir}{Colors.RESET}")
    return dest_path

def generate_research_questions(topic, perspective, depth):
    """
    Generates research questions using Perplexity API.
    Returns a list of questions.
    """
    safe_print(f"{Colors.BLUE}Generating research questions for topic: {topic}{Colors.RESET}")
    safe_print(f"{Colors.BLUE}From perspective: {perspective}{Colors.RESET}")
    safe_print(f"{Colors.BLUE}Number of questions requested: {depth}{Colors.RESET}")
    
    # Construct the prompt for Perplexity
    prompt = f"""
I'm going to be doing deep research on {topic}. From the perspective of a {perspective}. 
Give me {depth} interesting research questions to dive into. 

Embed each question in [[[<question>]]] and just show the {depth} questions with no other text. 
Start from the most general questions ("What is {topic}?") to increasingly specific questions that are relevant based on the perspective of a {perspective}. 
Good research on a company, as an example, would focus on competitors as well the industry and other key factors. It might also ask specificquestions about each module of the software. Research on other topics should be similarly thorough.
First think deeply and mentally mind map this project deeply across all facets then begin.
"""
    
    # Query Perplexity for questions
    try:
        # Use the retry wrapper for API call
        response = with_retry(
            query_perplexity,
            prompt=prompt,
            model=PERPLEXITY_RESEARCH_MODEL,
            system_prompt="You are a professional research question generator. Create insightful and specific questions.",
            is_research=False,  # We don't need the long timeout for this
            prefix="[Question Generation]"
        )
        
        # Extract the content from the response
        content = ""
        if response.get("choices") and len(response["choices"]) > 0:
            content = response["choices"][0]["message"].get("content", "")
        
        # Clean any thinking sections
        content = clean_thinking_sections(content)
        
        # Extract questions using regex
        questions = re.findall(r'\[\[\[(.*?)\]\]\]', content, re.DOTALL)
        
        # Clean up questions (remove extra whitespace, etc.)
        questions = [q.strip() for q in questions]
        
        safe_print(f"{Colors.GREEN}Generated {len(questions)} research questions.{Colors.RESET}")
        return questions
        
    except Exception as e:
        safe_print(f"{Colors.RED}Error generating research questions: {str(e)}{Colors.RESET}")
        return []

def load_project_tracking():
    """
    Load the project tracking data from JSON file.
    If file doesn't exist, create a new one with default structure.
    
    Returns:
        dict: The project tracking data
    """
    if os.path.exists(RESEARCH_PROJECTS_FILE):
        try:
            with open(RESEARCH_PROJECTS_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception as e:
            safe_print(f"{Colors.YELLOW}Warning: Could not load project tracking file: {str(e)}{Colors.RESET}")
            
    # Create new tracking file with default structure
    data = {
        "version": "1.0",
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "projects": []
    }
    
    # Save the new file
    try:
        with open(RESEARCH_PROJECTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        safe_print(f"{Colors.YELLOW}Warning: Could not create project tracking file: {str(e)}{Colors.RESET}")
    
    return data

def get_project_by_id(project_id):
    """
    Retrieve a project from the tracking file by its ID.
    
    Args:
        project_id (str): The ID of the project to retrieve
    
    Returns:
        dict: The project data or None if not found
    """
    try:
        # Load existing tracking data
        tracking_data = load_project_tracking()
        
        # Find the project by ID
        for project in tracking_data.get("projects", []):
            if project.get("id") == project_id:
                return project
        
        safe_print(f"{Colors.YELLOW}Warning: Project with ID {project_id} not found in tracking file{Colors.RESET}")
        return None
    except Exception as e:
        safe_print(f"{Colors.RED}Error retrieving project by ID: {str(e)}{Colors.RESET}")
        return None

def get_project_folder(project_data):
    """
    Get the folder path for an existing project.
    
    Args:
        project_data (dict): The project data
    
    Returns:
        str: The project folder path or None if not found
    """
    try:
        # Check if the project has local storage information
        local_storage = project_data.get("local_storage", {})
        folder_path = local_storage.get("folder")
        
        if not folder_path:
            safe_print(f"{Colors.YELLOW}Warning: Project does not have a folder path in its data{Colors.RESET}")
            return None
            
        # Verify the folder exists
        if not os.path.exists(folder_path):
            safe_print(f"{Colors.YELLOW}Warning: Project folder does not exist: {folder_path}{Colors.RESET}")
            return None
            
        return folder_path
    except Exception as e:
        safe_print(f"{Colors.RED}Error retrieving project folder: {str(e)}{Colors.RESET}")
        return None

def process_new_files_with_openai(master_folder, project_data, start_question_number, question_count):
    """
    Process only new research files with OpenAI: upload files, add to vector store, and update tracking.
    
    Args:
        master_folder: Folder containing the research project
        project_data: Project data dictionary
        start_question_number: The starting question number for the new questions
        question_count: The number of new questions added
        
    Returns:
        Updated project data with OpenAI integration info
    """
    # Preserve the active status if it exists
    active_status = project_data.get("active", True)
    
    if not ENABLE_OPENAI_INTEGRATION:
        safe_print(f"{Colors.YELLOW}OpenAI integration is disabled. Set ENABLE_OPENAI_INTEGRATION=true to enable.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "disabled"}
        project_data["active"] = active_status
        return project_data
        
    if not OPENAI_AVAILABLE:
        safe_print(f"{Colors.YELLOW}OpenAI package is not installed. Run 'pip install openai' to enable this feature.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "unavailable", "reason": "openai package not installed"}
        project_data["active"] = active_status
        return project_data
        
    if not OPENAI_API_KEY:
        safe_print(f"{Colors.YELLOW}OPENAI_API_KEY is not set in environment. Add it to your .env file.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "unavailable", "reason": "api key not configured"}
        project_data["active"] = active_status
        return project_data
    
    # Create OpenAI client
    client = create_openai_client()
    if not client:
        safe_print(f"{Colors.RED}Failed to create OpenAI client. OpenAI integration will be skipped.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "error", "reason": "client creation failed"}
        project_data["active"] = active_status
        return project_data
    
    prefix = "[OpenAI]"
    safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PHASE 5: OPENAI FILE PROCESSING (NEW FILES ONLY) ========{Colors.RESET}")
    
    # Get project ID
    project_id = project_data.get("id")
    if not project_id:
        safe_print(f"{Colors.RED}{prefix} Project ID not found in project data. OpenAI integration will be skipped.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "error", "reason": "project id missing"}
        project_data["active"] = active_status
        return project_data
    
    # Check if project already has OpenAI integration
    existing_integration = project_data.get("openai_integration", {})
    existing_file_ids = existing_integration.get("file_ids", {"readme": None, "markdown_files": [], "summary_files": []})
    existing_vector_store = existing_integration.get("vector_store", {})
    vector_store_id = existing_vector_store.get("id")
    
    if not vector_store_id:
        safe_print(f"{Colors.YELLOW}{prefix} No existing vector store found. Will need to create a new one.{Colors.RESET}")
        # Fall back to regular process_files_with_openai
        return process_files_with_openai(master_folder, project_data)
    
    # Step 1: Upload only the new files to OpenAI
    safe_print(f"{Colors.CYAN}{prefix} Uploading new files to OpenAI...{Colors.RESET}")
    
    new_file_ids = {
        "readme": None,  # We'll update this from the readme only if it doesn't exist already
        "markdown_files": [],
        "summary_files": []
    }
    
    # Upload README.md if it doesn't exist already
    if not existing_file_ids.get("readme"):
        readme_path = os.path.join(master_folder, "README.md")
        if os.path.exists(readme_path):
            file_id = upload_file_to_openai(client, readme_path, prefix)
            if file_id:
                new_file_ids["readme"] = file_id
                safe_print(f"{Colors.GREEN}{prefix} Uploaded README.md: {file_id}{Colors.RESET}")
    
    # Upload only the new markdown files for the new questions
    markdown_folder = os.path.join(master_folder, "markdown")
    if os.path.exists(markdown_folder):
        for i in range(start_question_number, start_question_number + question_count):
            # Pattern for markdown files: Q01_markdown.md, Q02_markdown.md, etc.
            file_pattern = f"Q{i:02d}_"
            for filename in os.listdir(markdown_folder):
                if filename.endswith(".md") and file_pattern in filename:
                    file_path = os.path.join(markdown_folder, filename)
                    file_id = upload_file_to_openai(client, file_path, prefix)
                    if file_id:
                        new_file_ids["markdown_files"].append(file_id)
                        safe_print(f"{Colors.GREEN}{prefix} Uploaded new markdown file: {filename}{Colors.RESET}")
    
    # Upload only the new summary files in the summaries folder
    summaries_folder = os.path.join(master_folder, "summaries")
    if os.path.exists(summaries_folder):
        # Upload consolidated files and any files related to new questions
        for filename in os.listdir(summaries_folder):
            # Only upload files that are consolidated summaries or related to new questions
            if filename.endswith(".md") and (
                filename.startswith("consolidated_") or
                "master_index" in filename or
                "citation_index" in filename or
                any(f"ES{i}_" in filename for i in range(start_question_number, start_question_number + question_count))
            ):
                file_path = os.path.join(summaries_folder, filename)
                file_id = upload_file_to_openai(client, file_path, prefix)
                if file_id:
                    new_file_ids["summary_files"].append(file_id)
                    safe_print(f"{Colors.GREEN}{prefix} Uploaded new summary file: {filename}{Colors.RESET}")
    
    # Count total uploaded files
    total_new_files = (1 if new_file_ids["readme"] else 0) + len(new_file_ids["markdown_files"]) + len(new_file_ids["summary_files"])
    safe_print(f"{Colors.GREEN}{prefix} Successfully uploaded {total_new_files} new files to OpenAI.{Colors.RESET}")
    
    # If no new files were uploaded, just return the existing project data
    if total_new_files == 0:
        safe_print(f"{Colors.YELLOW}{prefix} No new files were uploaded. Keeping existing vector store.{Colors.RESET}")
        project_data["active"] = active_status
        return project_data
    
    # Step 3: Add new files to existing vector store
    safe_print(f"{Colors.CYAN}{prefix} Adding new files to existing vector store...{Colors.RESET}")
    
    # Collect all new file IDs
    all_new_file_ids = []
    if new_file_ids["readme"]:
        all_new_file_ids.append(new_file_ids["readme"])
    all_new_file_ids.extend(new_file_ids["markdown_files"])
    all_new_file_ids.extend(new_file_ids["summary_files"])
    
    added_count = add_files_to_vector_store(client, vector_store_id, all_new_file_ids, prefix)
    safe_print(f"{Colors.GREEN}{prefix} Added {added_count} new files to vector store.{Colors.RESET}")
    
    if added_count == 0:
        safe_print(f"{Colors.RED}{prefix} Failed to add any new files to vector store.{Colors.RESET}")
        project_data["active"] = active_status
        return project_data
    
    # Step 4: Wait for files to be processed
    safe_print(f"{Colors.CYAN}{prefix} Waiting for files to be processed...{Colors.RESET}")
    all_completed = False
    max_checks = OPENAI_PROCESSING_MAX_CHECKS
    check_interval = OPENAI_PROCESSING_CHECK_INTERVAL
    check_count = 0
    
    while not all_completed and check_count < max_checks:
        check_count += 1
        all_completed = check_files_processing_status(client, vector_store_id, prefix)
        
        if not all_completed:
            safe_print(f"{Colors.CYAN}{prefix} Files still processing. Checking again in {check_interval} seconds... (Check {check_count}/{max_checks}){Colors.RESET}")
            time.sleep(check_interval)
    
    # Merge new file IDs with existing file IDs
    merged_file_ids = {
        "readme": new_file_ids["readme"] or existing_file_ids.get("readme"),
        "markdown_files": existing_file_ids.get("markdown_files", []) + new_file_ids["markdown_files"],
        "summary_files": existing_file_ids.get("summary_files", []) + new_file_ids["summary_files"]
    }
    
    # Update project tracking with updated vector store info
    vector_store_info = {
        "id": vector_store_id,
        "name": existing_vector_store.get("name"),
        "file_count": existing_vector_store.get("file_count", 0) + added_count,
        "processing_completed": all_completed
    }
    
    # Create update data that preserves project parameters
    update_data = {
        "openai_integration": {
            "status": "success",
            "file_ids": merged_file_ids,
            "vector_store": vector_store_info
        }
    }
    
    # Make sure we're not overwriting any other project data
    # Only update the openai_integration field in the tracking file
    update_project_in_tracking(project_id, update_data)
    
    # Add the vector store info to the project data
    project_data["openai_integration"] = {
        "status": "success",
        "file_ids": merged_file_ids,
        "vector_store": vector_store_info
    }
    
    # Ensure active status is preserved
    project_data["active"] = active_status
    
    if all_completed:
        safe_print(f"{Colors.BOLD}{Colors.GREEN}{prefix} All files have been processed successfully!{Colors.RESET}")
    else:
        safe_print(f"{Colors.YELLOW}{prefix} Some files are still not processed after maximum wait time. You can check status later.{Colors.RESET}")
    
    return project_data

def add_questions_to_project(project_data, new_questions, args):
    """
    Add new questions to an existing project.
    
    Args:
        project_data (dict): The existing project data
        new_questions (list): List of new questions to add
        args: Command-line arguments
    
    Returns:
        dict: Updated project data or None if failed
    """
    try:
        # Preserve the active status
        active_status = project_data.get("active", True)
        
        # Get the project folder
        master_folder = get_project_folder(project_data)
        if not master_folder:
            return None
            
        # Get existing questions
        existing_questions = project_data.get("parameters", {}).get("questions", [])
        
        # Calculate starting question number for new questions
        start_question_number = len(existing_questions) + 1
        
        # Update the project data with combined questions
        all_questions = existing_questions + new_questions
        project_data["parameters"]["questions"] = all_questions
        
        # Update the project status
        project_data["status"] = "in_progress"
        
        # Ensure active status is preserved
        project_data["active"] = active_status
        
        # Prepare updates for the tracking file
        # Get full parameters to preserve fields like topic, perspective, and depth
        parameters_update = project_data.get("parameters", {}).copy()
        parameters_update["questions"] = all_questions
        
        # Update the project in the tracking file
        update_project_in_tracking(project_data["id"], {
            "parameters": parameters_update,
            "status": "in_progress",
            "active": active_status
        })
        
        # Update the README to include new questions
        readme_path = os.path.join(master_folder, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                readme_content = f.read()
                
            # Check if README already has a Research Questions section
            if "## Research Questions" in readme_content:
                # Split the content at the Research Questions section
                parts = readme_content.split("## Research Questions")
                before_questions = parts[0] + "## Research Questions\n\n"
                
                # Create updated questions list
                questions_content = ""
                for i, q in enumerate(all_questions, 1):
                    questions_content += f"{i}. {q}\n"
                
                # Find the next section if any
                after_questions = ""
                if len(parts) > 1 and "##" in parts[1]:
                    after_parts = parts[1].split("##", 1)
                    after_questions = "##" + after_parts[1]
                
                # Write updated README
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(before_questions + questions_content + "\n" + after_questions)
            else:
                # Append Research Questions section to README
                with open(readme_path, "a", encoding="utf-8") as f:
                    f.write("\n## Research Questions\n\n")
                    for i, q in enumerate(all_questions, 1):
                        f.write(f"{i}. {q}\n")
        
        # Process the new questions
        safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PROCESSING NEW QUESTIONS ========{Colors.RESET}")
        safe_print(f"{Colors.CYAN}Adding {len(new_questions)} new questions to existing project{Colors.RESET}")
        
        # Load the rate limit settings
        RATE_LIMIT_QUESTIONS_PER_WORKER = int(os.getenv('RATE_LIMIT_QUESTIONS_PER_WORKER', 10))
        THREAD_STAGGER_DELAY = float(os.getenv('THREAD_STAGGER_DELAY', 5.0))
        
        # Override with command line args if provided
        if args.stagger_delay is not None:
            THREAD_STAGGER_DELAY = args.stagger_delay
            
        # Calculate max workers based on number of questions and rate limit
        if args.max_workers is not None:
            max_workers = args.max_workers
        else:
            max_workers = max(1, int(len(new_questions) / RATE_LIMIT_QUESTIONS_PER_WORKER))
        
        # Get topic and perspective if available
        topic = project_data.get("parameters", {}).get("topic")
        perspective = project_data.get("parameters", {}).get("perspective")
        
        # Process each new question
        all_question_results = []
        successful_questions = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a future for each question
            futures = {}
            for i, question in enumerate(new_questions, start_question_number):
                # Stagger the thread starts to avoid API rate limits
                if i > start_question_number and THREAD_STAGGER_DELAY > 0:
                    time.sleep(THREAD_STAGGER_DELAY)
                
                future = executor.submit(
                    research_pipeline,
                    question,
                    master_folder,
                    i,
                    len(all_questions),
                    topic,
                    perspective
                )
                futures[future] = (i, question)
            
            # Collect results as they complete
            for future in as_completed(futures):
                i, question = futures[future]
                try:
                    success, research_response, citations = future.result()
                    all_question_results.append((success, research_response, citations))
                    
                    if success:
                        successful_questions += 1
                        
                except Exception as e:
                    safe_print(f"{Colors.RED}Error processing question {i}: {str(e)}{Colors.RESET}")
                    all_question_results.append((False, None, []))
        
        # Extract and deduplicate citations from all questions
        safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== EXTRACTING CITATIONS FROM NEW QUESTIONS ========{Colors.RESET}")
        citation_map, unique_citation_count = extract_and_deduplicate_citations(all_question_results)
        
        # Process citations if there are any
        if citation_map:
            # Prioritize citations based on reference count
            prioritized_citation_map, skipped_count = prioritize_citations(citation_map, args.max_citations)
            
            # Check for skipped citations
            if skipped_count > 0:
                safe_print(f"{Colors.YELLOW}Skipping {skipped_count} less referenced citations to stay within limit of {args.max_citations}{Colors.RESET}")
            
            # Process each unique citation
            safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PROCESSING CITATIONS FROM NEW QUESTIONS ========{Colors.RESET}")
            citation_results = process_citations(prioritized_citation_map, master_folder, max_workers, THREAD_STAGGER_DELAY)
            
            # Create indexes
            master_index_path = create_master_index(master_folder, all_questions, all_question_results)
            citation_index_path = create_citation_index(master_folder, citation_map, citation_results, skipped_count)
            
            # Consolidate summaries
            safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== CONSOLIDATING SUMMARIES ========{Colors.RESET}")
            consolidate_summary_files(master_folder, "executive_summary", "consolidated_executive_summaries.md", "Consolidated Executive Summaries")
            consolidate_summary_files(master_folder, "research_summary", "consolidated_research_summaries.md", "Consolidated Research Summaries")
            
            # Move master index and citation index to summaries folder
            move_file(master_index_path, os.path.join(master_folder, "summaries"))
            move_file(citation_index_path, os.path.join(master_folder, "summaries"))
        else:
            safe_print(f"{Colors.YELLOW}No citations found in new questions. Skipping citation processing phase.{Colors.RESET}")
            # Create the master index even if there are no citations
            master_index_path = create_master_index(master_folder, all_questions, all_question_results)
            
            # Consolidate summary files and move master index
            safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== CONSOLIDATING SUMMARIES ========{Colors.RESET}")
            consolidate_summary_files(master_folder, "executive_summary", "consolidated_executive_summaries.md", "Consolidated Executive Summaries")
            consolidate_summary_files(master_folder, "research_summary", "consolidated_research_summaries.md", "Consolidated Research Summaries")
            move_file(master_index_path, os.path.join(master_folder, "summaries"))
        
        # Process files with OpenAI if enabled
        if ENABLE_OPENAI_INTEGRATION:
            # Use our new function that only processes the new files
            project_data = process_new_files_with_openai(master_folder, project_data, start_question_number, len(new_questions))
        
        # Update project status to completed
        project_data["status"] = "completed"
        update_project_in_tracking(project_data["id"], {"status": "completed"})
        
        safe_print(f"\n{Colors.BOLD}{Colors.GREEN}Successfully added {len(new_questions)} new questions to project.{Colors.RESET}")
        return project_data
        
    except Exception as e:
        safe_print(f"{Colors.RED}Error adding questions to project: {str(e)}{Colors.RESET}")
        with print_lock:
            traceback.print_exc()
        return None

def save_project_tracking(data):
    """
    Save the project tracking data to JSON file.
    
    Args:
        data (dict): The project tracking data to save
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Update the last_updated timestamp
    data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    try:
        with open(RESEARCH_PROJECTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        safe_print(f"{Colors.YELLOW}Warning: Could not save project tracking file: {str(e)}{Colors.RESET}")
        return False

def add_project_to_tracking(project_data):
    """
    Add a new project to the tracking file.
    
    Args:
        project_data (dict): Data about the research project
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load existing tracking data
        tracking_data = load_project_tracking()
        
        # Add the new project
        tracking_data["projects"].append(project_data)
        
        # Save the updated tracking data
        return save_project_tracking(tracking_data)
    except Exception as e:
        safe_print(f"{Colors.YELLOW}Warning: Could not add project to tracking file: {str(e)}{Colors.RESET}")
        return False

def update_project_in_tracking(project_id, updates):
    """
    Update an existing project in the tracking file.
    
    IMPORTANT: This function uses dict.update() which replaces entire nested objects.
    For example, if you pass {"parameters": {"questions": [...]}}, it will replace the
    entire "parameters" object, losing any other fields like "topic", "perspective", etc.
    Always copy the full object first before modifying it.
    
    Args:
        project_id (str): The ID of the project to update
        updates (dict): The data to update
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load existing tracking data
        tracking_data = load_project_tracking()
        
        # Find the project by ID
        for project in tracking_data["projects"]:
            if project.get("id") == project_id:
                # Update the project data
                project.update(updates)
                # Save the updated tracking data
                return save_project_tracking(tracking_data)
        
        safe_print(f"{Colors.YELLOW}Warning: Project with ID {project_id} not found in tracking file{Colors.RESET}")
        return False
    except Exception as e:
        safe_print(f"{Colors.YELLOW}Warning: Could not update project in tracking file: {str(e)}{Colors.RESET}")
        return False

def create_openai_client():
    """
    Create an OpenAI client instance if OpenAI is available.
    
    Returns:
        OpenAI client or None if not available
    """
    if not OPENAI_AVAILABLE:
        safe_print(f"{Colors.YELLOW}OpenAI integration is not available: OpenAI package not installed{Colors.RESET}")
        return None
        
    if not OPENAI_API_KEY:
        safe_print(f"{Colors.YELLOW}OpenAI integration is not available: OPENAI_API_KEY not set in environment{Colors.RESET}")
        return None
        
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        return client
    except Exception as e:
        safe_print(f"{Colors.RED}Error creating OpenAI client: {str(e)}{Colors.RESET}")
        return None

def upload_file_to_openai(client, file_path, prefix=""):
    """
    Upload a file to OpenAI's API.
    
    Args:
        client: The OpenAI client
        file_path: Path to the file to upload
        prefix: Prefix for log messages
        
    Returns:
        The file ID or None if failed
    """
    try:
        safe_print(f"{Colors.CYAN}{prefix} Uploading file: {file_path}{Colors.RESET}")
        
        with open(file_path, "rb") as file_content:
            result = client.files.create(
                file=file_content,
                purpose="assistants"
            )
            
        safe_print(f"{Colors.GREEN}{prefix} Successfully uploaded file: {file_path}, File ID: {result.id}{Colors.RESET}")
        return result.id
    except Exception as e:
        safe_print(f"{Colors.RED}{prefix} Error uploading file {file_path}: {str(e)}{Colors.RESET}")
        return None

def upload_files_to_openai(client, project_folder, project_id, prefix=""):
    """
    Upload multiple files from a project folder to OpenAI.
    
    Args:
        client: The OpenAI client
        project_folder: The folder containing the research project
        project_id: The ID of the project for tracking
        prefix: Prefix for log messages
        
    Returns:
        Dictionary with uploaded file IDs
    """
    if not client:
        return None
        
    try:
        file_ids = {
            "readme": None,
            "markdown_files": [],
            "summary_files": []
        }
        
        # Upload README.md if it exists
        readme_path = os.path.join(project_folder, "README.md")
        if os.path.exists(readme_path):
            file_id = upload_file_to_openai(client, readme_path, prefix)
            if file_id:
                file_ids["readme"] = file_id
        
        # Upload markdown files
        markdown_folder = os.path.join(project_folder, "markdown")
        if os.path.exists(markdown_folder):
            for filename in os.listdir(markdown_folder):
                if filename.endswith(".md"):
                    file_path = os.path.join(markdown_folder, filename)
                    file_id = upload_file_to_openai(client, file_path, prefix)
                    if file_id:
                        file_ids["markdown_files"].append(file_id)
        
        # Upload summary files
        summaries_folder = os.path.join(project_folder, "summaries")
        if os.path.exists(summaries_folder):
            for filename in os.listdir(summaries_folder):
                if filename.endswith(".md"):
                    file_path = os.path.join(summaries_folder, filename)
                    file_id = upload_file_to_openai(client, file_path, prefix)
                    if file_id:
                        file_ids["summary_files"].append(file_id)
        
        # Update project tracking with file IDs
        update_data = {
            "openai_integration": {
                "file_ids": file_ids
            }
        }
        update_project_in_tracking(project_id, update_data)
        
        return file_ids
    except Exception as e:
        safe_print(f"{Colors.RED}{prefix} Error uploading files: {str(e)}{Colors.RESET}")
        return None

def create_vector_store(client, name, prefix=""):
    """
    Create a vector store with OpenAI.
    
    Args:
        client: The OpenAI client
        name: Name for the vector store
        prefix: Prefix for log messages
        
    Returns:
        The vector store object or None if failed
    """
    if not client:
        return None
        
    try:
        safe_print(f"{Colors.CYAN}{prefix} Creating vector store: {name}{Colors.RESET}")
        vector_store = client.vector_stores.create(name=name)
        safe_print(f"{Colors.GREEN}{prefix} Vector store created with ID: {vector_store.id}{Colors.RESET}")
        return vector_store
    except Exception as e:
        safe_print(f"{Colors.RED}{prefix} Error creating vector store: {str(e)}{Colors.RESET}")
        return None

def add_files_to_vector_store(client, vector_store_id, file_ids, prefix=""):
    """
    Add multiple files to a vector store.
    
    Args:
        client: The OpenAI client
        vector_store_id: ID of the vector store
        file_ids: List of file IDs to add
        prefix: Prefix for log messages
        
    Returns:
        Number of files successfully added
    """
    if not client or not vector_store_id or not file_ids:
        return 0
        
    added_count = 0
    
    for file_id in file_ids:
        try:
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            safe_print(f"{Colors.GREEN}{prefix} Added file {file_id} to vector store{Colors.RESET}")
            added_count += 1
        except Exception as e:
            safe_print(f"{Colors.RED}{prefix} Error adding file {file_id} to vector store: {str(e)}{Colors.RESET}")
    
    return added_count

def check_files_processing_status(client, vector_store_id, prefix=""):
    """
    Check if all files in a vector store have been processed.
    
    Args:
        client: The OpenAI client
        vector_store_id: The ID of the vector store
        prefix: Prefix for log messages
        
    Returns:
        bool: True if all files are processed, False otherwise
    """
    try:
        # Get the vector store - using updated API path
        vector_store = client.vector_stores.retrieve(vector_store_id)
        
        # Check file counts from the vector store object
        if hasattr(vector_store, 'file_counts'):
            # New API format
            in_progress = vector_store.file_counts.get('in_progress', 0)
            failed = vector_store.file_counts.get('failed', 0)
            cancelled = vector_store.file_counts.get('cancelled', 0)
            
            # If any files are still in progress or have failed, not all are completed
            if in_progress > 0:
                safe_print(f"{Colors.YELLOW}{prefix} Files still processing: {in_progress} in progress{Colors.RESET}")
                return False
                
            if failed > 0:
                safe_print(f"{Colors.YELLOW}{prefix} Some files failed processing: {failed} failed{Colors.RESET}")
                # We still consider the overall process "completed" even if some files failed
            
            # If we get here, processing is completed (even if some files failed)
            return True
        else:
            # Fallback to checking status directly
            if hasattr(vector_store, 'status') and vector_store.status == 'completed':
                return True
            else:
                safe_print(f"{Colors.YELLOW}{prefix} Vector store status: {getattr(vector_store, 'status', 'unknown')}{Colors.RESET}")
                return False
            
    except Exception as e:
        safe_print(f"{Colors.RED}{prefix} Error checking file processing status: {str(e)}{Colors.RESET}")
        # Consider it completed if we can't check (otherwise it might never complete)
        # This is a judgment call - could go either way depending on risk tolerance
        safe_print(f"{Colors.YELLOW}{prefix} Assuming processing is complete due to API error{Colors.RESET}")
        return True

def process_citations(prioritized_citation_map, master_folder, max_workers, thread_stagger_delay=5.0):
    """
    Process each unique citation in parallel.
    
    Args:
        prioritized_citation_map: Dictionary mapping citation URLs to question contexts
        master_folder: Path to the master folder
        max_workers: Maximum number of worker threads
        thread_stagger_delay: Delay between starting thread in seconds
        
    Returns:
        List of citation processing results
    """
    # Display citation processing parameters
    safe_print(f"{Colors.MAGENTA}Citation timeout: {CITATION_TIMEOUT} seconds per citation{Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Worker threads: {max_workers}{Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Thread stagger delay: {thread_stagger_delay} seconds{Colors.RESET}")
    
    # Process citations in parallel
    citation_results = []
    successful_citations = 0
    failed_citations = 0
    timeout_citations = 0
    
    # Create a progress tracking function
    def update_progress():
        total = len(prioritized_citation_map)
        completed = successful_citations + failed_citations
        if total == 0:
            return
        
        percent = int((completed / total) * 100)
        bar_length = 40
        filled_length = int(bar_length * completed / total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Clear the line and print the progress bar
        sys.stdout.write('\r')
        sys.stdout.write(f"{Colors.CYAN}Progress: [{bar}] {percent}% | ✅ {successful_citations} | ❌ {failed_citations} | ⏱️ {timeout_citations} | Total: {completed}/{total}{Colors.RESET}")
        sys.stdout.flush()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each unique citation
        futures = {}
        for i, (citation_url, question_context) in enumerate(prioritized_citation_map.items(), 1):
            # Stagger the thread starts to avoid API rate limits
            if i > 1 and thread_stagger_delay > 0:
                time.sleep(thread_stagger_delay)
                
            # For log message, show citation rank by reference count
            ref_count = len(question_context)
            
            # Debug output - print the citation URL and its type
            safe_print(f"{Colors.YELLOW}Debug - Before with_timeout - Citation {i}: {citation_url} (type: {type(citation_url)}){Colors.RESET}")
            
            # Use the timeout wrapper with a configurable timeout
            # This ensures no single citation can hang the entire process
            future = executor.submit(
                with_timeout,
                process_citation, 
                citation_url,
                question_context,
                master_folder,
                i,
                len(prioritized_citation_map),
                f"[Refs: {ref_count}]",
                timeout=CITATION_TIMEOUT  # Pass timeout as a keyword argument
            )
            futures[future] = (i, citation_url, ref_count)
            
        # Collect results as they complete
        for future in as_completed(futures):
            i, citation_url, ref_count = futures[future]
            try:
                result = future.result()
                citation_results.append(result)
                
                # Update counters based on result
                if result.get("success", False):
                    successful_citations += 1
                    success_indicator = Colors.GREEN + "✓"
                else:
                    failed_citations += 1
                    success_indicator = Colors.RED + "✗"
                    
                    # Check if it was a timeout
                    if result.get("error_type") == "Timeout":
                        timeout_citations += 1
                
                # Update progress bar
                update_progress()
                
                # Print detailed result
                safe_print(f"\n{success_indicator} Citation {i}/{len(prioritized_citation_map)} complete: {citation_url[:60]}... (Referenced by {ref_count} questions){Colors.RESET}")
                
                # Print error details if failed
                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error")
                    safe_print(f"{Colors.RED}  ↳ Error: {error_msg}{Colors.RESET}")
                    
            except Exception as e:
                failed_citations += 1
                citation_results.append({
                    "citation_id": i,
                    "url": citation_url,
                    "success": False,
                    "content": f"# Error Processing Citation\n\n**Error**: {str(e)}",
                    "error": str(e)
                })
                
                # Update progress bar
                update_progress()
                
                # Print error
                safe_print(f"\n{Colors.RED}✗ Citation {i}/{len(prioritized_citation_map)} failed: {citation_url[:60]}... (Referenced by {ref_count} questions){Colors.RESET}")
                safe_print(f"{Colors.RED}  ↳ Error: {str(e)}{Colors.RESET}")
    
    # Print final newline after progress bar
    print()
    
    # Count successful citations
    safe_print(f"\n{Colors.BOLD}{Colors.GREEN}Citation processing complete: Successfully processed {successful_citations} out of {len(prioritized_citation_map)} citations.{Colors.RESET}")
    
    # Print detailed statistics
    safe_print(f"{Colors.CYAN}Citation processing statistics:{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Successful: {successful_citations} ({successful_citations/max(1, len(prioritized_citation_map))*100:.1f}%){Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Failed: {failed_citations} ({failed_citations/max(1, len(prioritized_citation_map))*100:.1f}%){Colors.RESET}")
    safe_print(f"{Colors.CYAN}  - Timeouts: {timeout_citations} ({timeout_citations/max(1, len(prioritized_citation_map))*100:.1f}%){Colors.RESET}")
    safe_print(f"{Colors.CYAN}  - Other errors: {failed_citations - timeout_citations} ({(failed_citations - timeout_citations)/max(1, len(prioritized_citation_map))*100:.1f}%){Colors.RESET}")
    
    return citation_results

def process_files_with_openai(master_folder, project_data):
    """
    Process research files with OpenAI: upload files, create vector store, and update tracking.
    
    Args:
        master_folder: Folder containing the research project
        project_data: Project data dictionary
        
    Returns:
        Updated project data with OpenAI integration info
    """
    # Preserve the active status if it exists
    active_status = project_data.get("active", True)
    
    if not ENABLE_OPENAI_INTEGRATION:
        safe_print(f"{Colors.YELLOW}OpenAI integration is disabled. Set ENABLE_OPENAI_INTEGRATION=true to enable.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "disabled"}
        project_data["active"] = active_status
        return project_data
        
    if not OPENAI_AVAILABLE:
        safe_print(f"{Colors.YELLOW}OpenAI package is not installed. Run 'pip install openai' to enable this feature.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "unavailable", "reason": "openai package not installed"}
        project_data["active"] = active_status
        return project_data
        
    if not OPENAI_API_KEY:
        safe_print(f"{Colors.YELLOW}OPENAI_API_KEY is not set in environment. Add it to your .env file.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "unavailable", "reason": "api key not configured"}
        project_data["active"] = active_status
        return project_data
    
    # Create OpenAI client
    client = create_openai_client()
    if not client:
        safe_print(f"{Colors.RED}Failed to create OpenAI client. OpenAI integration will be skipped.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "error", "reason": "client creation failed"}
        project_data["active"] = active_status
        return project_data
    
    prefix = "[OpenAI]"
    safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PHASE 5: OPENAI FILE PROCESSING ========{Colors.RESET}")
    
    # Get project ID
    project_id = project_data.get("id")
    if not project_id:
        safe_print(f"{Colors.RED}{prefix} Project ID not found in project data. OpenAI integration will be skipped.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "error", "reason": "project id missing"}
        project_data["active"] = active_status
        return project_data
    
    # Step 1: Upload files to OpenAI
    safe_print(f"{Colors.CYAN}{prefix} Uploading files to OpenAI...{Colors.RESET}")
    file_ids = upload_files_to_openai(client, master_folder, project_id, prefix)
    
    if not file_ids:
        safe_print(f"{Colors.RED}{prefix} Failed to upload files to OpenAI.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "error", "reason": "file upload failed"}
        project_data["active"] = active_status
        return project_data
    
    # Count total uploaded files
    total_files = (1 if file_ids["readme"] else 0) + len(file_ids["markdown_files"]) + len(file_ids["summary_files"])
    safe_print(f"{Colors.GREEN}{prefix} Successfully uploaded {total_files} files to OpenAI.{Colors.RESET}")
    
    # If no files were uploaded, skip vector store creation
    if total_files == 0:
        safe_print(f"{Colors.YELLOW}{prefix} No files were uploaded. Skipping vector store creation.{Colors.RESET}")
        project_data["openai_integration"] = {"status": "no_files", "file_ids": file_ids}
        project_data["active"] = active_status
        return project_data
    
    # Step 2: Create vector store
    # Generate a name for the vector store based on topic or questions
    if project_data.get("parameters", {}).get("topic"):
        topic = project_data["parameters"]["topic"]
    else:
        # Use first question as topic (truncated)
        first_question = project_data.get("parameters", {}).get("questions", ["Research"])[0]
        topic = first_question[:30].replace("?", "").strip()
    
    timestamp = project_data.get("timestamp", "").replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
    vector_store_name = f"{topic}_{timestamp}".replace(" ", "_")[:50]
    
    safe_print(f"{Colors.CYAN}{prefix} Creating vector store: {vector_store_name}{Colors.RESET}")
    vector_store = create_vector_store(client, vector_store_name, prefix)
    
    if not vector_store:
        safe_print(f"{Colors.RED}{prefix} Failed to create vector store.{Colors.RESET}")
        project_data["openai_integration"] = {
            "status": "partial",
            "file_ids": file_ids,
            "reason": "vector store creation failed"
        }
        project_data["active"] = active_status
        return project_data
    
    # Step 3: Add files to vector store
    safe_print(f"{Colors.CYAN}{prefix} Adding files to vector store...{Colors.RESET}")
    
    # Collect all file IDs
    all_file_ids = []
    if file_ids["readme"]:
        all_file_ids.append(file_ids["readme"])
    all_file_ids.extend(file_ids["markdown_files"])
    all_file_ids.extend(file_ids["summary_files"])
    
    added_count = add_files_to_vector_store(client, vector_store.id, all_file_ids, prefix)
    safe_print(f"{Colors.GREEN}{prefix} Added {added_count} files to vector store.{Colors.RESET}")
    
    if added_count == 0:
        safe_print(f"{Colors.RED}{prefix} Failed to add any files to vector store.{Colors.RESET}")
        project_data["openai_integration"] = {
            "status": "partial",
            "file_ids": file_ids,
            "vector_store": {
                "id": vector_store.id,
                "name": vector_store_name,
                "file_count": 0
            },
            "reason": "no files added to vector store"
        }
        project_data["active"] = active_status
        return project_data
    
    # Step 4: Wait for files to be processed
    safe_print(f"{Colors.CYAN}{prefix} Waiting for files to be processed...{Colors.RESET}")
    all_completed = False
    max_checks = OPENAI_PROCESSING_MAX_CHECKS
    check_interval = OPENAI_PROCESSING_CHECK_INTERVAL
    check_count = 0
    
    while not all_completed and check_count < max_checks:
        check_count += 1
        all_completed = check_files_processing_status(client, vector_store.id, prefix)
        
        if not all_completed:
            safe_print(f"{Colors.CYAN}{prefix} Files still processing. Checking again in {check_interval} seconds... (Check {check_count}/{max_checks}){Colors.RESET}")
            time.sleep(check_interval)
    
    # Update project tracking with vector store info
    vector_store_info = {
        "id": vector_store.id,
        "name": vector_store_name,
        "file_count": added_count,
        "processing_completed": all_completed
    }
    
    # Preserve the active status if it exists
    active_status = project_data.get("active", True)
    
    update_data = {
        "openai_integration": {
            "status": "success",
            "file_ids": file_ids,
            "vector_store": vector_store_info
        }
    }
    
    # Update the project with this info
    update_project_in_tracking(project_id, update_data)
    
    # Add the vector store info to the project data
    project_data["openai_integration"] = {
        "status": "success",
        "file_ids": file_ids,
        "vector_store": vector_store_info
    }
    
    # Ensure active status is preserved
    project_data["active"] = active_status
    
    if all_completed:
        safe_print(f"{Colors.BOLD}{Colors.GREEN}{prefix} All files have been processed successfully!{Colors.RESET}")
    else:
        safe_print(f"{Colors.YELLOW}{prefix} Some files are still not processed after maximum wait time. You can check status later.{Colors.RESET}")
    
    return project_data

def test_citation_url(url, timeout=10):
    """
    Test if a URL is accessible before attempting to scrape it.
    
    Args:
        url: The URL to test
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (is_accessible, status_code, content_type, error_message)
    """
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, None, None, "Invalid URL format"
    except Exception:
        return False, None, None, "URL parsing error"
    
    # Validate protocol
    if parsed.scheme not in ['http', 'https']:
        return False, None, None, f"Unsupported protocol: {parsed.scheme}"
    
    # Check common problematic domains
    problematic_domains = [
        'linkedin.com', 'facebook.com', 'instagram.com',  # Social media
        'jstor.org', 'springer.com', 'sciencedirect.com',  # Academic paywalls
        'pdfs.semanticscholar.org',  # PDF repositories
        'drive.google.com', 'docs.google.com'  # Google Docs/Drive
    ]
    
    domain = parsed.netloc.lower()
    for problem_domain in problematic_domains:
        if problem_domain in domain:
            return True, None, None, f"Warning: Potentially difficult domain {problem_domain}"
    
    # Try HEAD request first (faster)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        status_code = response.status_code
        content_type = response.headers.get('Content-Type', '')
        
        # Check status codes
        if 200 <= status_code < 300:
            if 'pdf' in content_type.lower():
                return True, status_code, content_type, "Warning: PDF content (may be difficult to process)"
            elif 'application/' in content_type.lower() and 'json' not in content_type.lower():
                return False, status_code, content_type, f"Warning: Binary content type: {content_type}"
            else:
                return True, status_code, content_type, "URL appears accessible"
        elif 300 <= status_code < 400:
            return False, status_code, content_type, f"Redirection error: {status_code}"
        elif status_code == 403:
            return False, status_code, content_type, "Access forbidden (403)"
        elif status_code == 404:
            return False, status_code, content_type, "Page not found (404)"
        elif status_code == 429:
            return False, status_code, content_type, "Rate limited (429)"
        else:
            return False, status_code, content_type, f"HTTP error: {status_code}"
            
    except requests.exceptions.Timeout:
        return False, None, None, "Connection timeout"
    except requests.exceptions.TooManyRedirects:
        return False, None, None, "Too many redirects"
    except requests.exceptions.SSLError:
        return False, None, None, "SSL certificate error"
    except requests.exceptions.ConnectionError:
        return False, None, None, "Connection error"
    except Exception as e:
        return False, None, None, f"Request error: {str(e)}"

def main():
    """
    Main entry point for the research orchestrator.
    Implements a three-phase workflow:
    1. Process all research questions to get initial responses
    2. Extract and deduplicate citations from all responses
    3. Process each unique citation once
    4. Consolidate outputs and generate summaries
    5. (Optional) Process files with OpenAI for vector search
    
    Supports three modes:
    - Direct question mode: Provide questions directly via command line or file
    - Topic mode: Generate questions based on a topic, perspective, and depth
    - Interactive mode: Prompt for topic, perspective, and depth when run without arguments
    """
    # Declare global variables
    global ENABLE_OPENAI_INTEGRATION
    
    # Create a unique ID for this research project right at the beginning
    # to ensure it's always available regardless of code path
    project_id = str(uuid.uuid4())
    
    parser = argparse.ArgumentParser(description="Research orchestrator for multiple questions.")
    
    # Create a mutually exclusive group for the two explicit modes
    mode_group = parser.add_mutually_exclusive_group(required=False)  # Changed to False to allow no args
    
    # Direct question mode args
    mode_group.add_argument("--questions", "-q", nargs="+", help="One or more research questions, or a filename containing questions (one per line)")
    
    # Topic mode args
    mode_group.add_argument("--topic", "-t", help="Research topic to generate questions for")
    parser.add_argument("--perspective", "-p", default="Researcher", help="Professional perspective (default: Researcher)")
    parser.add_argument("--depth", "-d", type=int, default=5, help="Number of questions to generate (default: 5)")
    
    # Common args
    parser.add_argument("--output", "-o", default="./research_output", help="Output directory (default: ./research_output)")
    parser.add_argument("--max-workers", "-w", type=int, default=None, help="Maximum number of worker threads (default: automatic based on number of questions)")
    parser.add_argument("--stagger-delay", "-s", type=float, default=None, help="Seconds to wait before starting each new thread (default: from .env)")
    parser.add_argument("--max-citations", "-c", type=int, default=MAX_CITATIONS, help=f"Maximum number of citations to process (default: {MAX_CITATIONS} from .env)")
    
    # OpenAI integration args
    parser.add_argument("--openai-integration", "-ai", choices=["enable", "disable"], help="Enable or disable OpenAI file processing (default: from .env)")
    
    # New args for existing project and adding questions
    parser.add_argument("--existing-project", "-ep", help="ID of an existing project to process with OpenAI integration or add questions to")
    parser.add_argument("--add-questions", "-aq", action="store_true", help="Add questions to an existing project (requires --existing-project)")
    
    args = parser.parse_args()
    
    # Override OpenAI integration setting from command line if provided
    if args.openai_integration:
        ENABLE_OPENAI_INTEGRATION = args.openai_integration == "enable"
    
    # Handle existing project processing
    if args.existing_project:
        project_data = get_project_by_id(args.existing_project)
        if not project_data:
            safe_print(f"{Colors.RED}Project with ID {args.existing_project} not found. Exiting.{Colors.RESET}")
            return None
            
        if args.add_questions:
            # Adding questions to existing project
            if not args.questions:
                safe_print(f"{Colors.RED}No questions provided. Use --questions option to specify questions or a file containing questions. Exiting.{Colors.RESET}")
                return None
                
            # Load questions (reuse existing code for loading questions from args.questions)
            questions = []
            if len(args.questions) == 1 and os.path.isfile(args.questions[0]):
                # Questions from file
                with open(args.questions[0], "r", encoding="utf-8") as f:
                    questions = [line.strip() for line in f.readlines() if line.strip()]
                safe_print(f"{Colors.GREEN}Loaded {len(questions)} questions from {args.questions[0]}{Colors.RESET}")
            else:
                # Questions from command line
                questions = args.questions
                
            if not questions:
                safe_print(f"{Colors.RED}No valid questions found. Exiting.{Colors.RESET}")
                return None
                
            # Add questions to existing project
            return add_questions_to_project(project_data, questions, args)
        else:
            # Process existing project with OpenAI integration
            master_folder = get_project_folder(project_data)
            if not master_folder:
                safe_print(f"{Colors.RED}Project folder not found for project {args.existing_project}. Exiting.{Colors.RESET}")
                return None
                
            # Enable OpenAI integration for this operation
            old_setting = ENABLE_OPENAI_INTEGRATION
            ENABLE_OPENAI_INTEGRATION = True
            
            safe_print(f"{Colors.BOLD}{Colors.CYAN}Processing existing project with OpenAI integration{Colors.RESET}")
            safe_print(f"{Colors.CYAN}Project ID: {args.existing_project}{Colors.RESET}")
            safe_print(f"{Colors.CYAN}Project folder: {master_folder}{Colors.RESET}")
            
            # Store the active status before processing
            active_status = project_data.get("active", True)
            
            # Process the project with OpenAI
            project_data = process_files_with_openai(master_folder, project_data)
            
            # Ensure the active status is preserved
            if "active" not in project_data:
                project_data["active"] = active_status
                # Update the tracking file with the active status
                update_project_in_tracking(project_data["id"], {"active": active_status})
            
            # Restore original setting
            ENABLE_OPENAI_INTEGRATION = old_setting
            
            return project_data
    
    # Determine which mode we're operating in
    questions = []
    
    if args.questions:
        # Direct question mode
        if len(args.questions) == 1 and os.path.isfile(args.questions[0]):
            # Questions from file
            with open(args.questions[0], "r", encoding="utf-8") as f:
                questions = [line.strip() for line in f.readlines() if line.strip()]
            safe_print(f"{Colors.GREEN}Loaded {len(questions)} questions from {args.questions[0]}{Colors.RESET}")
        else:
            # Questions from command line
            questions = args.questions
    elif args.topic:
        # Topic mode - generate questions
        safe_print(f"{Colors.BOLD}{Colors.BLUE}Generating questions for topic: {args.topic}{Colors.RESET}")
        questions = generate_research_questions(args.topic, args.perspective, args.depth)
        if not questions:
            safe_print(f"{Colors.RED}Failed to generate questions for topic. Exiting.{Colors.RESET}")
            # Create an empty project tracking entry with failure status
            project_data = {
                "id": project_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "parameters": {
                    "topic": args.topic,
                    "perspective": args.perspective,
                    "depth": args.depth,
                    "questions": []
                },
                "status": "failed",
                "reason": "Failed to generate questions for topic",
                "active": True
            }
            add_project_to_tracking(project_data)
            return project_data
        
        # Limit to the requested depth (in case API returned more)
        questions = questions[:args.depth]
        safe_print(f"{Colors.BOLD}{Colors.GREEN}Generated {len(questions)} questions for topic{Colors.RESET}")
    else:
        # Interactive mode - prompt for inputs
        safe_print(f"{Colors.BOLD}{Colors.BLUE}Welcome to the Research Orchestrator{Colors.RESET}")
        safe_print(f"{Colors.BLUE}Please select an option:{Colors.RESET}")
        safe_print(f"{Colors.CYAN}1. Create a new research project{Colors.RESET}")
        safe_print(f"{Colors.CYAN}2. Add questions to an existing project{Colors.RESET}")
        safe_print(f"{Colors.CYAN}3. Process an existing project with OpenAI integration{Colors.RESET}")
        
        option = input(f"{Colors.CYAN}Enter your choice (1-3): {Colors.RESET}").strip()
        
        if option == "1":
            # Create a new research project - original interactive mode
            safe_print(f"{Colors.BLUE}Creating a new research project. Please provide the following information:{Colors.RESET}")
            
            # Prompt for topic
            topic = input(f"{Colors.CYAN}Enter research topic: {Colors.RESET}").strip()
            if not topic:
                safe_print(f"{Colors.RED}Error: Topic is required.{Colors.RESET}")
                return

            # Prompt for perspective
            perspective = input(f"{Colors.CYAN}Enter professional perspective (or press Enter for 'Researcher'): {Colors.RESET}").strip()
            if not perspective:
                perspective = "Researcher"
                safe_print(f"{Colors.YELLOW}Using default perspective: {perspective}{Colors.RESET}")

            # Prompt for depth
            depth_input = input(f"{Colors.CYAN}Enter number of questions to generate (or press Enter for 5): {Colors.RESET}").strip()
            try:
                depth = int(depth_input) if depth_input else 5
                if depth < 1:
                    safe_print(f"{Colors.RED}Error: Depth must be at least 1. Using default of 5.{Colors.RESET}")
                    depth = 5
                elif depth > 50:
                    safe_print(f"{Colors.YELLOW}Warning: Large number of questions requested. This may take a long time.{Colors.RESET}")
            except ValueError:
                safe_print(f"{Colors.RED}Invalid number. Using default of 5.{Colors.RESET}")
                depth = 5
                
            # Prompt for max workers
            workers_input = input(f"{Colors.CYAN}Enter maximum number of worker threads (or press Enter for automatic): {Colors.RESET}").strip()
            if workers_input:
                try:
                    args.max_workers = int(workers_input)
                    if args.max_workers < 1:
                        safe_print(f"{Colors.RED}Error: Workers must be at least 1. Using automatic calculation.{Colors.RESET}")
                        args.max_workers = None
                except ValueError:
                    safe_print(f"{Colors.RED}Invalid number. Using automatic calculation.{Colors.RESET}")
            
            # Prompt for max citations
            citations_input = input(f"{Colors.CYAN}Enter maximum number of citations to process (or press Enter for 50): {Colors.RESET}").strip()
            if citations_input:
                try:
                    args.max_citations = int(citations_input)
                    if args.max_citations < 1:
                        safe_print(f"{Colors.RED}Error: Max citations must be at least 1. Using default of 50.{Colors.RESET}")
                        args.max_citations = 50
                except ValueError:
                    safe_print(f"{Colors.RED}Invalid number. Using default of 50.{Colors.RESET}")
            
            # Generate questions using the provided inputs
            safe_print(f"{Colors.BOLD}{Colors.BLUE}Generating questions for topic: {topic}{Colors.RESET}")
            questions = generate_research_questions(topic, perspective, depth)
            if not questions:
                safe_print(f"{Colors.RED}Failed to generate questions for topic. Exiting.{Colors.RESET}")
                # Create an empty project tracking entry with failure status
                project_data = {
                    "id": project_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "parameters": {
                        "topic": topic,
                        "perspective": perspective,
                        "depth": depth,
                        "questions": []
                    },
                    "status": "failed",
                    "reason": "Failed to generate questions for topic",
                    "active": True
                }
                add_project_to_tracking(project_data)
                return project_data
            
            # Limit to the requested depth (in case API returned more)
            questions = questions[:depth]
            safe_print(f"{Colors.BOLD}{Colors.GREEN}Generated {len(questions)} questions for topic{Colors.RESET}")
            
            # Save the values to args for later use
            args.topic = topic
            args.perspective = perspective
            args.depth = depth
            
        elif option == "2":
            # Add questions to an existing project
            safe_print(f"{Colors.BLUE}Adding questions to an existing project.{Colors.RESET}")
            
            # Load existing projects
            tracking_data = load_project_tracking()
            projects = tracking_data.get("projects", [])
            
            if not projects:
                safe_print(f"{Colors.RED}No existing projects found. Please create a new project first.{Colors.RESET}")
                return
            
            # Display available projects
            safe_print(f"{Colors.CYAN}Available projects:{Colors.RESET}")
            for i, project in enumerate(projects, 1):
                project_id = project.get("id", "Unknown")
                topic = project.get("parameters", {}).get("topic", "Research Project")
                timestamp = project.get("timestamp", "").split("T")[0]
                question_count = len(project.get("parameters", {}).get("questions", []))
                safe_print(f"{Colors.CYAN}{i}. {topic} ({timestamp}) - {question_count} questions - ID: {project_id}{Colors.RESET}")
            
            # Prompt for project selection
            project_input = input(f"{Colors.CYAN}Enter project number to select: {Colors.RESET}").strip()
            try:
                project_index = int(project_input) - 1
                if project_index < 0 or project_index >= len(projects):
                    safe_print(f"{Colors.RED}Invalid project number. Exiting.{Colors.RESET}")
                    return
                
                selected_project = projects[project_index]
                project_id = selected_project.get("id")
                
                # Prompt for questions file
                questions_file = input(f"{Colors.CYAN}Enter path to file containing questions (one per line): {Colors.RESET}").strip()
                if not questions_file or not os.path.isfile(questions_file):
                    safe_print(f"{Colors.RED}Invalid file path. Exiting.{Colors.RESET}")
                    return
                
                # Load questions from file
                with open(questions_file, "r", encoding="utf-8") as f:
                    questions = [line.strip() for line in f.readlines() if line.strip()]
                
                if not questions:
                    safe_print(f"{Colors.RED}No valid questions found in file. Exiting.{Colors.RESET}")
                    return
                
                safe_print(f"{Colors.GREEN}Loaded {len(questions)} questions from {questions_file}{Colors.RESET}")
                
                # Add questions to the selected project
                return add_questions_to_project(selected_project, questions, args)
                
            except ValueError:
                safe_print(f"{Colors.RED}Invalid input. Exiting.{Colors.RESET}")
                return
                
        elif option == "3":
            # Process an existing project with OpenAI integration
            safe_print(f"{Colors.BLUE}Processing an existing project with OpenAI integration.{Colors.RESET}")
            
            # Load existing projects
            tracking_data = load_project_tracking()
            projects = tracking_data.get("projects", [])
            
            if not projects:
                safe_print(f"{Colors.RED}No existing projects found. Please create a new project first.{Colors.RESET}")
                return
            
            # Display available projects
            safe_print(f"{Colors.CYAN}Available projects:{Colors.RESET}")
            for i, project in enumerate(projects, 1):
                project_id = project.get("id", "Unknown")
                topic = project.get("parameters", {}).get("topic", "Research Project")
                timestamp = project.get("timestamp", "").split("T")[0]
                openai_status = project.get("openai_integration", {}).get("status", "not processed")
                safe_print(f"{Colors.CYAN}{i}. {topic} ({timestamp}) - OpenAI: {openai_status} - ID: {project_id}{Colors.RESET}")
            
            # Prompt for project selection
            project_input = input(f"{Colors.CYAN}Enter project number to select: {Colors.RESET}").strip()
            try:
                project_index = int(project_input) - 1
                if project_index < 0 or project_index >= len(projects):
                    safe_print(f"{Colors.RED}Invalid project number. Exiting.{Colors.RESET}")
                    return
                
                selected_project = projects[project_index]
                project_id = selected_project.get("id")
                
                # Get the project folder
                master_folder = get_project_folder(selected_project)
                if not master_folder:
                    safe_print(f"{Colors.RED}Project folder not found. Exiting.{Colors.RESET}")
                    return
                
                # Enable OpenAI integration for this operation
                old_setting = ENABLE_OPENAI_INTEGRATION
                ENABLE_OPENAI_INTEGRATION = True
                
                safe_print(f"{Colors.BOLD}{Colors.CYAN}Processing project with OpenAI integration{Colors.RESET}")
                safe_print(f"{Colors.CYAN}Project ID: {project_id}{Colors.RESET}")
                safe_print(f"{Colors.CYAN}Project folder: {master_folder}{Colors.RESET}")
                
                # Store the active status before processing
                active_status = selected_project.get("active", True)
                
                # Process the project with OpenAI
                project_data = process_files_with_openai(master_folder, selected_project)
                
                # Ensure the active status is preserved
                if "active" not in project_data:
                    project_data["active"] = active_status
                    # Update the tracking file with the active status
                    update_project_in_tracking(project_data["id"], {"active": active_status})
                
                # Restore original setting
                ENABLE_OPENAI_INTEGRATION = old_setting
                
                return project_data
                
            except ValueError:
                safe_print(f"{Colors.RED}Invalid input. Exiting.{Colors.RESET}")
                return
        else:
            safe_print(f"{Colors.RED}Invalid option. Exiting.{Colors.RESET}")
            return

    if not questions:
        safe_print(f"{Colors.RED}No research questions provided. Exiting.{Colors.RESET}")
        # Create an empty project tracking entry with failure status
        project_data = {
            "id": project_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "parameters": {
                "questions": []
            },
            "status": "failed",
            "reason": "No research questions provided",
            "active": True
        }
        # Add topic, perspective, and depth if available
        if args.topic:
            project_data["parameters"]["topic"] = args.topic
            project_data["parameters"]["perspective"] = args.perspective
            project_data["parameters"]["depth"] = args.depth
        
        add_project_to_tracking(project_data)
        return project_data

    # Load the rate limit settings
    RATE_LIMIT_QUESTIONS_PER_WORKER = int(os.getenv('RATE_LIMIT_QUESTIONS_PER_WORKER', 10))
    THREAD_STAGGER_DELAY = float(os.getenv('THREAD_STAGGER_DELAY', 5.0))
    
    # Override with command line args if provided
    if args.stagger_delay is not None:
        THREAD_STAGGER_DELAY = args.stagger_delay
        
    # Calculate max workers based on number of questions and rate limit
    if args.max_workers is not None:
        max_workers = args.max_workers
    else:
        max_workers = max(1, int(len(questions) / RATE_LIMIT_QUESTIONS_PER_WORKER))
    
    # Create a descriptive folder name (with topic if available)
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    folder_prefix = "research"
    if args.topic:
        # Sanitize topic for folder name
        safe_topic = re.sub(r'[^\w\s-]', '', args.topic)
        safe_topic = re.sub(r'[-\s]+', '_', safe_topic).strip('-_')
        safe_topic = safe_topic[:30] if len(safe_topic) > 30 else safe_topic
        folder_prefix = safe_topic
    
    master_folder = os.path.join(os.path.abspath(args.output), f"{folder_prefix}_{timestamp}")
    
    # Create all required directories
    os.makedirs(master_folder, exist_ok=True)
    os.makedirs(os.path.join(master_folder, "response"), exist_ok=True)
    os.makedirs(os.path.join(master_folder, "markdown"), exist_ok=True)
    os.makedirs(os.path.join(master_folder, "summaries"), exist_ok=True)  # Added new summaries directory
    
    # Create a README for the project
    readme_path = os.path.join(master_folder, "README.md")
    topic_title = args.topic if args.topic else "Research Project"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# {topic_title}\n\n")
        f.write(f"**Generated on**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n")
        f.write(f"**Project ID**: {project_id}\n\n")

        if args.topic:
            f.write(f"**Topic**: {args.topic}\n\n")
            f.write(f"**Perspective**: {args.perspective}\n\n")
        
        f.write("## Folder Structure\n\n")
        f.write("- `markdown/`: Formatted markdown files for each research question\n")
        f.write("- `response/`: Raw API responses\n")
        f.write("- `summaries/`: Consolidated files and indexes\n\n")
        
        # Add OpenAI integration info if enabled
        if ENABLE_OPENAI_INTEGRATION:
            f.write("## OpenAI Integration\n\n")
            f.write("This research project has been integrated with OpenAI's file search capabilities:\n\n")
            f.write("- Research files have been uploaded to OpenAI\n")
            f.write("- A vector store has been created for semantic search\n")
            f.write("- Project tracking information is stored in the research_projects.json file\n\n")
            f.write("Use the project ID above when using the OpenAI search functionality.\n\n")
        
        f.write("## Research Questions\n\n")
        for i, q in enumerate(questions, 1):
            f.write(f"{i}. {q}\n")
    
    safe_print(f"{Colors.BOLD}{Colors.GREEN}Research orchestrator started at {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Processing {len(questions)} questions with a maximum of {max_workers} worker threads{Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Thread stagger delay: {THREAD_STAGGER_DELAY} seconds{Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Max citations to process: {args.max_citations} (prioritizing most referenced ones){Colors.RESET}")
    safe_print(f"{Colors.MAGENTA}Output directory: {master_folder}{Colors.RESET}")
    
    # Create a project data structure for tracking
    project_data = {
        "id": project_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parameters": {
            "questions": questions
        },
        "local_storage": {
            "folder": os.path.abspath(master_folder),
            "markdown_folder": "markdown",
            "summary_folder": "summaries",
            "response_folder": "response"
        },
        "status": "in_progress",
        "active": True
    }
    
    # Add topic, perspective, and depth if available
    if args.topic:
        project_data["parameters"]["topic"] = args.topic
        project_data["parameters"]["perspective"] = args.perspective
        project_data["parameters"]["depth"] = args.depth
    
    # Add project to tracking file
    add_project_to_tracking(project_data)
    
    # Initialize counter for successful questions
    successful_questions = 0
    
    ########## PHASE 1: Process all questions ##########
    safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PHASE 1: PROCESSING ALL QUESTIONS ========{Colors.RESET}")
    
    # Process each question with ThreadPoolExecutor
    all_question_results = []  # Store results as (success_flag, research_response, citations)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a future for each question
        futures = {}
        for i, question in enumerate(questions, 1):
            # Stagger the thread starts to avoid API rate limits
            if i > 1 and THREAD_STAGGER_DELAY > 0:
                time.sleep(THREAD_STAGGER_DELAY)
            
            future = executor.submit(
                research_pipeline,
                question,
                master_folder,
                i,
                len(questions)
            )
            futures[future] = (i, question)
        
        # Collect results as they complete
        for future in as_completed(futures):
            i, question = futures[future]
            try:
                success, research_response, citations = future.result()
                all_question_results.append((success, research_response, citations))
                
                if success:
                    successful_questions += 1
                    
            except Exception as e:
                safe_print(f"{Colors.RED}Error processing question {i}: {str(e)}{Colors.RESET}")
                all_question_results.append((False, None, []))
    
    # Extract and deduplicate citations from all questions
    safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== EXTRACTING CITATIONS FROM QUESTIONS ========{Colors.RESET}")
    citation_map, unique_citation_count = extract_and_deduplicate_citations(all_question_results)
    
    # Process citations if there are any
    if citation_map:
        # Prioritize citations based on reference count
        prioritized_citation_map, skipped_count = prioritize_citations(citation_map, args.max_citations)
        
        if skipped_count > 0:
            safe_print(f"{Colors.YELLOW}Skipping {skipped_count} less referenced citations to stay within limit of {args.max_citations}{Colors.RESET}")
        
        # Process each unique citation
        safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== PROCESSING CITATIONS ========{Colors.RESET}")
        citation_results = process_citations(prioritized_citation_map, master_folder, max_workers, THREAD_STAGGER_DELAY)
        
        # Create indexes
        master_index_path = create_master_index(master_folder, questions, all_question_results)
        citation_index_path = create_citation_index(master_folder, citation_map, citation_results, skipped_count)
        
        # Consolidate summaries
        safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== CONSOLIDATING SUMMARIES ========{Colors.RESET}")
        consolidate_summary_files(master_folder, "executive_summary", "consolidated_executive_summaries.md", "Consolidated Executive Summaries")
        consolidate_summary_files(master_folder, "research_summary", "consolidated_research_summaries.md", "Consolidated Research Summaries")
        
        # Move master index and citation index to summaries folder
        move_file(master_index_path, os.path.join(master_folder, "summaries"))
        move_file(citation_index_path, os.path.join(master_folder, "summaries"))
    else:
        safe_print(f"{Colors.YELLOW}No citations found. Skipping citation processing phase.{Colors.RESET}")
        # Create the master index even if there are no citations
        master_index_path = create_master_index(master_folder, questions, all_question_results)
        
        # Consolidate summary files and move master index
        safe_print(f"\n{Colors.BOLD}{Colors.CYAN}======== CONSOLIDATING SUMMARIES ========{Colors.RESET}")
        consolidate_summary_files(master_folder, "executive_summary", "consolidated_executive_summaries.md", "Consolidated Executive Summaries")
        consolidate_summary_files(master_folder, "research_summary", "consolidated_research_summaries.md", "Consolidated Research Summaries")
        move_file(master_index_path, os.path.join(master_folder, "summaries"))
    
    # Process files with OpenAI if enabled
    if ENABLE_OPENAI_INTEGRATION:
        project_data = process_files_with_openai(master_folder, project_data)
    
    # Update project status to completed
    project_data["status"] = "completed"
    update_project_in_tracking(project_id, {"status": "completed"})
    
    # Output summary
    safe_print(f"\n{Colors.BOLD}{Colors.GREEN}Research complete at {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    safe_print(f"{Colors.CYAN}Summary:{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Questions: {successful_questions}/{len(questions)} successfully processed{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Citations: Found {unique_citation_count} unique citations{Colors.RESET}")
    if citation_map:
        if skipped_count > 0:
            safe_print(f"{Colors.CYAN}- Citation Processing: {len(citation_results)}/{len(prioritized_citation_map)} prioritized citations processed, {skipped_count} less relevant citations skipped{Colors.RESET}")
        else:
            safe_print(f"{Colors.CYAN}- Citation Processing: {len(citation_results)}/{len(prioritized_citation_map)} citations processed{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Consolidated Files: Executive summaries, research summaries{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Output directory: {master_folder}{Colors.RESET}")
    safe_print(f"{Colors.CYAN}- Summaries directory: {os.path.join(master_folder, 'summaries')}{Colors.RESET}")
    
    # Add OpenAI info to the summary if it was processed
    if project_data.get("openai_integration"):
        vs_info = project_data["openai_integration"].get("vector_store", {})
        file_ids = project_data["openai_integration"].get("file_ids", {})
        
        total_files = (1 if file_ids.get("readme") else 0) + len(file_ids.get("markdown_files", [])) + len(file_ids.get("summary_files", []))
        
        safe_print(f"{Colors.CYAN}- OpenAI Integration: {total_files} files uploaded{Colors.RESET}")
        safe_print(f"{Colors.CYAN}- Vector Store: {vs_info.get('name')} (ID: {vs_info.get('id')}){Colors.RESET}")
    
    return project_data

if __name__ == "__main__":
    main() 