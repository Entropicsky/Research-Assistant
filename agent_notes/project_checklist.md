# Perplexity Research Project Checklist

## Initial Assessment
- [x] Review perplexityresearch.py script
- [x] Understand all main components and workflows
- [x] Check environment configuration (.env file)
- [x] Review README for additional context
- [x] Identify any potential issues or areas for improvement

## Main Components
- [x] Environment Configuration
  - [x] Confirm required environment variables: PERPLEXITY_API_KEY, FIRECRAWL_API_KEY
  - [x] Identify model configuration: PERPLEXITY_RESEARCH_MODEL, PERPLEXITY_CLEANUP_MODEL
  - [x] Evaluate need for additional environment variables

- [x] Perplexity API Integration
  - [x] Review query_perplexity function
  - [x] Note non-streaming API implementation
  - [x] Observe different timeouts for research vs. cleanup calls
  - [x] Understand executive summary generation process

- [x] Firecrawl Integration
  - [x] Review intelligent_scrape function
  - [x] Understand site mapping for complex websites
  - [x] Observe special handling for social media sites
  - [x] Note the fallback mechanisms for failed scrapes

- [x] PDF Report Generation
  - [x] Review PDFReport class structure
  - [x] Understand how it processes markdown into PDF elements
  - [x] Review styling and formatting options
  - [x] Note HTML fallback when PDF generation fails

- [x] File and Directory Management
  - [x] Review folder structure: response/, markdown/, reports/
  - [x] Understand timestamped subfolder convention
  - [x] Note the README creation in each run

## New Research Orchestrator
- [x] Create new script for high-level research orchestration
  - [x] Design function to collect input parameters (Topic, Perspective, Depth)
  - [x] Implement question generation via Perplexity
  - [x] Create parsing logic for extracting questions from response
  - [x] Develop loop for processing each question through research pipeline
  - [x] Implement new folder structure (Topic-based master folder)

- [x] Design Enhancements
  - [x] Implement progress tracking across multiple questions
  - [x] Create master summary/index for all research questions
  - [x] Ensure proper error handling for question generation stage
  - [x] Add logging for the multi-question process

- [x] Integration
  - [x] Ensure proper reuse of existing functions from perplexityresearch.py
  - [x] Modify folder creation logic to support new structure
  - [x] Create consolidated final report with all question results

## Performance Optimization
- [x] Implement parallel processing
  - [x] Add ThreadPoolExecutor for concurrent question processing
  - [x] Implement thread-safe printing
  - [x] Add configurable maximum worker threads
  - [x] Ensure proper error handling in worker threads
  - [x] Track individual thread progress with thread-specific prefixes

## API Rate Limiting and Error Handling
- [x] Implement API rate limiting detection and retry logic
  - [x] Create a utility function with exponential backoff for API calls
  - [x] Add detection for common rate limiting error messages
  - [x] Add configurable retry parameters in .env file
  - [x] Modify worker allocation based on rate limits
  - [x] Apply retry logic to all API calls (Perplexity and Firecrawl)
  - [x] Add clear logging for retry attempts

- [x] Configure rate limit parameters
  - [x] Add API_MAX_RETRIES to control maximum retry attempts
  - [x] Add API_INITIAL_RETRY_DELAY for initial backoff period
  - [x] Add API_MAX_RETRY_DELAY to cap maximum delay between retries
  - [x] Add RATE_LIMIT_QUESTIONS_PER_WORKER to control worker allocation

- [x] Implement staggered thread starts to prevent API hammering
  - [x] Add THREAD_STAGGER_DELAY parameter to control time between thread starts
  - [x] Modify ThreadPoolExecutor implementation for staggered launches
  - [x] Add command-line argument for custom stagger delay
  - [x] Add visual feedback for thread start staggering

## Testing
- [ ] Verify dependencies are installed
  - [ ] reportlab
  - [ ] requests
  - [ ] python-dotenv
  - [ ] firecrawl
- [ ] Test question generation functionality
- [ ] Test parallel processing with different numbers of workers
- [ ] Test rate limiting and retry logic
- [ ] Run the orchestrator with a simple topic
- [ ] Verify correct folder structure creation
- [ ] Check PDF report generation for each question
- [ ] Test error handling for various failure scenarios

## Potential Improvements
- [x] Add progress indicators (colored terminal output)
- [x] Implement command-line argument parsing with argparse
- [x] Consider parallelizing citation processing
- [x] Add rate limiting detection and retry logic
- [ ] Add logging instead of print statements
- [ ] Add option to skip already processed citations on re-runs
- [x] Implement better error reporting and recovery
- [ ] Add unit tests for key functions

## Citation Deduplication and Optimization (March 14, 2024)

