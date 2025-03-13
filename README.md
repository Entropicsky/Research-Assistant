# Research Assistant

A comprehensive research automation tool that generates deep research on topics using AI-powered search and analysis.

## Overview

This project consists of two main components:

1. **Research Orchestrator (`research_orchestrator.py`)**: A powerful command-line tool that:
   - Generates research questions from a given topic
   - Processes questions through the Perplexity API
   - Extracts and deduplicates citations from responses
   - Intelligently scrapes and processes citation content
   - Creates organized research outputs
   - Integrates with OpenAI for semantic search capabilities

2. **Streamlit Research Assistant App (`streamlit_app/app.py`)**: A web-based interface that:
   - Allows chatting with existing research projects using OpenAI
   - Provides a form-based interface to initiate new research
   - Offers preview functionality for research questions

> **Note**: The Streamlit app is currently the recommended way to interact with research projects. There is an experimental Next.js chatbot in the `research_chatbot` folder, but it is not fully supported at this time.

## Installation

### Requirements

- Python 3.8+
- Required Python packages:
  ```
  pip install streamlit openai python-dotenv reportlab requests firecrawl
  ```

### Environment Setup

Create a `.env` file in the project root with the following variables:

```
# API Keys
PERPLEXITY_API_KEY=your_perplexity_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
OPENAI_API_KEY=your_openai_api_key

# Model Configuration
PERPLEXITY_RESEARCH_MODEL=sonar-deep-research
PERPLEXITY_CLEANUP_MODEL=sonar-pro
OPENAI_CHAT_MODEL=gpt-4o-mini

# Rate Limiting Configuration
API_MAX_RETRIES=3
API_INITIAL_RETRY_DELAY=5.0
API_MAX_RETRY_DELAY=60.0
RATE_LIMIT_QUESTIONS_PER_WORKER=7
THREAD_STAGGER_DELAY=5.0

# Citation Configuration
MAX_CITATIONS=50
CITATION_TIMEOUT=300

# Search Configuration
MAX_SEARCH_RESULTS=5

# File Paths
RESEARCH_PROJECTS_FILE=research_projects.json
```

## Research Orchestrator Command-Line Reference

The `research_orchestrator.py` script can be run in multiple modes with various command-line arguments.

### Basic Usage

```bash
# Interactive mode (follow the prompts)
python research_orchestrator.py

# Topic mode (generate questions automatically)
python research_orchestrator.py --topic "Your Research Topic" --perspective "Researcher" --depth 5

# Direct questions mode
python research_orchestrator.py --questions "Question 1" "Question 2" "Question 3"

# Questions from file (one per line)
python research_orchestrator.py --questions questions.txt
```

### Command-Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--topic` | `-t` | Research topic to generate questions about | None |
| `--perspective` | `-p` | Professional perspective for research | "Researcher" |
| `--depth` | `-d` | Number of research questions to generate | 5 |
| `--questions` | `-q` | Directly specify questions or provide a file with questions | None |
| `--output-dir` | `-o` | Custom output directory | Based on topic name |
| `--max-workers` | `-w` | Maximum number of worker threads | Auto-calculated |
| `--max-citations` | `-c` | Maximum number of citations to process | 50 |
| `--stagger-delay` | `-s` | Delay between starting worker threads (seconds) | 5.0 |
| `--limit` | `-l` | Limit processing to N questions (for testing) | Process all |
| `--openai-integration` | None | Enable or disable OpenAI integration | "enable" |
| `--skip-openai-upload` | None | Skip uploading to OpenAI | False |

### Example Commands

```bash
# Basic research with all defaults
python research_orchestrator.py --topic "Quantum Computing Applications"

# Research with custom perspective and depth
python research_orchestrator.py --topic "AI in Healthcare" --perspective "Hospital Administrator" --depth 10

# Research with custom output directory and worker limits
python research_orchestrator.py --topic "Climate Change Solutions" --output-dir ./climate_research --max-workers 4

# Process specific questions with citation limit
python research_orchestrator.py --questions "What is quantum computing?" "How are quantum computers built?" --max-citations 30

# Disable OpenAI integration
python research_orchestrator.py --topic "Renewable Energy" --openai-integration disable

# Advanced configuration
python research_orchestrator.py --topic "Space Exploration" --perspective "Astrophysicist" --depth 8 --max-workers 3 --stagger-delay 10 --max-citations 40
```

## Streamlit Research Assistant App

The Streamlit app provides a user-friendly interface to interact with research projects and initiate new research.

### Running the App

```bash
cd streamlit_app
streamlit run app.py
```

### Features

The app consists of three main tabs:

#### 1. Chat with Projects

- Select from available research projects with OpenAI integration
- Interactive chat interface using OpenAI's vector search capabilities
- View citations and sources for each response
- Start new chats or switch between projects

#### 2. Start New Research

- Form-based interface to configure research parameters:
  - Research Topic
  - Professional Perspective
  - Number of Questions
  - Maximum Worker Threads
  - Maximum Citations
  - OpenAI Integration toggle
- Real-time progress display during research execution

#### 3. Preview Questions

- Generate sample research questions without starting a full research project
- Configure topic, perspective, and number of questions
- View generated questions instantly

## Project Output Structure

For each research project, the following structure is created:

```
[Topic]_[timestamp]/
├── markdown/                 # Markdown versions of research outputs
├── response/                 # Raw API responses
├── reports/                  # PDF reports (if generated)
├── summaries/                # Consolidated summary files
├── README.md                 # Project overview
├── index.md                  # Master index with links to all outputs
├── citation_index.md         # Index of all citations
└── openai_upload_info.json   # OpenAI integration details
```

Research files follow these naming conventions:
- `Q01_research_response.json`: Raw API response for question 1
- `A01_research_summary.md`: Research summary for question 1
- `ES1_executive_summary.md`: Executive summary for question 1

## Recent Updates

### March 14, 2024 Updates:

1. **Streamlit App**:
   - Added web-based interface for research project interaction
   - Implemented chat functionality with OpenAI vector search
   - Added research initiation form interface
   - Added question preview functionality

2. **Research Orchestrator Enhancements**:
   - Enhanced context for research questions 
   - Improved file naming convention for executive summaries (ES prefix)
   - Fixed citation processing error handling
   - Added better URL validation

## Troubleshooting

### Common Issues:

1. **API Rate Limiting**: 
   - Adjust `RATE_LIMIT_QUESTIONS_PER_WORKER` and `THREAD_STAGGER_DELAY` in `.env`
   - Reduce `--max-workers` parameter

2. **Citation Processing Errors**:
   - Increase `CITATION_TIMEOUT` for slow websites
   - Use `--max-citations` to limit processing to most important sources

3. **OpenAI Integration Issues**:
   - Check `OPENAI_API_KEY` is set correctly
   - Use `--skip-openai-upload` to bypass OpenAI integration

### Streamlit App Issues:

1. **Missing Projects**:
   - Ensure `RESEARCH_PROJECTS_FILE` points to the correct file
   - Check that projects have completed OpenAI integration

2. **Chat Not Working**:
   - Verify `OPENAI_API_KEY` is set correctly
   - Check that vector store IDs exist in the project data

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.