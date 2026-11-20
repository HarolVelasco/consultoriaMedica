import json
import unittest
from unittest.mock import MagicMock, Mock, patch

import httpx

from backend.services import vision_service
from backend.services.vision_service import _resumir_error_gemini


class ResumirErrorGeminiTests(unittest.TestCase):
    def test_api_key_is_sent_in_header_not_url(self):
        response = Mock()
        response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "nombre_completo": None,
                                        "numero_documento": None,
                                        "confianza": 0.9,
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.return_value = response

        with patch.object(vision_service, "GEMINI_API_KEY", "secret-test-key"):
            with patch.object(vision_service.httpx, "Client", return_value=client):
                vision_service.extraer_con_gemini(b"image")

        args, kwargs = client.post.call_args
        self.assertNotIn("key=", args[0])
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "secret-test-key")

    def test_http_status_summary_does_not_include_api_key(self):
        request = httpx.Request(
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent?key=secret-test-key",
        )
        response = httpx.Response(404, request=request)
        error = httpx.HTTPStatusError(
            "Not found",
            request=request,
            response=response,
        )

        message = _resumir_error_gemini(error)

        self.assertIn("HTTP 404", message)
        self.assertNotIn("secret-test-key", message)

    def test_quota_error_is_explained_without_raw_response(self):
        request = httpx.Request("POST", "https://example.test/generateContent")
        response = httpx.Response(429, request=request)
        error = httpx.HTTPStatusError(
            "Too many requests",
            request=request,
            response=response,
        )

        self.assertIn("límite de solicitudes", _resumir_error_gemini(error))

    def test_api_failure_falls_back_without_saving_key_in_error(self):
        request = httpx.Request(
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/models/test:generateContent?key=secret-test-key",
        )
        response = httpx.Response(404, request=request)
        error = httpx.HTTPStatusError(
            "Not found",
            request=request,
            response=response,
        )

        with patch.object(vision_service, "GEMINI_API_KEY", "secret-test-key"):
            with patch.object(
                vision_service,
                "extraer_con_gemini",
                side_effect=error,
            ):
                result = vision_service.procesar_cedula(b"image")

        self.assertEqual(result["motor"], "demo_fallback")
        self.assertIn("HTTP 404", result["error_api"])
        self.assertNotIn("secret-test-key", result["error_api"])


if __name__ == "__main__":
    unittest.main()