- [x] Analyze current research pipeline to identify inefficiencies in citation processing
- [x] Design a three-phase approach for optimizing citation processing
  - [x] Phase 1: Process all questions to get responses
  - [x] Phase 2: Extract and deduplicate citations from all responses
  - [x] Phase 3: Process each unique citation once
- [x] Modify `research_pipeline` function to stop after getting the research response
- [x] Create new citation management functions
  - [x] `process_citation` for processing individual citations
  - [x] `extract_and_deduplicate_citations` for gathering unique citations across questions
  - [x] `create_citation_index` for generating an index of all citations
- [x] Update `main` function to implement the new three-phase workflow
- [x] Update `create_master_index` to work with the new data structures
- [x] Remove unused functions and code
  - [x] PDF generation code
  - [x] `create_master_folder`, `update_master_readme`, `generate_research_questions` functions
  - [x] `create_consolidated_report` function
- [x] Update imports and fix any dependencies
- [ ] Test the new workflow with a small set of questions
- [ ] Document the changes and enhancements

## Enhancement Requests

- [x] Add citation prioritization to reduce API costs and focus on most important sources
- [x] Add MAX_CITATIONS parameter to .env file and expose via command line
- [x] Timeout handling for citation processing to prevent script hanging
- [x] Add CITATION_TIMEOUT parameter to .env file 
- [x] Implement OpenAI File Search functionality
- [x] Integrate OpenAI File Search into research_orchestrator.py
- [x] Create tracking system for research projects
- [ ] Add error handling for invalid research questions
- [ ] Add support for image generation from research summaries
- [x] Restore topic-based question generation functionality
- [x] Add interactive mode when no parameters are provided
- [x] Create consolidated output files with all summaries
- [x] Create "summaries" subfolder for consolidated outputs
- [x] Change naming convention from Q-prefix to A-prefix for better sorting
- [x] Limit number of citations processed to 50 (prioritizing by frequency)
- [x] Add timeout protection for citation processing to prevent hanging
- [x] Update README.md with all recent changes
- [x] Create run_examples.sh with usage examples

## OpenAI File and Vector Store Integration

- [x] Create project tracking JSON file
  - [x] Define JSON schema for project tracking
  - [x] Implement functions to read/write the tracking file
  - [x] Add logic to update tracking when new projects are created

- [x] Implement OpenAI file upload functionality
  - [x] Add OpenAI API integration
  - [x] Create function to upload README.md
  - [x] Create function to upload markdown and summary files
  - [x] Add retry logic for failed uploads
  - [x] Track uploaded file IDs

- [x] Implement vector store creation
  - [x] Create function to create a new vector store
  - [x] Implement file addition to vector store
  - [x] Add wait logic for file processing
  - [x] Add status checking and verification
  - [x] Store vector store ID in tracking file

- [x] Update main workflow
  - [x] Modify main() to include file upload and vector store steps
  - [x] Update environment variable handling for OpenAI API key
  - [x] Add proper error handling for OpenAI operations
  - [x] Make OpenAI integration optional via --openai-integration flag

- [x] Testing and validation
  - [x] Test setup for file upload functionality
  - [x] Test setup for vector store creation
  - [x] Test project tracking updates
  - [x] Ensure all components work together
  - [x] Ensure good error handling for all edge cases 

# Research Orchestrator Project Checklist

## Enhancements Implemented

- [x] Add context to the research prompt
  - [x] Modified research_pipeline to accept topic and perspective parameters
  - [x] Updated main function to pass topic and perspective to research_pipeline
  - [x] Enhanced the prompt with context about overall research topic and perspective
  - [x] Updated system prompt to guide the model better with context
  
- [x] Fix file naming convention for executive summaries
  - [x] Changed executive summary prefix from "A01_" to "ES1_" 
  - [x] Updated consolidate_summary_files to handle both naming conventions
  - [x] Ensured sorting works correctly with new naming pattern
  
- [x] Fix citation processing errors
  - [x] Updated with_timeout function to validate citation URL before processing
  - [x] Added proper error handling for non-string citation URLs
  - [x] Added basic URL validation for citation URLs

## Pending Tasks

- [ ] Test the changes with a real research project
- [ ] Add additional error handling for edge cases
- [ ] Consider expanding context information in the research prompt (e.g., add more metadata)
- [ ] Consider further enhancements to the executive summary template
- [ ] Implement a more robust URL validation system for citations

## Future Ideas

- [ ] Create a simple configuration system for customizing file naming conventions
- [ ] Add a feature to specify custom naming patterns via command line arguments
- [ ] Implement a progress tracking dashboard for long-running projects
- [ ] Add an option to generate visual representations of research findings
- [ ] Consider ML-based citation ranking beyond simple reference counting 

# Streamlit Research Assistant Project Checklist

## Initial Planning
- [x] Review existing codebase (testchat.py and research_orchestrator.py)
- [x] Identify key functionalities to integrate 
- [x] Design Streamlit app structure
- [x] Plan UI and user experience

