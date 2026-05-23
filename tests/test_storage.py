import pytest
import os
import shutil
from src.common.storage import BlobStore


class TestBlobStore:
    def setup_method(self):
        self.test_dir = "/tmp/test_blobstore"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        self.store = BlobStore(self.test_dir)

    def teardown_method(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_upload_and_deduplication(self):
        data = b"hello world"
        name1 = "file1.txt"
        name2 = "file2.txt"

        # Upload first file
        digest1 = self.store.upload_artifact(name1, data)
        
        # Upload second file with same content
        digest2 = self.store.upload_artifact(name2, data)

        # Digests should be identical (deduplicated)
        assert digest1 == digest2
        
        # Verify only one blob exists
        blobs = os.listdir(os.path.join(self.test_dir, "blobs"))
        assert len(blobs) == 1
        assert blobs[0] == digest1

    def test_different_content_same_name(self):
        name = "config.json"
        data1 = b'{"version": 1}'
        data2 = b'{"version": 2}'

        # Upload first version
        digest1 = self.store.upload_artifact(name, data1)
        
        # Upload second version with same logical name
        digest2 = self.store.upload_artifact(name, data2)

        # Digests should be different
        assert digest1 != digest2
        
        # Both blobs should exist
        blobs = os.listdir(os.path.join(self.test_dir, "blobs"))
        assert len(blobs) == 2
        
        # Metadata should point to the LATEST upload for that name
        _, meta = self.store.get_artifact(name)
        assert meta["digest"] == digest2

    def test_metadata_consistency(self):
        name = "data.bin"
        data = b"\x00\x01\x02\x03"
        metadata = {"project": "alpha", "priority": "high"}
        
        digest = self.store.upload_artifact(name, data, metadata=metadata)
        
        retrieved_data, retrieved_meta = self.store.get_artifact(name)
        assert retrieved_data == data
        assert retrieved_meta["digest"] == digest
        assert retrieved_meta["custom_metadata"]["project"] == "alpha"
