"""ADR 0006 acceptance check: no video in the cloud database or hosting files.

    python -m app.jobs.no_video_check [DIR ...]     (exit 1 if anything is found)

Database: no binary columns (bytea/blob) in any table of the current schema.
Files: no video/photo files by extension OR by magic bytes (renamed files too).
Allowed: the PWA's own icons (icon-*.png, apple-touch-icon.png, icon.svg).
"""

import os
import sys
from typing import Iterable, List

from sqlalchemy import inspect
from sqlalchemy.types import LargeBinary

MEDIA_EXT = {".mp4", ".mkv", ".avi", ".mov", ".h264", ".h265", ".hevc", ".ts", ".m3u8",
             ".webm", ".jpg", ".jpeg", ".webp", ".heic", ".bmp", ".gif"}
MAGIC = [
    (4, b"ftyp"),            # MP4 / MOV / HEIC
    (0, b"\x1a\x45\xdf\xa3"),  # Matroska / WebM
    (0, b"RIFF"),            # AVI / WEBP
    (0, b"\xff\xd8\xff"),    # JPEG
    (0, b"\x00\x00\x00\x01\x67"),  # raw H.264 NAL
    (0, b"GIF8"),
]
ALLOWED = {"icon-192.png", "icon-512.png", "apple-touch-icon.png", "icon.svg"}


def db_findings(engine) -> List[str]:
    out = []
    insp = inspect(engine)
    for table in insp.get_table_names():
        for col in insp.get_columns(table):
            t = col["type"]
            name = type(t).__name__.lower()
            if isinstance(t, LargeBinary) or name in ("bytea", "blob", "binary", "varbinary"):
                out.append(f"db: binary column {table}.{col['name']}")
    return out


def file_findings(dirs: Iterable[str]) -> List[str]:
    out = []
    for root_dir in dirs:
        for root, _dirs, files in os.walk(root_dir):
            for f in files:
                path = os.path.join(root, f)
                if f in ALLOWED:
                    continue
                if os.path.splitext(f)[1].lower() in MEDIA_EXT:
                    out.append(f"file: media extension {path}")
                    continue
                try:
                    with open(path, "rb") as fh:
                        head = fh.read(16)
                except OSError:
                    continue
                if any(head[off:off + len(sig)] == sig for off, sig in MAGIC):
                    out.append(f"file: media signature {path}")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from app.core.config import get_settings
    from app.db.session import make_engine
    engine = make_engine(get_settings().database_url)
    findings = db_findings(engine) + file_findings(argv)
    engine.dispose()
    for f in findings:
        print(f)
    print("NO VIDEO: OK" if not findings else f"FOUND {len(findings)} PROBLEM(S)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
