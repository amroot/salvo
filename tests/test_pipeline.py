import unittest
import threading
import http.server
import socketserver
from unittest.mock import patch
from salvo import Pipeline, Request

class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, format, *args):
        pass

class TestPipelineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start a local HTTP server
        handler = SilentHTTPRequestHandler
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.url = f"http://127.0.0.1:{cls.port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_single_request(self):
        pipe = Pipeline(self.url)
        pipe.add(Request("GET", "/"))
        results = pipe.fire()
        self.assertEqual(len(results), 1)
        req, res = results[0]
        self.assertEqual(res.status, 200)

    def test_multiple_pipelined_requests(self):
        pipe = Pipeline(self.url, connections=1)
        for _ in range(5):
            pipe.add(Request("GET", "/"))
        results = pipe.fire()
        self.assertEqual(len(results), 5)
        for req, res in results:
            self.assertEqual(res.status, 200)

    def test_parallel_connections(self):
        pipe = Pipeline(self.url, connections=3)
        for _ in range(6):
            pipe.add(Request("GET", "/"))
        results = pipe.fire()
        self.assertEqual(len(results), 6)
        for req, res in results:
            self.assertEqual(res.status, 200)

    def test_gate_mode(self):
        pipe = Pipeline(self.url, connections=2, gate=True)
        pipe.add(Request("GET", "/"))
        pipe.add(Request("GET", "/"))
        
        # Start fire in a thread as it will block
        all_res = []
        def run_fire():
            all_res.extend(pipe.fire())
        
        t = threading.Thread(target=run_fire)
        t.start()
        
        # Wait a bit, then release
        import time
        time.sleep(0.5)
        pipe.release()
        t.join()
        
        self.assertEqual(len(all_res), 2)
        for req, res in all_res:
            self.assertEqual(res.status, 200)

    def test_gate_mode_auto_fire(self):
        pipe = Pipeline(self.url, connections=2, gate=True)
        pipe.add(Request("GET", "/"))
        pipe.add(Request("GET", "/"))

        results = pipe.fire(auto_fire=True)

        self.assertEqual(len(results), 2)
        for req, res in results:
            self.assertEqual(res.status, 200)

    def test_gate_mode_auto_fire_returns_when_connection_priming_fails(self):
        pipe = Pipeline(self.url, gate=True)
        pipe.add(Request("GET", "/"))

        with patch("salvo.core.pipeline.SocketWriter") as socket_writer:
            socket_writer.return_value.__enter__.return_value.connect.side_effect = OSError
            results = pipe.fire(auto_fire=True)

        self.assertEqual(results, [(pipe.requests[0], None)])

    def test_gate_mode_rearms_after_release(self):
        pipe = Pipeline(self.url, connections=2, gate=True)
        pipe.add(Request("GET", "/"))
        pipe.add(Request("GET", "/"))

        for _ in range(2):
            results = []
            thread = threading.Thread(target=lambda: results.extend(pipe.fire()))
            thread.start()
            self.assertTrue(pipe._ready_event.wait(timeout=5))
            self.assertTrue(thread.is_alive())
            pipe.release()
            thread.join(timeout=5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(len(results), 2)

if __name__ == "__main__":
    unittest.main()
