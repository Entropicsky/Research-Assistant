"""
Research Assistant Streamlit App

This app allows you to:
1. Chat with your existing research projects (using OpenAI's API)
2. Initiate new research projects (using Perplexity's API)

Features:
- Modern chat interface with citation display
- Project selection with card view
- Model selection with multiple options
- Web search integration
- Debug panel for troubleshooting
"""

import os
import sys
import json
import time
import subprocess
from dotenv import load_dotenv
import streamlit as st

# Add parent directory to path so we can import from research_orchestrator.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities and components
from streamlit_app.utils import (
    init_session_state,
    create_openai_client,
    load_research_projects,
    filter_available_projects,
    set_selected_project,
    get_selected_project,
    logger,
    INFO,
    get_model,
    is_web_search_enabled,
    clear_conversation,
    should_show_inactive_projects,
    set_show_inactive_projects
)

from streamlit_app.components import (
    chat_interface,
    project_selector,
    compact_project_selector,
    model_settings_panel,
    debug_panel,
    toggle_debug_mode
)

# Try to import generate_research_questions from research_orchestrator.py
try:
    from research_orchestrator import generate_research_questions
    has_research_orchestrator = True
except ImportError:
    has_research_orchestrator = False
    st.warning("Could not import from research_orchestrator.py. Some features may be disabled.")

# Load environment variables
load_dotenv()

# Constants
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))