## Implementation
- [x] Create basic Streamlit app structure
- [x] Implement chat tab functionality
  - [x] Load projects from research_projects.json
  - [x] Filter projects with OpenAI integration
  - [x] Create project selection interface
  - [x] Implement chat interface with OpenAI API
  - [x] Display citations and sources
  - [x] Handle conversation history

- [x] Implement research initiation tab
  - [x] Create form for research parameters
  - [x] Implement subprocess to run research_orchestrator.py
  - [x] Display real-time output from subprocess
  - [x] Add success/error handling

- [x] Implement question preview tab
  - [x] Create interface for topic, perspective, and depth
  - [x] Integrate with generate_research_questions function
  - [x] Display generated questions

- [x] Add error handling and validation
  - [x] Check for missing API keys
  - [x] Handle missing research_projects.json
  - [x] Validate input parameters

## Testing
- [ ] Test chat functionality with existing projects
- [ ] Test research initiation with a sample topic
- [ ] Test question preview with various topics
- [ ] Test error handling with invalid inputs
- [ ] Check responsiveness and UI on different screen sizes

## Enhancements
- [ ] Add option to select OpenAI model
- [ ] Add styling and better UI
- [ ] Implement progress tracking for research projects
- [ ] Add visualization of research data
- [ ] Add ability to view existing research files
- [ ] Create a project management interface to delete/archive projects

## Documentation
- [x] Add docstrings to all functions
- [x] Create README.md for the Streamlit app
- [x] Update main README.md with comprehensive documentation
- [x] Document command-line switches for research_orchestrator.py
- [ ] Add usage examples and screenshots 

## Streamlit App Fixes (March 14, 2024)
- [x] Fixed chat functionality in Streamlit app (app.py)
- [x] Improved the message display using Streamlit's chat components
- [x] Enhanced session state management for better conversation persistence
- [x] Added better error handling for OpenAI responses
- [x] Implemented a better UI flow with "New Chat / Switch Project" button
- [x] Fixed the markdown rendering of chat messages
- [x] Updated deprecated `st.experimental_rerun()` to `st.rerun()` per Streamlit API changes 

## Citation Processing Enhancements (March 15, 2024)

- [x] Improve citation processing feedback and debugging
  - [x] Fix overlapping code in process_citation function
  - [x] Add real-time progress bar for citation processing
  - [x] Implement detailed counters for successful, failed, and timed-out citations
  - [x] Add percentage-based completion statistics

- [x] Enhance error handling and reporting
  - [x] Improve the with_timeout function with better error information
  - [x] Add preliminary URL testing with test_citation_url function
  - [x] Categorize errors into specific types (timeouts, HTTP errors, scraping errors)
  - [x] Implement detailed error reporting in the citation index

- [x] Improve citation index
  - [x] Add processing statistics with success/failure rates
  - [x] Categorize failures by type with percentage breakdowns
  - [x] Include troubleshooting suggestions based on error types
  - [x] Add links to raw and formatted content files

- [x] Add debugging improvements
  - [x] Implement step-by-step progress indicators for each citation
  - [x] Enhance logging with detailed error messages and status codes
  - [x] Improve validation for citation URLs before processing

## Future Enhancements

- [ ] Add option to retry failed citations
- [ ] Implement a citation health check before full processing
- [ ] Create a visual dashboard for citation processing status
- [ ] Add support for resuming interrupted citation processing
- [ ] Implement adaptive timeout based on citation complexity 

## Citation Processing Enhancements

- [x] Add real-time progress tracking for citation processing
- [x] Improve error handling and categorization for citation failures
- [x] Create a comprehensive citation index with detailed statistics
- [x] Add detailed logging for citation processing steps
- [x] Fix citation URL handling in the `with_timeout` function
- [x] Resolve Firecrawl library installation issue (cannot import FirecrawlClient)
- [ ] Add support for YouTube and other restricted sites (requires contacting Firecrawl support) 

# Research Assistant Project Checklist

## GitHub Setup
- [x] Create agent_notes directory
- [x] Create project_checklist.md
- [x] Create agentnotes.md
- [x] Initialize Git repository
- [x] Create .gitignore file
- [x] Make initial commit
- [x] Create requirements.txt file
- [x] Create GitHub repository
- [x] Connect local repository to GitHub
- [x] Push code to GitHub

## Completed Features
- [x] Basic Streamlit UI
- [x] OpenAI integration
- [x] Vector store search
- [x] Web search capabilities
- [x] Debug panel
- [x] Model selection
- [x] Project management (active/inactive)
- [x] Progress tracking for research

## Future Enhancements
- [ ] Improve error handling
- [ ] Add more comprehensive documentation
- [ ] Create test suite
- [ ] Performance optimizations 