import time

class Request:
    def __init__(self, method, path, headers=None, body=None):
        self.method = method.upper()
        self.path = path
        self.headers = headers or {}
        self.body = body

    def to_bytes(self, host):
        headers = self.headers.copy()
        if "Host" not in headers:
            headers["Host"] = host
        if "Connection" not in headers:
            headers["Connection"] = "keep-alive"
        
        body_bytes = b""
        if self.body:
            if isinstance(self.body, str):
                body_bytes = self.body.encode("utf-8")
            else:
                body_bytes = self.body
            headers["Content-Length"] = str(len(body_bytes))

        req_lines = [f"{self.method} {self.path} HTTP/1.1"]
        for k, v in headers.items():
            req_lines.append(f"{k}: {v}")
        
        header_bytes = "\r\n".join(req_lines).encode("ascii") + b"\r\n\r\n"
        return header_bytes + body_bytes

class RequestTemplate:
    """Pre-compiled request for ultra-fast fuzzing."""
    def __init__(self, method, url_template, headers=None, body_template=None):
        from urllib.parse import urlparse
        parsed = urlparse(url_template)
        self.host = parsed.hostname
        self.path_template = parsed.path + ("?" + parsed.query if parsed.query else "")
        self.headers = headers or {}
        self.body_template = body_template or ""
        
        # Pre-build the constant parts
        self._prepare()

    def _prepare(self):
        # This is a simplification; a true template would split at {FUZZ}
        pass

    def render(self, payload):
        # For now, we still use the standard Request for simplicity, 
        # but the infrastructure is here for the split-byte optimization.
        path = self.path_template.replace("{FUZZ}", payload)
        body = self.body_template.replace("{FUZZ}", payload) if self.body_template else None
        return Request("GET", path, headers=self.headers, body=body)

class Response:
    def __init__(self, status, headers, body, elapsed_ms, raw_response=b"", start_time=0, end_time=0):
        self.status = status
        self.headers = headers
        self.body = body
        self.elapsed_ms = elapsed_ms
        self.raw_response = raw_response
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return f"<Response [{self.status}] {len(self.body)} bytes, {self.elapsed_ms:.2f}ms>"

class ResponseParser:
    def __init__(self):
        self.buffer = bytearray()
        self.mv = memoryview(self.buffer)
        self.bytes_in_buffer = 0

    def feed(self, data):
        self.mv = None # Release the view so we can resize the buffer
        self.buffer.extend(data)
        self.bytes_in_buffer = len(self.buffer)
        self.mv = memoryview(self.buffer)

    def parse_next(self, send_start_time):
        if self.bytes_in_buffer == 0:
            return None

        # Look for end of headers
        headers_end = self.buffer.find(b"\r\n\r\n")
        if headers_end == -1:
            return None

        header_part = self.mv[:headers_end].tobytes()
        lines = header_part.split(b"\r\n")
        
        if not lines[0]:
            # Consume the empty lines
            self.buffer = self.buffer[2:]
            self.bytes_in_buffer = len(self.buffer)
            self.mv = memoryview(self.buffer)
            return self.parse_next(send_start_time)

        try:
            status_line = lines[0].decode("ascii")
            status = int(status_line.split(" ")[1])
        except (IndexError, ValueError):
            return None

        headers = {}
        for line in lines[1:]:
            if b": " in line:
                try:
                    k, v = line.decode("ascii").split(": ", 1)
                    headers[k.lower()] = v
                except UnicodeDecodeError:
                    continue

        body_start = headers_end + 4
        body = b""
        next_pos = body_start

        if headers.get("transfer-encoding", "").lower() == "chunked":
            curr = body_start
            while True:
                line_end = self.buffer.find(b"\r\n", curr)
                if line_end == -1: return None
                
                try:
                    chunk_size = int(self.buffer[curr:line_end].split(b";")[0], 16)
                except ValueError:
                    return None
                
                curr = line_end + 2
                if chunk_size == 0:
                    if self.bytes_in_buffer < curr + 2: return None
                    next_pos = curr + 2
                    break
                
                if self.bytes_in_buffer < curr + chunk_size + 2:
                    return None
                
                body += self.mv[curr:curr + chunk_size].tobytes()
                curr += chunk_size + 2
            
        elif "content-length" in headers:
            try:
                content_length = int(headers["content-length"])
            except ValueError:
                content_length = 0
            
            if self.bytes_in_buffer < body_start + content_length:
                return None
            
            body = self.mv[body_start:body_start + content_length].tobytes()
            next_pos = body_start + content_length
        else:
            body = b""
            next_pos = body_start

        # Capture raw response before consuming buffer
        raw_response = self.buffer[:next_pos]
        end_time = time.time()
        
        # Zero-copy buffer management (re-slicing bytearray is efficient in Python 3)
        self.buffer = self.buffer[next_pos:]
        self.bytes_in_buffer = len(self.buffer)
        self.mv = memoryview(self.buffer)
        
        elapsed_ms = (end_time - send_start_time) * 1000
        return Response(status, headers, body, elapsed_ms, 
                        raw_response=bytes(raw_response), 
                        start_time=send_start_time, 
                        end_time=end_time)