# Page configuration
def setup_page():
    """Set up the page configuration and apply custom CSS."""
    st.set_page_config(
        page_title="Research Assistant",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="auto"
    )
    
    # Load and apply custom CSS
    with open(os.path.join(os.path.dirname(__file__), "styles", "main.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def on_project_selected(project, index):
    """Callback for when a project is selected."""
    set_selected_project(project, index)
    logger.info(f"Selected project: {project.get('parameters', {}).get('topic', 'unknown')}")
    st.rerun()

def display_chat_tab():
    """Display the chat tab content with a more compact layout."""
    # Get OpenAI client
    client = create_openai_client()
    if not client:
        st.error("Failed to create OpenAI client. Please check your API key.")
        return
    
    # Load and filter projects - handle inactive projects
    all_projects = load_research_projects()
    show_inactive = should_show_inactive_projects()
    available_projects = filter_available_projects(
        all_projects, 
        include_inactive=show_inactive
    )
    
    if not available_projects:
        st.warning("No research projects with OpenAI integration available.")
        return
    
    # Display project selector if no project is selected
    selected_project = get_selected_project()
    
    # Create a more compact header with debug toggle
    st.header("Chat with Research Projects", help="Chat with your research documents using AI")
    
    # Create a row of toggles/controls
    col1, col2 = st.columns([1, 1])
    with col1:
        # Toggle for inactive projects
        if st.toggle("Show Inactive Projects", value=show_inactive, key="show_inactive_toggle"):
            if not show_inactive:
                set_show_inactive_projects(True)
                st.rerun()
        else:
            if show_inactive:
                set_show_inactive_projects(False)
                st.rerun()
    
    with col2:
        # Toggle for debug mode
        debug_enabled = toggle_debug_mode()
    
    # If no project is selected, show the project selector
    if not selected_project:
        project_selector(available_projects, on_project_selected)
        return
    
    # Show a compact project selector with the current selection
    currently_selected_index = st.session_state.last_selected_project_index
    compact_project_selector(available_projects, on_project_selected, currently_selected_index)
    
    # Display model settings panel without nested columns
    current_model, web_enabled = model_settings_panel()
    
    # Create a clear visual separation with a subtle divider
    st.markdown("<hr style='margin: 0.5rem 0; border: none; height: 1px; background-color: rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
    
    # Display the chat interface
    chat_interface(use_streaming=True)
    
    # Show debug panel if enabled
    if debug_enabled:
        with st.expander("Debug Information", expanded=False):
            debug_data = {
                "model": get_model(),
                "web_search_enabled": is_web_search_enabled(),
                "vector_store_id": get_selected_project().get("vector_store_id", "unknown") if get_selected_project() else None
            }
            debug_panel(debug_data)
            
def initiate_research_project():
    """Form for initiating a new research project."""
    st.header("Start a New Research Project")
    
    with st.form("research_form"):
        topic = st.text_input("Research Topic", 
                             help="Enter the main subject of your research (e.g., 'Kahua, the Construction Software Management Company')")
        
        perspective = st.text_input("Professional Perspective", 
                                   value="Researcher",
                                   help="Enter the professional perspective to research from (e.g., 'Chief Product Officer')")
        
        depth = st.slider("Number of Questions", 
                          min_value=1, 
                          max_value=20, 
                          value=5,
                          help="Select how many research questions to generate")
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_workers = st.slider("Maximum Worker Threads", 
                                   min_value=1, 
                                   max_value=10, 
                                   value=3,
                                   help="Select maximum number of parallel worker threads")
        
        with col2:
            max_citations = st.slider("Maximum Citations", 
                                     min_value=10, 
                                     max_value=100, 
                                     value=50,
                                     help="Select maximum number of citations to process")
        
        enable_openai = st.checkbox("Enable OpenAI Integration", 
                                   value=True,
                                   help="Upload research to OpenAI for vector search")
        
        submitted = st.form_submit_button("Start Research")
        
        if submitted:
            if not topic:
                st.error("Please enter a research topic.")
                return
            
            # Use python3 explicitly and detect which python command is available
            python_cmd = "python3"
            try:
                # Check if python3 is available, if not fall back to python
                import shutil
                if not shutil.which("python3"):
                    python_cmd = "python"
                    
                logger.info(f"Using Python command: {python_cmd}")
            except Exception as e:
                logger.warning(f"Error detecting Python command: {str(e)}. Falling back to python3")
            
            # Build command for subprocess
            cmd = [
                python_cmd, 
                "research_orchestrator.py",
                "--topic", topic,
                "--perspective", perspective,
                "--depth", str(depth),
                "--max-workers", str(max_workers),
                "--max-citations", str(max_citations),
                "--openai-integration", "enable" if enable_openai else "disable"
            ]
            
            # Execute research_orchestrator.py as a subprocess
            with st.spinner(f"Running research on topic: {topic}..."):
                try:
                    # Create a progress display container
                    progress_container = st.container()
                    with progress_container:
                        st.subheader("Research Progress")
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Add a copy button for the logs
                        copy_col1, copy_col2 = st.columns([3, 1])
                        with copy_col2:
                            st.markdown("""
                            <div id="copy-button-container" style="text-align: right;">
                                <button id="copy-logs-button" style="
                                    background-color: #f0f2f6; 
                                    border: 1px solid #ddd; 
                                    padding: 5px 10px; 
                                    border-radius: 4px;
                                    cursor: pointer;
                                    font-size: 0.8em;">
                                    📋 Copy Logs
                                </button>
                            </div>
                            
                            <script>
                                document.getElementById('copy-logs-button').addEventListener('click', function() {
                                    const preElement = document.querySelector('[data-testid="stText"] pre');
                                    if (preElement) {
                                        const text = preElement.textContent;
                                        navigator.clipboard.writeText(text).then(
                                            () => {
                                                const btn = document.getElementById('copy-logs-button');
                                                const originalText = btn.textContent;
                                                btn.textContent = "✅ Copied!";
                                                setTimeout(() => { btn.textContent = originalText; }, 2000);
                                            },
                                            () => {
                                                const btn = document.getElementById('copy-logs-button');
                                                btn.textContent = "❌ Failed to copy";
                                                setTimeout(() => { btn.textContent = "📋 Copy Logs"; }, 2000);
                                            }
                                        );
                                    }
                                });
                            </script>
                            """, unsafe_allow_html=True)
                        
                        # Create a container for the log output with auto-scroll
                        log_container = st.container()
                        
                        # Add custom JavaScript to auto-scroll to bottom
                        st.markdown("""
                        <script>
                            // Function to scroll log to bottom
                            function scrollLogToBottom() {
                                const logElement = document.querySelector('[data-testid="stText"] pre');
                                if (logElement) {
                                    logElement.style.maxHeight = "400px";
                                    logElement.style.overflow = "auto";
                                    logElement.scrollTop = logElement.scrollHeight;
                                }
                            }
                            
                            // Set initial scroll and add observer to handle updates
                            scrollLogToBottom();
                            const observer = new MutationObserver(scrollLogToBottom);
                            const targetNode = document.querySelector('[data-testid="stText"]');
                            if (targetNode) {
                                observer.observe(targetNode, { childList: true, subtree: true });
                            }
                        </script>
                        """, unsafe_allow_html=True)
                    
                    # Run the process and capture output in real-time
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                    
                    # Import datetime for timestamps
                    from datetime import datetime
                    
                    # Show output in real-time with auto-scrolling and timestamps
                    full_output = ""
                    log_display = log_container.empty()
                    
                    # Track if we need to parse log sections
                    need_to_parse_sections = True
                    current_output = []
                    
                    for line in iter(process.stdout.readline, ''):
                        if not line:
                            break
                            
                        # Check if this looks like a log section start
                        if '[' in line and ']' in line and any(x in line for x in ['m[', 'Generating', 'Processing', 'Searching', 'Calling']):
                            # If we detect a timestamp pattern like [HH:MM:SS], treat as a new log entry
                            need_to_parse_sections = True
                        
                        # Add timestamp to the line
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Strip only trailing/leading whitespace but preserve internal spacing
                        styled_line = line.rstrip().lstrip()
                        
                        # Parse long lines into smaller chunks if needed
                        if need_to_parse_sections and len(styled_line) > 80 and ('[' in styled_line and ']' in styled_line):
                            # Try to break apart sections that look like separate log entries but got combined
                            sections = []
                            # Split on timestamp-like patterns but keep the delimiter
                            import re
                            parts = re.split(r'(\[\d{2}:\d{2}:\d{2}\])', styled_line)
                            
                            # Reconstruct with line breaks
                            current_section = ""
                            for i, part in enumerate(parts):
                                if i > 0 and re.match(r'\[\d{2}:\d{2}:\d{2}\]', part):
                                    # This is a timestamp, start a new section
                                    if current_section:
                                        sections.append(current_section)
                                    current_section = part
                                else:
                                    current_section += part
                            
                            if current_section:
                                sections.append(current_section)
                                
                            # Process each section with colors
                            for section in sections:
                                # Color the section based on content
                                if "ERROR" in section or "Error" in section or "Failed" in section:
                                    current_output.append(f"<span style='color: #ff4b4b;'>[{timestamp}] {section}</span>")
                                elif "WARNING" in section or "Warning" in section:
                                    current_output.append(f"<span style='color: #ffa500;'>[{timestamp}] {section}</span>")
                                elif "Searching for:" in section:
                                    current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {section}</span>")
                                elif "Processing results" in section:
                                    current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {section}</span>")
                                elif "Generating" in section:
                                    current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {section}</span>")
                                elif "Uploading to OpenAI" in section:
                                    current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {section}</span>")
                                elif "Research completed" in section or "success" in section.lower():
                                    current_output.append(f"<span style='color: #00cc66;'>[{timestamp}] {section}</span>")
                                elif "INFO" in section:
                                    current_output.append(f"<span style='color: #7f7f7f;'>[{timestamp}] {section}</span>")
                                else:
                                    current_output.append(f"[{timestamp}] {section}")
                        else:
                            # Process normally
                            if "ERROR" in styled_line or "Error" in styled_line or "Failed" in styled_line:
                                current_output.append(f"<span style='color: #ff4b4b;'>[{timestamp}] {styled_line}</span>")
                            elif "WARNING" in styled_line or "Warning" in styled_line:
                                current_output.append(f"<span style='color: #ffa500;'>[{timestamp}] {styled_line}</span>")
                            elif "Searching for:" in styled_line:
                                current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {styled_line}</span>")
                            elif "Processing results" in styled_line:
                                current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {styled_line}</span>")
                            elif "Generating" in styled_line:
                                current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {styled_line}</span>")
                            elif "Uploading to OpenAI" in styled_line:
                                current_output.append(f"<span style='color: #4b8eff;'>[{timestamp}] {styled_line}</span>")
                            elif "Research completed" in styled_line or "success" in styled_line.lower():
                                current_output.append(f"<span style='color: #00cc66;'>[{timestamp}] {styled_line}</span>")
                            elif "INFO" in styled_line:
                                current_output.append(f"<span style='color: #7f7f7f;'>[{timestamp}] {styled_line}</span>")
                            else:
                                current_output.append(f"[{timestamp}] {styled_line}")
                        
                        # Join output lines with explicit line breaks for HTML
                        full_output = "<br>".join(current_output)
                        
                        # Update status and progress estimate based on output parsing
                        if "Searching for:" in line:
                            status_text.text("Searching for information...")
                            progress_bar.progress(0.2)
                        elif "Processing results" in line:
                            status_text.text("Processing search results...")
                            progress_bar.progress(0.4)
                        elif "Generating research summaries" in line:
                            status_text.text("Generating research summaries...")
                            progress_bar.progress(0.6)
                        elif "Uploading to OpenAI" in line:
                            status_text.text("Uploading to OpenAI...")
                            progress_bar.progress(0.8)
                        elif "Research completed" in line:
                            status_text.text("Research completed!")
                            progress_bar.progress(1.0)
                        
                        # Display the log output with HTML formatting for proper line breaks
                        log_display.markdown(f"""
                        <div style='margin:0; padding:10px; background-color:#f5f5f5; max-height:400px; overflow:auto; white-space: pre-wrap; word-wrap: break-word;'>
                            {full_output}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Wait for process to complete
                    process.stdout.close()
                    return_code = process.wait()
                    
                    if return_code == 0:
                        status_text.text("Research completed successfully!")
                        progress_bar.progress(1.0)
                        st.success(f"Research on '{topic}' completed successfully!")
                        
                        # Refresh the project list
                        st.session_state.project_list_cache_time = 0
                    else:
                        status_text.text(f"Research failed with error code {return_code}")
                        st.error(f"Research process failed with return code {return_code}")
                    
                except Exception as e:
                    st.error(f"Error executing research: {str(e)}")
                    logger.error(f"Research execution error: {str(e)}", exc_info=True)

def preview_questions():
    """Generate and preview research questions without starting the full process."""
    st.header("Preview Research Questions")
    
    if not has_research_orchestrator:
        st.error("Research orchestrator module not available. Cannot preview questions.")
        return
    
    topic = st.text_input("Research Topic (for preview)", 
                         placeholder="Enter a topic to see sample questions")
    
    perspective = st.text_input("Professional Perspective (for preview)", 
                               value="Researcher")
    
    depth = st.slider("Number of Questions (for preview)", 
                      min_value=1, 
                      max_value=20, 
                      value=5)
    
    if st.button("Generate Preview") and topic:
        with st.spinner(f"Generating research questions for: {topic}..."):
            try:
                questions = generate_research_questions(topic, perspective, depth)
                if questions:
                    st.success(f"Generated {len(questions)} research questions")
                    for i, question in enumerate(questions, 1):
                        st.markdown(f"**Q{i}:** {question}")
                else:
                    st.error("Failed to generate questions. Please try again.")
            except Exception as e:
                st.error(f"Error generating questions: {str(e)}")

def main():
    """Main function to run the Streamlit app."""
    # Setup page configuration and CSS
    setup_page()
    
    # Initialize session state
    init_session_state()
    
    # Set up the title and description
    st.title("🔍 Research Assistant")
    st.markdown("""
    This tool helps you chat with your research projects and initiate new research.
    """)
    
    # Create tabs for different functionality
    tab1, tab2, tab3 = st.tabs(["Chat with Projects", "Start New Research", "Preview Questions"])
    
    with tab1:
        display_chat_tab()
    
    with tab2:
        initiate_research_project()
    
    with tab3:
        preview_questions()
    
    # Add a footer
    st.markdown("---")
    st.caption("Research Assistant App • Built with Streamlit and OpenAI")

if __name__ == "__main__":
    main() 