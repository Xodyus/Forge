"""Safe atomic file publication (Appendix C §361, §362 "atomic publication").

Write to a uniquely-named temporary file in the destination directory, fsync it,
`os.replace` it into place, then fsync the directory entry. A reader can never
observe a partially written dataset file: it either doesn't exist yet or is
complete, because nothing ever writes to `destination` directly.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

Writer = Callable[[BinaryIO], None]


class _DigestingWriter:
    def __init__(self, raw: BinaryIO) -> None:
        self._raw = raw
        self._digest = hashlib.sha256()
        self.byte_count = 0

    def write(self, data: bytes) -> int:
        written = self._raw.write(data)
        if written != len(data):
            raise OSError("short buffered file write")
        self._digest.update(data)
        self.byte_count += written
        return written

    def flush(self) -> None:
        self._raw.flush()

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


def write_atomic(destination: Path, writer: Writer, *, mode: int = 0o640) -> tuple[int, str]:
    """Write via `writer` and atomically publish at `destination`.

    Returns `(byte_count, sha256_hexdigest)` over exactly the bytes `writer` wrote.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")

    try:
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
        with os.fdopen(fd, "wb", buffering=1024 * 1024) as raw:
            wrapped = _DigestingWriter(raw)
            writer(wrapped)  # type: ignore[arg-type]
            wrapped.flush()
            os.fsync(raw.fileno())

        os.replace(temporary, destination)
        if os.name == "posix":
            # Durably persist the directory entry itself, not just the file's
            # contents. Windows has no equivalent of opening a directory as a file
            # descriptor to fsync; NTFS journals metadata for os.replace on its own.
            directory_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    return wrapped.byte_count, wrapped.hexdigest()
