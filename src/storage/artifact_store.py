"""Content-addressed artifact storage with digest-safe deduplication."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import os
import json
from typing import Dict, Mapping, Optional, Tuple
from uuid import uuid4


@dataclass(frozen=True)
class BlobRef:
    """Immutable reference to bytes stored by verified content digest."""
    digest: str
    size: int
    path: Path


@dataclass
class ArtifactMetadata:
    """Metadata for a logically-named artifact pointing to a physical blob."""
    name: str
    blob: BlobRef
    created_at: float
    custom_metadata: Dict = field(default_factory=dict)


class ArtifactDigestMismatchError(Exception):
    """Raised when a supplied digest does not match the actual content bytes."""
    pass


def sha256_digest(data: bytes) -> str:
    """Compute hex SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


class ContentAddressedArtifactStore:
    """
    Storage layer that ensures deduplication via content-addressing.
    Physical storage uses verified content digests; logical names map to digests.
    """
    def __init__(self, base_path: str | Path):
        self.root = Path(base_path)
        self.blobs_dir = self.root / "blobs"
        self.metadata_dir = self.root / "metadata"
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, data: bytes, expected_digest: str | None = None,
            metadata: Dict | None = None) -> ArtifactMetadata:
        """
        Store an artifact by logical name.
        Always verifies content digest before linking.
        """
        actual_digest = sha256_digest(data)
        
        if expected_digest and expected_digest != actual_digest:
            # Still store the verified blob for audit, but reject the metadata link
            self._ensure_blob(actual_digest, data)
            raise ArtifactDigestMismatchError(
                f"Supplied digest {expected_digest} does not match actual {actual_digest}"
            )

        blob = self._ensure_blob(actual_digest, data)
        
        # Create metadata linking the name to this immutable blob
        meta = ArtifactMetadata(
            name=name,
            blob=blob,
            created_at=0.0,  # In real impl use time.time()
            custom_metadata=metadata or {}
        )
        
        self._save_metadata(meta)
        return meta

    def _ensure_blob(self, digest: str, data: bytes) -> BlobRef:
        path = self.blobs_dir / digest
        if not path.exists():
            path.write_bytes(data)
        return BlobRef(digest=digest, size=len(data), path=path)

    def _save_metadata(self, meta: ArtifactMetadata) -> None:
        path = self.metadata_dir / f"{meta.name}.json"
        with open(path, "w") as f:
            json.dump({
                "name": meta.name,
                "digest": meta.blob.digest,
                "size": meta.blob.size,
                "custom_metadata": meta.custom_metadata
            }, f)

    def get(self, name: str) -> Tuple[bytes, ArtifactMetadata]:
        """Retrieve bytes and metadata for a logical name."""
        path = self.metadata_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Artifact {name} not found")
            
        with open(path, "r") as f:
            data = json.load(f)
            
        blob_path = self.blobs_dir / data["digest"]
        content = blob_path.read_bytes()
        
        meta = ArtifactMetadata(
            name=data["name"],
            blob=BlobRef(digest=data["digest"], size=data["size"], path=blob_path),
            created_at=0.0,
            custom_metadata=data["custom_metadata"]
        )
        
        return content, meta
