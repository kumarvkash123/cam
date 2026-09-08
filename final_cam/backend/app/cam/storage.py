"""Document storage helpers.

Local POC storage is anchored to the backend directory, not the process working
folder. This avoids preview failures when Flask is started from a different
folder on Windows. ``resolve_document_path`` also keeps older database rows
working when they contain relative or mixed-separator paths.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, Optional

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _configured_root() -> Path:
    raw = os.getenv("STORAGE_ROOT", "storage").strip() or "storage"
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = BACKEND_DIR / root
    return root.resolve(strict=False)


STORAGE_ROOT = _configured_root()


def build_stored_filename(application_id: str, doc_type: str, original_filename: str) -> str:
    ext = Path(original_filename or "document").suffix.lower()
    safe_doc_type = (doc_type or "unclassified").replace("/", "_").replace("\\", "_")
    return f"{application_id}_{safe_doc_type}{ext}"


def _normalise_legacy_path(raw: str) -> str:
    # DB rows created on Windows may contain a mixture of slash styles.
    return str(raw or "").strip().replace("\\", os.sep).replace("/", os.sep)


def _candidate_paths(
    stored_path: Optional[str],
    application_id: Optional[str] = None,
    stored_filename: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> Iterable[Path]:
    seen = set()

    def emit(p: Path):
        key = os.path.normcase(str(p.resolve(strict=False)))
        if key not in seen:
            seen.add(key)
            yield p

    raw = _normalise_legacy_path(stored_path or "")
    if raw:
        supplied = Path(raw).expanduser()
        if supplied.is_absolute():
            yield from emit(supplied)
        else:
            # Legacy values such as ./storage/app/file.pdf may have been
            # created relative to backend, repository root, or the current cwd.
            yield from emit((BACKEND_DIR / supplied).resolve(strict=False))
            yield from emit((Path.cwd() / supplied).resolve(strict=False))
            # If the row already contains "storage/...", avoid creating
            # backend/storage/storage/... and also try relative to backend parent.
            yield from emit((BACKEND_DIR.parent / supplied).resolve(strict=False))

    if application_id:
        names = [stored_filename, original_filename]
        if raw:
            names.append(Path(raw).name)
        for name in names:
            if name:
                yield from emit((STORAGE_ROOT / str(application_id) / Path(str(name)).name).resolve(strict=False))


def resolve_document_path(
    stored_path: Optional[str],
    application_id: Optional[str] = None,
    stored_filename: Optional[str] = None,
    original_filename: Optional[str] = None,
) -> Optional[str]:
    """Return the first existing file matching current or legacy storage data."""
    for candidate in _candidate_paths(stored_path, application_id, stored_filename, original_filename):
        try:
            if candidate.is_file():
                return str(candidate.resolve())
        except OSError:
            continue
    return None


def save_upload(tmp_path: str, application_id: str, doc_type: str, original_filename: str) -> str:
    source = resolve_document_path(tmp_path) or str(Path(tmp_path).expanduser().resolve(strict=False))
    if not Path(source).is_file():
        raise FileNotFoundError(f"Source upload is not available: {tmp_path}")

    app_dir = STORAGE_ROOT / str(application_id)
    app_dir.mkdir(parents=True, exist_ok=True)

    stored_name = build_stored_filename(application_id, doc_type, original_filename)
    dest_path = app_dir / stored_name

    counter = 1
    stem, suffix = dest_path.stem, dest_path.suffix
    while dest_path.exists():
        dest_path = app_dir / f"{stem}_v{counter}{suffix}"
        counter += 1

    shutil.copy2(source, dest_path)
    return str(dest_path.resolve())
