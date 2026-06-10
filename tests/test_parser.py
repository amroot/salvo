import unittest
from salvo.protocols.h11 import ResponseParser
import time

class TestParser(unittest.TestCase):
    def test_content_length(self):
        parser = ResponseParser()
        raw_resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 5\r\n"
            b"\r\n"
            b"Hello"
        )
        parser.feed(raw_resp)
        resp = parser.parse_next(time.time())
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body, b"Hello")

    def test_chunked(self):
        parser = ResponseParser()
        raw_resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"\r\n"
            b"5\r\n"
            b"Hello\r\n"
            b"0\r\n"
            b"\r\n"
        )
        parser.feed(raw_resp)
        resp = parser.parse_next(time.time())
        self.assertIsNotNone(resp)
        self.assertEqual(resp.body, b"Hello")

    def test_pipelined(self):
        parser = ResponseParser()
        raw_resp = (
            b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nHello"
            b"HTTP/1.1 404 Not Found\r\nContent-Length: 4\r\n\r\nOops"
        )
        parser.feed(raw_resp)
        
        resp1 = parser.parse_next(time.time())
        self.assertEqual(resp1.status, 200)
        self.assertEqual(resp1.body, b"Hello")
        
        resp2 = parser.parse_next(time.time())
        self.assertEqual(resp2.status, 404)
        self.assertEqual(resp2.body, b"Oops")

if __name__ == "__main__":
    unittest.main()
