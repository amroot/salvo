import socket
import ssl
import time

class SocketWriter:
    def __init__(self, host, port, use_tls=False, timeout=10.0):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.timeout = timeout
        self.sock = None

    def connect(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            if self.use_tls:
                context = ssl.create_default_context()
                self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
        except (socket.error, ssl.SSLError) as e:
            if self.sock:
                self.sock.close()
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port} - {e}")

    def send_all(self, buffer):
        if not self.sock:
            self.connect()
        
        start_time = time.time()
        try:
            self.sock.sendall(buffer)
        except socket.error as e:
            raise ConnectionError(f"Failed to send data to {self.host} - {e}")
        return start_time

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            self.sock.close()
            self.sock = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
