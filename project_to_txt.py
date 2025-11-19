#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Собирает в один TXT:
1) Дерево проекта (tree) в начале файла
2) Текстовое содержимое файлов проекта

Пропускает бинарные файлы, большие файлы и служебные директории.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode",
    "node_modules", "dist", "build", "out",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", ".tox", "coverage", ".gradle", ".terraform",
}

DEFAULT_EXCLUDE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".psd", ".ai",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".avi", ".mov",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".o", ".a",
    ".ttf", ".otf", ".woff", ".woff2",
    ".sqlite", ".db",
    ".pyc", ".pyo",
}

def is_probably_binary(path: Path, sample_size: int = 4096) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(sample_size)
        if not chunk:
            return False
        if b"\x00" in chunk:
            return True
        text_like = sum(32 <= b <= 126 or b in (9, 10, 13) for b in chunk)
        return (text_like / max(1, len(chunk))) < 0.8
    except Exception:
        return True

def read_text_best_effort(path: Path) -> str:
    encodings = ["utf-8", "utf-16", "cp1251", "latin-1"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    try:
        with path.open("rb") as f:
            data = f.read()
        return data.decode("latin-1", errors="replace")
    except Exception:
        return ""

def should_skip_file(path: Path, max_bytes: int) -> bool:
    if path.suffix.lower() in DEFAULT_EXCLUDE_EXTS:
        return True
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return True
    except Exception:
        return True
    return is_probably_binary(path)

def list_dir_sorted(p: Path, include_hidden: bool, exclude_dirs: set) -> Tuple[List[Path], List[Path]]:
    """Возвращает (dirs, files) отсортированные case-insensitive, dirs сначала."""
    try:
        entries = list(p.iterdir())
    except Exception:
        return [], []
    dirs = []
    files = []
    for e in entries:
        name = e.name
        if not include_hidden and name.startswith("."):
            continue
        if e.is_dir():
            if name in exclude_dirs or name.startswith(".cache"):
                continue
            dirs.append(e)
        elif e.is_file():
            files.append(e)
    key = lambda x: x.name.lower()
    return sorted(dirs, key=key), sorted(files, key=key)

def build_tree(root: Path, include_hidden: bool, exclude_dirs: set) -> str:
    """Строит текстовое дерево каталога, похоже на вывод `tree`."""
    lines: List[str] = [f"{root.name}/"]

    def walk(dir_path: Path, prefix: str):
        dirs, files = list_dir_sorted(dir_path, include_hidden, exclude_dirs)
        items = dirs + files
        for i, item in enumerate(items):
            connector = "└── " if i == len(items) - 1 else "├── "
            lines.append(prefix + connector + item.name + ("/" if item.is_dir() else ""))
            if item.is_dir():
                extension = "    " if i == len(items) - 1 else "│   "
                walk(item, prefix + extension)

    walk(root, "")
    return "\n".join(lines)

def collect_files(root: Path, exclude_dirs: set[str], include_hidden: bool) -> List[Path]:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        # фильтруем служебные директории на лету
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude_dirs and (include_hidden or not d.startswith(".")) and not d.startswith(".cache")
        ]
        if not include_hidden:
            filenames = [f for f in filenames if not f.startswith(".")]
        for fn in filenames:
            result.append(Path(dirpath) / fn)
    return result

def main():
    parser = argparse.ArgumentParser(description="Склейка содержимого проекта в один TXT + дерево проекта.")
    parser.add_argument("root", nargs="?", default=".", help="Корень проекта (по умолчанию текущая папка).")
    parser.add_argument("-o", "--output", default="project_dump.txt", help="Путь к выходному TXT.")
    parser.add_argument("--max-bytes", type=int, default=3 * 1024 * 1024,
                        help="Макс. размер файла для включения (в байтах), по умолчанию 524288.")
    parser.add_argument("--include-hidden", action="store_true",
                        help="Включать скрытые файлы/папки (по умолчанию — нет).")
    parser.add_argument("--extra-include-ext", action="append", default=[],
                        help="Дополнительно включить расширение (например: --extra-include-ext .pdf).")
    parser.add_argument("--extra-exclude-dir", action="append", default=["tmp", 'storage'],
                        help="Дополнительно исключить директорию по имени (можно несколько).")
    args = parser.parse_args()

    args.root = "Agents"
    args.output = "agents_dump.txt"
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Путь не найден: {root}", file=sys.stderr)
        sys.exit(1)

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(['screenshots', 'browser_profile'])

    # 1) Пишем заголовок и TREE проекта
    with open(args.output, "w", encoding="utf-8", errors="replace") as out:
        out.write(f"# PROJECT MERGE DUMP\n# Root: {root}\n\n")
        out.write("## PROJECT TREE\n")
        out.write("(исключены служебные директории; используйте --include-hidden для скрытых файлов)\n\n")
        try:
            tree_str = build_tree(root, include_hidden=args.include_hidden, exclude_dirs=exclude_dirs)
        except Exception as e:
            tree_str = f"[Не удалось построить дерево: {e}]"
        out.write(tree_str + "\n\n")
        out.write("## FILE CONTENTS\n")

    # 2) Дописываем содержимое файлов
    files = collect_files(root, exclude_dirs, include_hidden=args.include_hidden)
    force_include_exts = {e.lower() for e in args.extra_include_ext}

    with open(args.output, "a", encoding="utf-8", errors="replace") as out:
        for path in sorted(files):
            rel = path.relative_to(root)

            if not path.is_file():
                continue

            ext = path.suffix.lower()
            skip = False
            if ext in force_include_exts:
                skip = False
            else:
                skip = should_skip_file(path, args.max_bytes)
            if skip:
                continue

            try:
                size = path.stat().st_size
            except Exception:
                size = -1

            header = f"\n\n===== FILE START: {rel} | size={size} bytes =====\n"
            out.write(header)

            try:
                text = read_text_best_effort(path)
                out.write(text)
            except Exception as e:
                out.write(f"[ОШИБКА ЧТЕНИЯ: {e}]")

            out.write(f"\n===== FILE END: {rel} =====\n")

    print(f"Готово: {args.output}")

if __name__ == "__main__":
    main()
