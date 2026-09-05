from shutil import which
from pathlib import Path
import subprocess

def epub_to_mobi(epub: Path):
    kindlegen_path = which("kindlegen")  # Searches PATH for the executable
    if kindlegen_path is None:
        raise RuntimeError(
            "kindlegen is required. Install it and ensure it is on PATH."
        )

    kindlegen_cmd = [
        kindlegen_path,
        epub,
        '-c0',
        '-dont_append-source',
    ]

    try:
        result = subprocess.run(
            kindlegen_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        print(f"kindlegen failed with exit code {error.returncode}")
    else:
        return epub.with_suffix('mobi')
    return None
