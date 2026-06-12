#!/bin/bash
set -euo pipefail

# Per-process virtual memory limit (KB). 3GB = 3*1024*1024
PER_PROCESS_VMEM_KB=${PER_PROCESS_VMEM_KB:-3145728}

# Apply ulimit (affects this shell and children)
ulimit -v "$PER_PROCESS_VMEM_KB" || {
    echo "Warning: could not set ulimit -v to $PER_PROCESS_VMEM_KB KB"
}

# Signal handling for graceful shutdown
cleanup() {
    pkill -P $$ 2>/dev/null || true
    exec 3>&- 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Validate input
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory> [concurrency]"
    exit 1
fi

input_dir="$1"
output_dir="output"
failed_log="$output_dir/failed.txt"

# Determine system cores
nprocs=$(nproc 2>/dev/null || echo 4)

# If user passed concurrency, use it; otherwise auto-calc from RAM and per-process vmem.
if [ "${2:-}" != "" ]; then
    concurrency="$2"
else
    # Read total RAM in KB from /proc/meminfo
    if [ -r /proc/meminfo ]; then
        mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
    else
        mem_kb=0
    fi

    if [ "$mem_kb" -gt 0 ]; then
        # conservative: reserve one process' worth of RAM for system and shell
        avail_for_workers=$(( mem_kb - PER_PROCESS_VMEM_KB ))
        if [ "$avail_for_workers" -le 0 ]; then
            concurrency=1
        else
            concurrency=$(( avail_for_workers / PER_PROCESS_VMEM_KB ))
            if [ "$concurrency" -lt 1 ]; then
                concurrency=1
            fi
        fi
    else
        # fallback
        concurrency="$nprocs"
    fi

    # never exceed CPU cores
    if [ "$concurrency" -gt "$nprocs" ]; then
        concurrency="$nprocs"
    fi
fi

mkdir -p "$output_dir"

# Initialize failure log
: > "$failed_log"

# Semaphore fifo
sem="/tmp/$$.sem"
mkfifo "$sem"
exec 3<> "$sem"
rm "$sem"

# Populate semaphore tokens
for ((i=0;i<concurrency;i++)); do
    printf '%s\n' "token" >&3
done

process_file() {
    local file="$1"
    local filename base_name parent_name target_dir output_file venv

    # Guarantee token is released even if function exits abnormally
    trap 'printf "%s\n" "token" >&3' RETURN

    filename=$(basename "$file")
    base_name="${filename%.*}"
    parent_name=$(basename "$(dirname "$file")")
    target_dir="$output_dir/$parent_name"
    mkdir -p "$target_dir"
    output_file="$target_dir/$base_name.cbz"

    echo "Converting: $file → $output_file"

    # Activate venv if present (do not fail the job if not)
    if [ -f ".venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        . .venv/bin/activate
    fi

    if python3 ereaderMangaOptimizer.py "$file" -o "$output_file"; then
        echo "✓ $parent_name/$base_name"
    else
        echo "✗ $parent_name/$base_name failed"
        echo "$file" >> "$failed_log"
    fi
}

export -f process_file

# Main loop: read files and spawn jobs
while IFS= read -r file; do
    # acquire token (blocks if none available)
    read -r -u 3 || true

    {
        process_file "$file"
    } &
done < <(find "$input_dir" -maxdepth 2 -type f \( -iname "*.pdf" -o -iname "*.cbz" \))

wait

# Report results
total_failed=$(wc -l < "$failed_log" 2>/dev/null || echo 0)
echo "Done. Failures: $total_failed"

if [ "$total_failed" -gt 0 ]; then
    echo "Failed files:"
    cat "$failed_log"
fi
