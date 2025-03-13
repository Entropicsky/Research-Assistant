#!/bin/bash
# Setup script for filesearchtest

# Create the filesearchtest directory
mkdir -p filesearchtest

# Find the most recent research output directory
LATEST_DIR=$(ls -td research_output/*/ 2>/dev/null | head -n 1)

if [ -z "$LATEST_DIR" ]; then
    echo "No research output directories found. Please run research_orchestrator.py first."
    exit 1
fi

echo "Found latest research output directory: $LATEST_DIR"

# Check if the summaries folder exists
SUMMARIES_DIR="${LATEST_DIR}summaries"
if [ ! -d "$SUMMARIES_DIR" ]; then
    echo "Summaries directory not found in latest research output. Using markdown directory instead."
    SUMMARIES_DIR="${LATEST_DIR}markdown"
fi

# Count markdown files in the directory
MD_COUNT=$(ls "$SUMMARIES_DIR"/*.md 2>/dev/null | wc -l)

if [ "$MD_COUNT" -eq 0 ]; then
    echo "No markdown files found in $SUMMARIES_DIR"
    exit 1
fi

echo "Found $MD_COUNT markdown files in $SUMMARIES_DIR"

# Copy consolidated markdown files to filesearchtest directory
echo "Copying files to filesearchtest directory..."

# First try to copy consolidated files
CONSOLIDATED_COUNT=0
for file in "$SUMMARIES_DIR"/consolidated_*.md; do
    if [ -f "$file" ]; then
        cp "$file" filesearchtest/
        echo "Copied $(basename "$file")"
        CONSOLIDATED_COUNT=$((CONSOLIDATED_COUNT + 1))
    fi
done

# If no consolidated files found, copy some individual files (limit to 5)
if [ "$CONSOLIDATED_COUNT" -eq 0 ]; then
    echo "No consolidated files found. Copying individual files..."
    
    # Get a list of markdown files, excluding index files
    files=$(ls "$SUMMARIES_DIR"/*.md | grep -v "index.md" | head -n 5)
    
    for file in $files; do
        cp "$file" filesearchtest/
        echo "Copied $(basename "$file")"
    done
fi

# Also copy the master index if it exists
if [ -f "$SUMMARIES_DIR/master_index.md" ]; then
    cp "$SUMMARIES_DIR/master_index.md" filesearchtest/
    echo "Copied master_index.md"
fi

# List the files in the filesearchtest directory
echo ""
echo "Files ready for testing:"
ls -l filesearchtest/

echo ""
echo "Setup complete! You can now run:"
echo "python filesearchtest.py"
echo ""
echo "Make sure your OPENAI_API_KEY is set in the .env file." 