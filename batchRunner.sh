#!/bin/bash

# Validate input
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

input_dir="$1"
output_dir="output"
failure_count=0
max_failures=2

# Create output directory
mkdir -p "$output_dir"

# Find PDFs and CBZs up to 2 levels deep (case-insensitive)
while IFS= read -r file; do
    # Extract basename without extension
    filename=$(basename "$file")
    base_name="${filename%.*}"   # remove extension
    parent_name=$(basename "$(dirname "$file")")  # immediate parent folder
    target_dir="$output_dir/$parent_name"
    mkdir -p "$target_dir"
    output_file="$target_dir/$base_name.cbz"

    echo "Converting: $file → $output_file"

    # Run ereaderMangaOptimizer.py (same call for PDFs and CBZs)
        # Activate venv if present (do not fail the job if not)
    if [ -f ".venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        . .venv/bin/activate
    fi
    if python3 ereaderMangaOptimizer.py "$file" -o "$output_file"; then
        echo "✓ $parent_name/$base_name"
    else
        echo "✗ $parent_name/$base_name failed"
        ((failure_count++))

        if [ $failure_count -ge $max_failures ]; then
            echo "Stopping: $max_failures files failed."
            exit 1
        fi
    fi
done < <(find "$input_dir" -maxdepth 2 -type f \( -iname "*.pdf" -o -iname "*.cbz" \))

echo "Done. Failures: $failure_count"
