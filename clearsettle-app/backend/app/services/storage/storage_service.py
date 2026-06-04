"""
Storage service abstraction for uploaded files.

Environment variables:
  STORAGE_BACKEND  = local (default) | gcs
  UPLOAD_DIR       = /data/uploads   (local backend, mount a persistent volume here)
  GCS_BUCKET_NAME  = clearsettle-uploads  (gcs backend)
  GCS_UPLOAD_PREFIX = uploads             (optional GCS key prefix)

Bucket path pattern (both backends):
  {company_id}/{year}/{month}/{uuid}{ext}

For local dev: UPLOAD_DIR defaults to /data/uploads (not /tmp — ephemeral).
For production: mount a persistent disk at /data/uploads or set GCS_BUCKET_NAME.
"""
from __future__ import annotations

import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")


class StorageService(ABC):
    """Abstract base — save/read/delete/exists for uploaded file bytes."""

    @abstractmethod
    def save(self, file_bytes: bytes, ext: str, company_id: str) -> str:
        """Persist bytes and return an opaque storage key (path or GCS URI)."""

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Return raw bytes for a previously saved file. Raises FileNotFoundError."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete the stored file. Silently ignores missing files."""

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Return True if the file exists in storage."""


# ── Local filesystem backend ──────────────────────────────────────────────────

class LocalStorageService(StorageService):
    """Stores files on the local filesystem under base_dir.

    Production: mount a persistent volume at the path set in UPLOAD_DIR
    (e.g. a GCP Persistent Disk or NFS share).  Never use the container's
    ephemeral /tmp/ for business-critical files.

    Path layout:
      {base_dir}/{company_id}/{year}/{month}/{uuid}{ext}
    """

    def __init__(self, base_dir: str = _DEFAULT_UPLOAD_DIR) -> None:
        self.base_dir = base_dir

    def _make_path(self, ext: str, company_id: str) -> str:
        now = datetime.utcnow()
        subdir = os.path.join(
            self.base_dir,
            str(company_id),
            str(now.year),
            f"{now.month:02d}",
        )
        os.makedirs(subdir, exist_ok=True)
        filename = f"{uuid.uuid4()}{ext}"
        return os.path.join(subdir, filename)

    def save(self, file_bytes: bytes, ext: str, company_id: str) -> str:
        path = self._make_path(ext, company_id)
        with open(path, "wb") as fh:
            fh.write(file_bytes)
        logger.debug("Saved %d bytes to %s", len(file_bytes), path)
        return path

    def read(self, storage_key: str) -> bytes:
        if not os.path.exists(storage_key):
            raise FileNotFoundError(f"File not found in local storage: {storage_key}")
        with open(storage_key, "rb") as fh:
            return fh.read()

    def delete(self, storage_key: str) -> None:
        try:
            os.remove(storage_key)
        except FileNotFoundError:
            pass

    def exists(self, storage_key: str) -> bool:
        return os.path.exists(storage_key)


# ── Google Cloud Storage backend ──────────────────────────────────────────────

class GCSStorageService(StorageService):
    """Stores files in Google Cloud Storage.

    Requires:
      GCS_BUCKET_NAME env var (e.g. clearsettle-uploads)
      GOOGLE_APPLICATION_CREDENTIALS env var or Workload Identity

    Blob key layout:
      {prefix}/{company_id}/{year}/{month}/{uuid}{ext}
    """

    def __init__(
        self,
        bucket_name: str,
        prefix: str = "uploads",
    ) -> None:
        try:
            from google.cloud import storage as gcs  # type: ignore
            self._client = gcs.Client()
            self._bucket = self._client.bucket(bucket_name)
            self._prefix = prefix
            logger.info("GCS storage backend initialised (bucket=%s)", bucket_name)
        except ImportError as e:
            raise RuntimeError(
                "google-cloud-storage is not installed. "
                "Run: pip install google-cloud-storage"
            ) from e

    def _make_blob_name(self, ext: str, company_id: str) -> str:
        now = datetime.utcnow()
        return (
            f"{self._prefix}/{company_id}/{now.year}/{now.month:02d}"
            f"/{uuid.uuid4()}{ext}"
        )

    def save(self, file_bytes: bytes, ext: str, company_id: str) -> str:
        blob_name = self._make_blob_name(ext, company_id)
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(file_bytes)
        uri = f"gs://{self._bucket.name}/{blob_name}"
        logger.debug("Saved %d bytes to %s", len(file_bytes), uri)
        return uri

    def read(self, storage_key: str) -> bytes:
        blob_name = storage_key.replace(f"gs://{self._bucket.name}/", "", 1)
        blob = self._bucket.blob(blob_name)
        if not blob.exists():
            raise FileNotFoundError(f"GCS object not found: {storage_key}")
        return blob.download_as_bytes()

    def delete(self, storage_key: str) -> None:
        try:
            blob_name = storage_key.replace(f"gs://{self._bucket.name}/", "", 1)
            self._bucket.blob(blob_name).delete()
        except Exception:
            pass

    def exists(self, storage_key: str) -> bool:
        blob_name = storage_key.replace(f"gs://{self._bucket.name}/", "", 1)
        return self._bucket.blob(blob_name).exists()


# ── Factory ───────────────────────────────────────────────────────────────────

_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    """Return a singleton storage service based on STORAGE_BACKEND env var."""
    global _instance
    if _instance is not None:
        return _instance

    backend = os.environ.get("STORAGE_BACKEND", "local").lower()

    if backend == "gcs":
        bucket = os.environ.get("GCS_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("GCS_BUCKET_NAME must be set when STORAGE_BACKEND=gcs")
        prefix = os.environ.get("GCS_UPLOAD_PREFIX", "uploads")
        _instance = GCSStorageService(bucket_name=bucket, prefix=prefix)
    else:
        upload_dir = os.environ.get("UPLOAD_DIR", _DEFAULT_UPLOAD_DIR)
        _instance = LocalStorageService(base_dir=upload_dir)
        logger.info("Local storage backend initialised (dir=%s)", upload_dir)

    return _instance
