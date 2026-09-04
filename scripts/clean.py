import shutil
from pathlib import Path

MYAPP = 'manga_optimizer'
ROOT = Path(__file__).resolve().parents[1]

DIRECTORIES_TO_REMOVE = (
    ROOT / 'build',
    ROOT / 'dist',
)

FILES_TO_REMOVE = (
    ROOT / MYAPP+'.spec'
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
