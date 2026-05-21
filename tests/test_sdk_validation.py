import unittest
from src.sdk.client import OrchestratorClient

class TestSDKValidation(unittest.TestCase):
    def test_url_normalization_strips_trailing_slash(self):
        # Test that trailing slashes are normalized
        client = OrchestratorClient(base_url="https://api.example.com/")
        self.assertEqual(client.base_url, "https://api.example.com")

    def test_url_normalization_handles_no_slash(self):
        client = OrchestratorClient(base_url="https://api.example.com")
        self.assertEqual(client.base_url, "https://api.example.com")

if __name__ == "__main__":
    unittest.main()
