# Salvo Technical Documentation

Salvo is a high-performance Python library and CLI tool designed for HTTP/1.1 pipelining and concurrent request execution. It is optimized for speed, precision, and low-level protocol control.

## 1. Architecture

### System Purpose
The primary goal of Salvo is to deliver a large volume of HTTP requests with minimal overhead. It achieves this by bypassing high-level libraries like `requests` and interacting directly with raw TCP sockets.

### Components
- **Transport (`SocketWriter`)**: Manages raw TCP and TLS socket connections. Implements `TCP_NODELAY` to ensure packets are sent immediately.
- **Protocol (`ResponseParser`)**: A non-blocking, zero-copy byte parser for HTTP/1.1. It handles `Content-Length` and `Chunked` transfer encodings.
- **Orchestrator (`Pipeline`)**: Manages a thread pool of parallel connections. It splits the total request load across connections and aggregates results.
- **Interface (`CLI`)**: A command-line wrapper providing fuzzing, raw request loading (Burp-style), and detailed logging.

### Data Flow
1. **Compilation**: The `Pipeline` compiles multiple `Request` objects into a single byte buffer per connection.
2. **Synchronization**: If `gate` (Precision Mode) is enabled, all threads synchronize at a barrier.
3. **Dispatch**: Buffers are written to sockets simultaneously.
4. **Parsing**: Incoming bytes are fed into the `ResponseParser` until all expected responses are reconstructed.
5. **Aggregation**: `Pipeline` returns a list of `(Request, Response)` pairs.

### Constraints & Tradeoffs
- **Protocol**: Currently strictly HTTP/1.1.
- **Memory**: Buffers raw responses in memory for analysis; users can disable this with `capture_raw=False` in the library.

---

## 2. API Documentation

### `salvo.Pipeline`
The main entry point for library users.

#### `__init__(url, connections=1, gate=False, capture_raw=True)`
- `url` (str): Target base URL.
- `connections` (int): Number of parallel TCP connections.
- `gate` (bool): Synchronize connection firing (Precision Mode).
- `capture_raw` (bool): If True, stores full response bytes in the result.

#### `add(request)` / `add_many(requests)`
- `request`: A `salvo.protocols.h11.Request` object.

#### `fire()`
- **Returns**: `List[Tuple[Request, Response]]`.

#### `results_to_dict(results)`
- Converts results into a JSON-serializable list of dictionaries including base64 encoded data.

### `salvo.protocols.h11.Request`
#### `__init__(method, path, headers=None, body=None)`
- `headers` (dict): Optional custom HTTP headers.
- `body` (str/bytes): Optional request body.

---

## 3. Onboarding & Setup

### Prerequisites
- **Python 3.11+**
- **Git Bash** (Recommended for Windows users)
- **Oracle OCI CLI** (Required for infrastructure management)

### Environment Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/amroot/salvo.git

   cd salvo
   ```
2. Install in editable mode:
   ```bash
   pip install -e .
   ```

### Running Tests
Run the full suite using the standard unittest discover:
```bash
python -m unittest discover tests
```

---

## 4. Reference: CLI Flags

| Flag | Name | Description |
| :--- | :--- | :--- |
| `-u` | `--url` | Target URL (supports `{FUZZ}` placeholder). |
| `-f` | `--file` | Path to raw HTTP request file (Burp style). |
| `-c` | `--connections`| Number of parallel TCP connections. |
| `-n` | `--count` | Total requests per connection/payload. |
| `-H` | `--header` | Custom HTTP header (can be used multiple times). |
| `-v` | `--verbose` | Output every response code and latency. |
| `--race` | `N/A` | Enable Precision Mode (synchronized firing). |
| `--no-log` | `N/A` | Skip TSV file generation. |
