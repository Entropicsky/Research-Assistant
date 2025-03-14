# Implementation Plan for Command-Line Enhancements

## Overview
This document outlines the implementation plan for adding new command-line features to the `research_orchestrator.py` script. These features will enhance the script's functionality by allowing users to work with existing projects and add new questions to them.

## 1. New Functions to Implement

### 1.1 Project Retrieval
```python
def get_project_by_id(project_id):
    """
    Retrieve a project from the tracking file by its ID.
    
    Args:
        project_id (str): The ID of the project to retrieve
    
    Returns:
        dict: The project data or None if not found
    """
    # Implementation details
```

### 1.2 Question Addition
```python
def add_questions_to_project(project_data, questions, args):
    """
    Add new questions to an existing project.
    
    Args:
        project_data (dict): The existing project data
        questions (list): List of new questions to add
        args: Command-line arguments
    
    Returns:
        dict: Updated project data
    """
    # Implementation details
```

### 1.3 Project Folder Retrieval
```python
def get_project_folder(project_data):
    """
    Get the folder path for an existing project.
    
    Args:
        project_data (dict): The project data
    
    Returns:
        str: The project folder path or None if not found
    """
    # Implementation details
```

## 2. Command-Line Argument Updates

### 2.1 New Arguments
```python
# Add to argparse setup
parser.add_argument("--existing-project", help="ID of an existing project to process with OpenAI integration")
parser.add_argument("--add-questions", action="store_true", help="Add questions to an existing project (requires --existing-project)")
```

### 2.2 Interactive Mode Updates
- Add initial prompt for "Create New Project" or "Add to Existing Project"
- If "Add to Existing Project" is selected:
  - Display list of existing projects
  - Prompt for project selection
  - Prompt for questions file location
  - Load questions from file
  - Call `add_questions_to_project`

## 3. Main Function Updates

### 3.1 Existing Project Processing
```python
# Add to main function
if args.existing_project:
    project_data = get_project_by_id(args.existing_project)
    if not project_data:
        safe_print(f"{Colors.RED}Project with ID {args.existing_project} not found. Exiting.{Colors.RESET}")
        return None
        
    if args.add_questions:
        # Handle adding questions to existing project
        pass
    else:
        # Process existing project with OpenAI integration
        master_folder = get_project_folder(project_data)
        if not master_folder:
            safe_print(f"{Colors.RED}Project folder not found for project {args.existing_project}. Exiting.{Colors.RESET}")
            return None
            
        project_data = process_files_with_openai(master_folder, project_data)
        return project_data
```

### 3.2 Adding Questions to Existing Project
```python
# Add to main function, inside the args.existing_project block
if args.add_questions:
    if not args.questions:
        safe_print(f"{Colors.RED}No questions provided. Use --questions option to specify questions or a file containing questions. Exiting.{Colors.RESET}")
        return None
        
    # Load questions (reuse existing code for loading questions from args.questions)
    # ...
    
    # Add questions to existing project
    project_data = add_questions_to_project(project_data, questions, args)
    return project_data
```

## 4. Testing Plan

### 4.1 Test Cases
1. Test retrieving a project by ID
   - Valid project ID
   - Invalid project ID
   - Malformed project ID

2. Test processing existing project with OpenAI integration
   - Project with valid folder
   - Project with missing folder
   - Project already processed with OpenAI

3. Test adding questions to existing project
   - Add questions from command line
   - Add questions from file
   - Add questions to project with existing questions
   - Add questions to project without existing questions

4. Test interactive mode
   - Create new project flow
   - Add to existing project flow
   - Error handling for invalid inputs

### 4.2 Integration Testing
- Verify compatibility with Streamlit website
- Verify all existing command-line options still work
- Verify error handling is comprehensive

## 5. Documentation Updates

### 5.1 README Updates
- Add section on working with existing projects
- Add examples for each new command-line option
- Update usage examples

### 5.2 Help Text Updates
- Update argparse help text for new options
- Add detailed descriptions for new functionality

## 6. Implementation Order
1. Implement `get_project_by_id` function
2. Implement `get_project_folder` function
3. Update command-line arguments
4. Implement existing project processing
5. Implement `add_questions_to_project` function
6. Update interactive mode
7. Add comprehensive error handling
8. Update documentation
9. Test all functionality

## 7. Potential Challenges and Solutions

### 7.1 Project Folder Structure
**Challenge**: Ensuring the project folder structure is maintained when adding new questions.
**Solution**: Carefully analyze the existing folder structure and ensure new questions follow the same pattern.

### 7.2 OpenAI Integration
**Challenge**: Handling OpenAI integration for projects that already have partial integration.
**Solution**: Check the current integration status and only perform necessary steps.

### 7.3 Streamlit Compatibility
**Challenge**: Ensuring changes don't break the Streamlit interface.
**Solution**: Test all changes with the Streamlit app to verify compatibility. 