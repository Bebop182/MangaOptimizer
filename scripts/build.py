import subprocess
import sys
from pathlib import Path

APP_NAME = 'manga_optimizer'
ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = ROOT / 'src' / APP_NAME.replace('_', '') / '__main__.py'

def run(command: list[str]) -> None:
    print('$', ' '.join(map(str, command)))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    if not ENTRY_POINT.is_file():
        raise FileNotFoundError(f'Entry point not found: {ENTRY_POINT}')

    # Remove previous build artifacts.
    run([sys.executable, str(ROOT / 'scripts' / 'clean.py')])

    # Build a single-file executable.
    run(
        [
            sys.executable,
            '-m',
            'PyInstaller',
            '--noconfirm',
            '--clean',
            '--onefile',
            '--name',
            APP_NAME,
            '--paths',
            str(ROOT / 'src'),
            str(ENTRY_POINT),
        ]
    )

    executable = ROOT / 'dist' / APP_NAME
    if sys.platform == 'win32':
        executable = executable.with_suffix('.exe')

    print(f'\nBuild complete: {executable}')


if __name__ == '__main__':
    main()
