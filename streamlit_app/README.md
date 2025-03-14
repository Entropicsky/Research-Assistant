# Research Assistant Streamlit App

A web-based interface for interacting with research projects and initiating new research using the Research Orchestrator.

## Features

This app provides four main functionalities:

1. **Chat with Research Projects**: Interact with existing research using OpenAI's vector search capabilities
2. **Start New Research**: Configure and launch new research projects 
3. **Add Questions to Existing Project**: Expand existing research projects with new questions
4. **Preview Research Questions**: Generate sample research questions without starting a full project

## Setup

### Prerequisites

- Python 3.8+
- Required packages:
  ```bash
  pip install -r requirements.txt
  ```
  The requirements.txt file is in the root directory of the project.

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

## Tab 3: Add Questions to Existing Project

This tab allows you to add new questions to an existing research project.

### Features:

- Project selection that defaults to the currently selected project in the Chat tab
- Display of current project information including existing questions
- Text area for entering new questions (one per line)
- Configuration options for worker threads, citations, and OpenAI integration
- Real-time progress display during processing

### How It Works:

1. Select an existing project (defaults to the one selected in Chat tab)
2. Review the current project information
3. Enter new questions, one per line
4. Configure processing parameters
5. Click "Add Questions" to begin the process
6. View real-time progress as the questions are processed
7. After completion, the updated project will be available in the Chat tab

## Tab 4: Preview Questions

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

## Recent Improvements (March 2024)

1. **Project Synchronization**:
   - The "Add Questions to Existing Project" tab now defaults to the project selected in the "Chat with Projects" tab
   - This creates a more seamless workflow when expanding research projects

2. **User Interface Enhancements**:
   - Fixed text visibility issues throughout the application
   - Ensured proper text color contrast in all components
   - Improved the styling of citations and web citations

3. **Chat Experience**:
   - Improved message display and formatting
   - Enhanced citation and source information display
   - Better error handling and feedback

4. **OpenAI Integration Optimization**:
   - The backend now only uploads new files when adding questions to projects
   - This reduces API usage and speeds up the process
   - Fixed bug where project metadata was being lost during updates

## Troubleshooting

### Common Issues:

1. **Missing Projects**:
   - Ensure `RESEARCH_PROJECTS_FILE` points to the correct file
   - Check that projects have completed OpenAI integration
   - Toggle "Show Inactive Projects" if projects are not appearing

2. **Chat Not Working**:
   - Verify `OPENAI_API_KEY` is set correctly
   - Check that vector store IDs exist in the project data
   - Ensure the selected model is available in your OpenAI account

3. **Text Visibility Issues**:
   - If text in chat inputs or other fields is not visible, check your browser's color scheme
   - The app has been updated to ensure text is visible in both light and dark modes

4. **Project Selection Errors**:
   - If selecting a project fails, try toggling the "Show Inactive Projects" option
   - Check the project's status in the `research_projects.json` file

5. **Real-time Progress Issues**:
   - If progress is not updating, check your browser's JavaScript settings
   - Try running the app in a different browser if issues persist 