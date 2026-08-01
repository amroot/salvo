import unittest
from salvo.protocols.h11 import Request, RequestTemplate

class TestRequest(unittest.TestCase):
    def test_basic_get(self):
        req = Request("GET", "/")
        raw = req.to_bytes("example.com")
        self.assertIn(b"GET / HTTP/1.1", raw)
        self.assertIn(b"Host: example.com", raw)
        self.assertIn(b"Connection: keep-alive", raw)

    def test_post_with_body(self):
        req = Request("POST", "/api", body="data")
        raw = req.to_bytes("api.com")
        self.assertIn(b"POST /api HTTP/1.1", raw)
        self.assertIn(b"Content-Length: 4", raw)
        self.assertTrue(raw.endswith(b"\r\n\r\ndata"))

    def test_custom_headers(self):
        req = Request("GET", "/", headers={"X-Test": "Value"})
        raw = req.to_bytes("test.com")
        self.assertIn(b"X-Test: Value", raw)

    def test_request_template_preserves_method(self):
        request = RequestTemplate("POST", "http://example.com/{FUZZ}").render("item")

        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/item")

if __name__ == "__main__":
    unittest.main()
