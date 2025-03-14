#!/usr/bin/env python3
"""
Script to update all existing projects in research_projects.json to have the active field set to true.
"""

import json
import os
import time
import sys

# Path to the research projects file
RESEARCH_PROJECTS_FILE = "research_projects.json"

def load_project_tracking():
    """
    Load the project tracking data from JSON file.
    
    Returns:
        dict: The project tracking data
    """
    if os.path.exists(RESEARCH_PROJECTS_FILE):
        try:
            with open(RESEARCH_PROJECTS_FILE, "r") as f:
                data = json.load(f)
                return data
        except Exception as e:
            print(f"Warning: Could not load project tracking file: {str(e)}")
            return None
    else:
        print(f"Error: Project tracking file not found: {RESEARCH_PROJECTS_FILE}")
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
        # Create a backup of the original file
        backup_file = f"{RESEARCH_PROJECTS_FILE}.bak"
        if os.path.exists(RESEARCH_PROJECTS_FILE):
            with open(RESEARCH_PROJECTS_FILE, "r") as src:
                with open(backup_file, "w") as dst:
                    dst.write(src.read())
            print(f"Created backup at {backup_file}")
        
        # Save the updated data
        with open(RESEARCH_PROJECTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Warning: Could not save project tracking file: {str(e)}")
        return False

def update_active_status():
    """
    Update all projects to have the active field set to true.
    """
    # Load existing tracking data
    tracking_data = load_project_tracking()
    if not tracking_data:
        return False
    
    # Count projects before update
    total_projects = len(tracking_data.get("projects", []))
    projects_with_active = sum(1 for p in tracking_data.get("projects", []) if "active" in p)
    active_projects = sum(1 for p in tracking_data.get("projects", []) if p.get("active", False))
    
    print(f"Before update:")
    print(f"  Total projects: {total_projects}")
    print(f"  Projects with active field: {projects_with_active}")
    print(f"  Active projects: {active_projects}")
    
    # Update all projects to have active=True
    updated_count = 0
    for project in tracking_data.get("projects", []):
        if "active" not in project or not project["active"]:
            project["active"] = True
            updated_count += 1
    
    # Save the updated tracking data
    if updated_count > 0:
        success = save_project_tracking(tracking_data)
        if success:
            print(f"Successfully updated {updated_count} projects to have active=True")
        else:
            print(f"Failed to save updated tracking data")
            return False
    else:
        print("No projects needed updating")
    
    # Count projects after update
    projects_with_active = sum(1 for p in tracking_data.get("projects", []) if "active" in p)
    active_projects = sum(1 for p in tracking_data.get("projects", []) if p.get("active", False))
    
    print(f"After update:")
    print(f"  Total projects: {total_projects}")
    print(f"  Projects with active field: {projects_with_active}")
    print(f"  Active projects: {active_projects}")
    
    return True

if __name__ == "__main__":
    print(f"Updating active status for all projects in {RESEARCH_PROJECTS_FILE}")
    
    # Check if the user wants to proceed
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        proceed = True
    else:
        response = input("This will set all projects to active=True. Proceed? (y/n): ")
        proceed = response.lower() in ["y", "yes"]
    
    if proceed:
        success = update_active_status()
        if success:
            print("Update completed successfully")
        else:
            print("Update failed")
            sys.exit(1)
    else:
        print("Update cancelled") 