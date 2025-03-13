# Research Assistant Streamlit App

A web-based interface for interacting with research projects and initiating new research using the Research Orchestrator.

## Features

This app provides three main functionalities:

1. **Chat with Research Projects**: Interact with existing research using OpenAI's vector search capabilities
2. **Start New Research**: Configure and launch new research projects 
3. **Preview Research Questions**: Generate sample research questions without starting a full project

## Setup

### Prerequisites

- Python 3.8+
- Streamlit (`pip install streamlit`)
- OpenAI Python SDK (`pip install openai`)
- Python-dotenv (`pip install python-dotenv`)
- Access to the parent directory with `research_orchestrator.py`

### Environment Variables

Create a `.env` file in the parent directory with:

```bash
# OpenAI API configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_CHAT_MODEL=gpt-4o-mini
MAX_SEARCH_RESULTS=5

# Research project configuration
RESEARCH_PROJECTS_FILE=research_projects.json

# Perplexity API (for new research)
PERPLEXITY_API_KEY=your_perplexity_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

## Running the App

From the project root directory:

```bash
cd streamlit_app
streamlit run app.py
```

## Tab 1: Chat with Projects

This tab allows you to interact with existing research projects that have been uploaded to OpenAI vector stores.

### Features:

- Project selection dropdown with all available projects
- Chat interface with message history
- Response generation using OpenAI's vector search
- Citation display with source information
- Ability to start new chats or switch projects

### How It Works:

1. Select a research project from the dropdown
2. Click "Start Chat" to begin a conversation
3. Enter your questions about the research topic
4. View AI responses with relevant citations
5. Click "New Chat / Switch Project" to reset or change projects

## Tab 2: Start New Research

This tab provides a form-based interface to configure and initiate new research projects.

### Features:

- Input fields for research topic and professional perspective
- Sliders for question depth, worker threads, and citation limits
- Toggle for OpenAI integration
- Real-time progress display during research execution

### How It Works:

1. Enter a research topic and configure parameters
2. Click "Start Research" to begin the process
3. View real-time progress as the research executes
4. After completion, the project will be available in the Chat tab

## Tab 3: Preview Questions

This tab allows you to generate sample research questions without starting a full research project.

### Features:

- Input fields for topic and professional perspective
- Slider for number of questions
- Preview of generated research questions

### How It Works:

1. Enter a topic and perspective
2. Select the number of questions to generate
3. Click "Generate Preview" to see sample questions
4. Review questions before starting a full research project

## Troubleshooting

### Common Issues:

1. **"Could not import from research_orchestrator.py" warning**:
   - Ensure the parent directory contains `research_orchestrator.py`
   - Check Python path configuration

2. **No research projects available**:
   - Verify that `research_projects.json` exists and is properly formatted
   - Check that at least one project has completed OpenAI integration

3. **Chat not working**:
   - Confirm OpenAI API key is correctly set
   - Check vector store ID in the project data
   - Look for error messages in the chat interface

4. **Research initiation fails**:
   - Check that all required API keys are correctly set
   - Verify that `research_orchestrator.py` is accessible
   - Look for error messages in the output area

## Recent Updates

### March 14, 2024:
- Fixed chat functionality with proper message display
- Improved session state management for better conversation persistence
- Enhanced error handling for OpenAI responses
- Added "New Chat / Switch Project" button for better navigation
- Updated from deprecated `st.experimental_rerun()` to `st.rerun()`
- Improved markdown rendering of chat messages 