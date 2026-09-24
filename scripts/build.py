from pathlib import Path
import subprocess
import sys
import os

PACKAGE_NAME = "manga_optimizer"
# resolve() get absolute path
# path = Path("/home/user/project/scripts/build.py")

# path.parent       # /home/user/project/scripts
# path.parents[0]   # /home/user/project/scripts
# path.parents[2]   # /home/user
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / PACKAGE_NAME
ENTRY_POINT = APP / "__main__.py"
VENV = ROOT / ".venv" / "bin"

# print command to standard output


def run(command: list[str]) -> None:
    print("$", " ".join(map(str, command)))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    if not ENTRY_POINT.is_file():
        raise FileNotFoundError(f"Entry point not found: {ENTRY_POINT}")

    appname = PACKAGE_NAME.replace("_", "-")
    resources_path = APP / "resources"

    # run pyinstaller
    pyinstaller = [
        VENV / "pyinstaller",
        "--onefile",
        # "--onedir",
        "--paths", ROOT / "src",
        "--name", appname,
        "--copy-metadata", appname,
        "--add-data", f'{APP}/resources{os.pathsep}{PACKAGE_NAME}/resources',
        ENTRY_POINT
    ]
    run(pyinstaller)


if __name__ == "__main__":
    main()
