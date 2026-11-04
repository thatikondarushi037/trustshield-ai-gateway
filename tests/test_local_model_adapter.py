
import unittest
from unittest.mock import Mock, patch

from src.local_model_adapter import generate_local_response


class TestLocalModelAdapter(unittest.TestCase):

    @patch("src.local_model_adapter.httpx.Client")
    def test_successful_generation(self, client_class):
        response = Mock()
        response.json.return_value = {
            "done": True,
            "response": "Machine learning learns patterns."
        }

        client = client_class.return_value.__enter__.return_value
        client.post.return_value = response

        answer = generate_local_response(
            "Explain machine learning."
        )

        self.assertEqual(
            answer,
            "Machine learning learns patterns."
        )
        response.raise_for_status.assert_called_once()

    @patch("src.local_model_adapter.httpx.Client")
    def test_invalid_response(self, client_class):
        response = Mock()
        response.json.return_value = {
            "done": False
        }

        client = client_class.return_value.__enter__.return_value
        client.post.return_value = response

        with self.assertRaises(ValueError):
            generate_local_response("Hello")

    @patch("src.local_model_adapter.httpx.Client")
    def test_empty_prompt_never_calls_backend(self, client_class):
        with self.assertRaises(ValueError):
            generate_local_response("   ")

        client_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
