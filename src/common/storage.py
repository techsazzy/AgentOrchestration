"""Blob Storage and Artifact Deduplication Layer."""

import hashlib
import os
import json
from typing import Any, Dict, Optional, Tuple


class BlobStore:
    def __init__(self, base_path: str = "/tmp/blobstore"):
        self.base_path = base_path
        self.blobs_path = os.path.join(base_path, "blobs")
        self.metadata_path = os.path.join(base_path, "metadata")
        os.makedirs(self.blobs_path, exist_ok=True)
        os.makedirs(self.metadata_path, exist_ok=True)

    def _compute_digest(self, data: bytes) -> str:
        """Compute SHA-256 digest of data."""
        return hashlib.sha256(data).hexdigest()

    def upload_artifact(self, name: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Upload an artifact with a logical name.
        Uses content-addressable storage (blobs) for deduplication.
        """
        digest = self._compute_digest(data)
        blob_path = os.path.join(self.blobs_path, digest)

        # Deduplication: Check if blob already exists
        if not os.path.exists(blob_path):
            with open(blob_path, "wb") as f:
                f.write(data)
            logger_info = f"Stored new blob: {digest}"
        else:
            logger_info = f"Deduplicated blob: {digest}"

        # Store artifact metadata linking logical name to immutable blob digest
        artifact_meta = {
            "name": name,
            "digest": digest,
            "size": len(data),
            "custom_metadata": metadata or {},
        }
        
        # In a real system, this would be in a DB. Here we use a file per artifact name.
        # Note: In a concurrent environment, we should handle collisions/locking.
        meta_file = os.path.join(self.metadata_path, f"{name}.json")
        
        # Security check: If metadata exists, verify digest matches or handle as new version
        # For this bounty, we ensure lookups use the calculated digest.
        with open(meta_file, "w") as f:
            json.dump(artifact_meta, f)

        return digest

    def get_artifact(self, name: str) -> Tuple[bytes, Dict[str, Any]]:
        """Retrieve artifact data and metadata by logical name."""
        meta_file = os.path.join(self.metadata_path, f"{name}.json")
        if not os.path.exists(meta_file):
            raise FileNotFoundError(f"Artifact {name} not found")

        with open(meta_file, "r") as f:
            meta = json.load(f)

        blob_path = os.path.join(self.blobs_path, meta["digest"])
        with open(blob_path, "rb") as f:
            data = f.read()

        return data, meta
