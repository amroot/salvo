import unittest
import threading
import http.server
import socketserver
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

if __name__ == "__main__":
    unittest.main()
