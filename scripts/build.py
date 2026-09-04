import subprocess
import sys
from pathlib import Path

APP_NAME = 'manga_optimizer'
# resolve() get absolute path
# path = Path("/home/user/project/scripts/build.py")

# path.parent       # /home/user/project/scripts
# path.parents[0]   # /home/user/project/scripts
# path.parents[2]   # /home/user
ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = ROOT / 'src' / APP_NAME / '__main__.py'
VENV = ROOT / '.venv' / 'bin'

# print command to standard output
def run(command: list[str]) -> None:
    print('$', ' '.join(map(str, command)))
    subprocess.run(command, cwd=ROOT, check=True)

def main() -> None:
    if not ENTRY_POINT.is_file():
        raise FileNotFoundError(f'Entry point not found: {ENTRY_POINT}')
    
    # run pyinstaller
    pyinstaller = [
        VENV / 'pyinstaller',
        '--onefile',
        '--paths', ROOT / 'src',
        '--name', APP_NAME,
        ENTRY_POINT
    ]
    run(pyinstaller)

if __name__ == '__main__':
    main()
