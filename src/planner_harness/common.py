from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def page(text, start=1, max_chars=12000, *, start_char=0, split_long_lines=False):
    """Return complete numbered lines and an explicit continuation position."""
    lines = text.splitlines()
    start = int(start)
    if start < 1 or start > max(len(lines), 1):
        raise ValueError(f"start_line must be between 1 and {max(len(lines), 1)}")
    if split_long_lines:
        if type(start_char) is not int or start_char < 0 or (lines and start_char > len(lines[start - 1])):
            raise ValueError("Invalid within-line character offset")
        chunks, size, end_char = [], 0, start_char
        end = start - 1
        following, next_char = None, 0
        for i in range(start - 1, len(lines)):
            offset = start_char if i == start - 1 else 0
            prefix = f"{i + 1}: "
            remaining = max_chars - size - len(prefix) - 1
            if remaining <= 0:
                following, next_char = i + 1, offset
                break
            fragment = lines[i][offset:offset + remaining]
            chunks.append(prefix + fragment)
            size += len(prefix) + len(fragment) + 1
            end, end_char = i + 1, offset + len(fragment)
            if end_char < len(lines[i]):
                following, next_char = i + 1, end_char
                break
        return {"text": "\n".join(chunks), "start_line": start, "start_char": start_char,
                "end_line": end, "end_char": end_char, "total_lines": len(lines),
                "next_line": following, "next_char": next_char,
                "pagination": "Exact source characters; continue at next_line/next_char. A long line may span pages."}
    chunks, size, end = [], 0, start - 1
    for i in range(start - 1, len(lines)):
        chunk = f"{i + 1}: {lines[i]}"
        if chunks and size + len(chunk) > max_chars:
            break
        # A single original line is never cut silently.
        chunks.append(chunk)
        size += len(chunk) + 1
        end = i + 1
    return {"text": "\n".join(chunks), "start_line": start, "end_line": end,
            "total_lines": len(lines), "next_line": end + 1 if end < len(lines) else None}
