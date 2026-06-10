import concurrent.futures
import threading
from urllib.parse import urlparse
from ..protocols.h11 import Request, ResponseParser
from .transport import SocketWriter

class Pipeline:
    def __init__(self, url, connections=1, gate=False, capture_raw=True):
        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.use_tls = parsed.scheme == "https"
        self.connections = connections
        self.gate = gate
        self.capture_raw = capture_raw
        self.requests = []
        self._gate_event = threading.Event()
        self._barrier = None

    def add(self, request):
        self.requests.append(request)

    def add_many(self, requests):
        self.requests.extend(requests)

    def _fire_connection(self, requests, use_barrier=False):
        if not requests:
            return []
            
        results = []
        try:
            with SocketWriter(self.host, self.port, self.use_tls) as writer:
                writer.connect()
                buffer = b"".join([r.to_bytes(self.host) for r in requests])
                
                if use_barrier:
                    # Wait for all other threads to be connected and buffered
                    self._barrier.wait()
                    # Secondary wait for the user to trigger the gate
                    self._gate_event.wait()
                
                start_time = writer.send_all(buffer)
                
                parser = ResponseParser()
                responses = []
                
                # Set a socket timeout so we don't hang forever
                writer.sock.settimeout(5.0)
                
                while len(responses) < len(requests):
                    try:
                        chunk = writer.sock.recv(16384)
                        if not chunk:
                            break
                        parser.feed(chunk)
                        while True:
                            resp = parser.parse_next(start_time)
                            if resp:
                                if not self.capture_raw:
                                    resp.raw_response = b""
                                responses.append(resp)
                            else:
                                break
                    except (socket.timeout, socket.error):
                        break
                
                # Map requests to responses (pipelining preserves order)
                for i, req in enumerate(requests):
                    res = responses[i] if i < len(responses) else None
                    results.append((req, res))
                    
        except Exception:
            # If connection or handshake fails entirely, return NULL for all requests in this chunk
            for req in requests:
                results.append((req, None))
        return results

    def fire(self):
        if not self.requests:
            return []

        # Split requests across connections
        chunk_size = (len(self.requests) + self.connections - 1) // self.connections
        chunks = [self.requests[i:i + chunk_size] for i in range(0, len(self.requests), chunk_size)]
        actual_connections = len(chunks)

        if self.gate:
            self._barrier = threading.Barrier(actual_connections)
            self._gate_event.clear()
        
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_connections) as executor:
            futures = [executor.submit(self._fire_connection, chunk, self.gate) for chunk in chunks]
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        return all_results

    def results_to_dict(self, results):
        """Helper to convert results to a list of dicts with full metadata."""
        import base64
        output = []
        for req, res in results:
            item = {
                "url": f"{self.base_url}{req.path}",
                "method": req.method,
                "status": res.status if res else "NULL",
                "latency_ms": res.elapsed_ms if res else 0,
                "start_time": res.start_time if res else 0,
                "end_time": res.end_time if res else 0,
                "request_body_b64": base64.b64encode(req.body.encode() if isinstance(req.body, str) else (req.body or b"")).decode(),
                "response_raw_b64": base64.b64encode(res.raw_response if res else b"").decode(),
            }
            output.append(item)
        return output

    def prepare(self):
        # For the new threaded model, 'fire' handles the lifecycle.
        # But we keep these for CLI compatibility if needed.
        pass

    def release(self):
        self._gate_event.set()
