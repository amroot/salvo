import unittest
import sys
import io
from unittest.mock import patch
import threading
import http.server
import socketserver
import os
from salvo.cli import main

class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, format, *args):
        pass

class TestCLIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), SilentHTTPRequestHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.url = f"http://127.0.0.1:{cls.port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_cli_basic(self):
        test_args = ["salvo", "-u", self.url, "-n", "2", "--no-log"]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                main()
                output = fake_out.getvalue()
                self.assertIn("Firing 2 requests", output)
                self.assertIn("200: 2", output)

    def test_cli_header(self):
        test_args = ["salvo", "-u", self.url, "-H", "X-Custom: CLI-Test", "--no-log"]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                main()
                output = fake_out.getvalue()
                self.assertIn("200: 1", output)

    def test_cli_file(self):
        # Create a temporary request file
        req_file = "test_req.txt"
        with open(req_file, "w") as f:
            f.write(f"GET / HTTP/1.1\nHost: 127.0.0.1:{self.port}\n\n")
        
        try:
            test_args = ["salvo", "-f", req_file, "-n", "1", "--no-log"]
            with patch.object(sys, 'argv', test_args):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    main()
                    output = fake_out.getvalue()
                    self.assertIn("200: 1", output)
        finally:
            if os.path.exists(req_file):
                os.remove(req_file)

    def test_cli_wordlist(self):
        # Create a temporary wordlist
        wl_file = "test_wordlist.txt"
        with open(wl_file, "w") as f:
            f.write("user1\nuser2\n")
        
        try:
            # We use a URL with {FUZZ}
            test_args = ["salvo", "-u", f"{self.url}?q={{FUZZ}}", "-w", wl_file, "--no-log"]
            with patch.object(sys, 'argv', test_args):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    main()
                    output = fake_out.getvalue()
                    self.assertIn("Firing 2 requests", output)
                    self.assertIn("200: 2", output)
        finally:
            if os.path.exists(wl_file):
                os.remove(wl_file)

    def test_cli_race_auto_fire(self):
        test_args = ["salvo", "-u", self.url, "-n", "1", "--race", "--auto-fire", "--no-log"]
        with patch.object(sys, 'argv', test_args):
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                main()
                output = fake_out.getvalue()
                self.assertIn("Firing 1 requests", output)
                self.assertIn("200: 1", output)
                self.assertIn("Auto-fire enabled, releasing the salvo immediately", output)

    def test_cli_race_auto_fire_no_input(self):
        class DummyPipeline:
            def __init__(self, target_url, connections, gate):
                self.requests = []
            def add(self, req):
                self.requests.append(req)
            def fire(self):
                return [(req, type("R", (), {"status": 200, "elapsed_ms": 1.0, "raw_response": b"OK", "start_time": 0, "end_time": 1})) for req in self.requests]
            def release(self):
                self.released = True

        class DummyRequest:
            def __init__(self, method, path, headers, body):
                self.body = body

        test_args = ["salvo", "-u", self.url, "-n", "1", "--race", "--auto-fire", "--no-log"]
        with patch('salvo.core.pipeline.Pipeline', DummyPipeline), patch('salvo.protocols.h11.Request', DummyRequest):
            with patch.object(sys, 'argv', test_args):
                with patch('sys.stdout', new=io.StringIO()) as fake_out:
                    main()
                    output = fake_out.getvalue()
                    self.assertIn("Firing 1 requests", output)
                    self.assertIn("Auto-fire enabled, releasing the salvo immediately", output)

if __name__ == "__main__":
    unittest.main()
