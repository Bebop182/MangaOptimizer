import shutil
from pathlib import Path

MYAPP = 'manga_optimizer'
ROOT = Path(__file__).resolve().parents[1]

DIRECTORIES_TO_REMOVE = (
    ROOT / 'build',
    ROOT / 'dist',
    ROOT / 'src' / (MYAPP + '.egg-info'),
    ROOT / 'src' / MYAPP / '__pycache__',
    ROOT / 'src' / MYAPP / 'export' / '__pycache__',
    ROOT / '.pytest_cache',
    ROOT / 'tests' / 'unit' / '__pycache__',
)

FILES_TO_REMOVE = (
    ROOT / (MYAPP.replace('_', '-') + '.spec'),
)

def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        print(f'Removed directory: {path}')
    elif path.is_file():
        path.unlink()
        print(f'Removed file: {path}')


def main() -> None:
    for path in (*DIRECTORIES_TO_REMOVE, *FILES_TO_REMOVE):
        remove(path)


if __name__ == '__main__':
    main()
