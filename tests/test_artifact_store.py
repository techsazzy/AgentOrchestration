"""Regression tests for digest-safe artifact deduplication."""

import pytest
from pathlib import Path
from src.storage.artifact_store import (
    ArtifactDigestMismatchError,
    ContentAddressedArtifactStore,
    sha256_digest,
)


def test_same_name_different_content_creates_distinct_blobs(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path)

    # First version of logical name "config"
    data1 = b"v1 content"
    digest1 = sha256_digest(data1)
    meta1 = store.put("config", data1)
    
    assert meta1.blob.digest == digest1
    assert (tmp_path / "blobs" / digest1).exists()

    # Second version of logical name "config" (different content)
    data2 = b"v2 content"
    digest2 = sha256_digest(data2)
    meta2 = store.put("config", data2)

    assert meta2.blob.digest == digest2
    assert (tmp_path / "blobs" / digest2).exists()
    assert digest1 != digest2
    
    # Verify we can still get v2
    content, meta = store.get("config")
    assert content == data2


def test_shared_content_deduplication(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path)

    data = b"shared secret content"
    digest = sha256_digest(data)

    # Store under two different logical names
    store.put("agent_1_key", data)
    store.put("agent_2_key", data)

    # Verify physical storage only has ONE blob
    blobs = list((tmp_path / "blobs").iterdir())
    assert len(blobs) == 1
    assert blobs[0].name == digest


def test_digest_mismatch_rejection(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path)

    data = b"correct content"
    wrong_digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # empty string digest

    with pytest.raises(ArtifactDigestMismatchError):
        store.put("malicious", data, expected_digest=wrong_digest)

    # Metadata should NOT have been created for the logical name
    assert not (tmp_path / "metadata" / "malicious.json").exists()
    
    # But the physical blob should still be stored (for forensics/audit)
    actual_digest = sha256_digest(data)
    assert (tmp_path / "blobs" / actual_digest).exists()
