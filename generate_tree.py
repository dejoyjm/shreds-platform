import os
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

EXCLUDE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', '.next', '.mypy_cache', '.idea', '.DS_Store'}
MAX_DEPTH = 3  # Change as needed

def tree(dir_path='.', prefix='', level=0):
    if level > MAX_DEPTH:
        return
    try:
        entries = sorted(
            [e for e in os.listdir(dir_path) if e not in EXCLUDE_DIRS and not e.startswith('.')],
            key=lambda s: s.lower()
        )
    except PermissionError:
        return

    for idx, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        connector = '├── ' if idx < len(entries) - 1 else '└── '
        print(prefix + connector + entry)
        if os.path.isdir(path):
            extension = '│   ' if idx < len(entries) - 1 else '    '
            tree(path, prefix + extension, level + 1)

if __name__ == '__main__':
    tree()
