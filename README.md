# Salvo 🚀
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Salvo** is a high-speed Python HTTP pipelining engine built for precision attack-surface testing and extreme throughput. By leveraging raw sockets and byte-level request assembly, it bypasses the overhead of traditional libraries to deliver tightly synchronized bursts of traffic -- ideal for race-condition discovery, high-volume load testing, and high-frequency API validation.

## 📖 Table of Contents
- [Features](#features)
- [Why Salvo?](#why-salvo)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Pipelining](#pipelining)
  - [The Pipeline Object](#the-pipeline-object)
- [CLI Usage](#cli-usage)
- [Configuration](#configuration)
- [Infrastructure & Testing](#infrastructure--testing)
- [Contributing](#contributing)
- [License](#license)

---

## 🏷️ What's in a Name?
In military terminology, a **Salvo** is a simultaneous discharge of artillery or firearms at a single target. 

This project was named **Salvo** because it specializes in the "synchronized strike." While other tools send requests as fast as possible in a sequence, Salvo allows you to prime multiple connections, wait for them all to be ready, and then "pull the trigger" to release them at the exact same millisecond.

---

## ✨ Features
- **HTTP/1.1 Pipelining:** Send multiple requests over a single TCP connection without waiting for individual responses.
- **Zero Dependencies:** Built entirely on Python's standard library (`socket`, `ssl`, `threading`).
- **Raw Socket Control:** Direct interaction with TCP sockets for minimal overhead and `TCP_NODELAY` optimization.
- **Threaded Concurrency:** Distribute pipelined salvos across multiple connections for parallel execution.
- **Precise Timing:** High-resolution latency tracking for every request in the salvo.
- **Modular Design:** Clean separation of transport and protocol layers, ready for future HTTP/2 and HTTP/3 support.

## ❓ Why Salvo?
Most Python HTTP libraries (like `requests` or `httpx`) focus on developer ergonomics and compliance, which introduces overhead. Salvo is built for **speed**. It allows you to:
1.  **Saturate Connections:** Push the limits of HTTP/1.1 pipelining.
2.  **Test Race Conditions:** Deliver multiple requests in a single network packet to trigger server-side concurrency issues.
3.  **High-Performance Fuzzing:** Rapidly iterate through payloads with minimal protocol overhead.

---

## 🚀 Installation

Salvo requires **Python 3.11+**.

### From Source
```bash
git clone https://github.com/amroot/salvo.git
cd salvo
pip install -e .
```

---

## 💻 Quick Start

### Using as a Library
```python
from salvo import Pipeline, Request

# 1. Initialize a pipeline with 10 concurrent connections
url = "http://localhost:8000/"
pipe = Pipeline(url, connections=10)

# 2. Add requests to the salvo
for i in range(100):
    pipe.add(Request("GET", f"/?id={i}"))

# 3. Fire the salvo!
results = pipe.fire()

# 4. Process results
print(f"Received {len(results)} responses.")
for res in results[:3]:
    print(f"Status: {res.status}, Latency: {res.elapsed_ms:.2f}ms")
```

### Using the CLI
Salvo comes with a built-in CLI for rapid testing:
```bash
# Basic usage (outputs a summary of response codes)
salvo --url http://localhost:8000/ --count 100 --connections 10

# Verbose usage (lists every request and response)
salvo --url http://localhost:8000/ --verbose

# Skip detailed TSV logging
salvo --url http://localhost:8000/ --no-log

# Load a raw request from a file (Burp Suite style)
salvo --file request.txt --connections 5 --count 10
```

---

## 🧠 Core Concepts

### Detailed Logging & Analysis
By default, Salvo generates a timestamped TSV file (`salvo_log_*.tsv`) containing:
- Target URL
- HTTP Status Code (including `NULL` for failed connections)
- Request Body (Base64 encoded)
- Full Raw Response (Base64 encoded)
- Latency (ms)
- Request/Response Timestamps

This file is optimized for analysis in Excel, Pandas, or custom security tools. Use `--no-log` to disable this behavior.

---

## 🛠️ Configuration

| Argument | Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `url` | `-u` | `str` | N/A | Target endpoint (HTTP/HTTPS). Supports `{FUZZ}` placeholder. |
| `file` | `-f` | `str` | N/A | Path to a raw HTTP request file (Burp style). |
| `connections`| `-c` | `int` | `1` | Number of parallel TCP connections. |
| `count` | `-n` | `int` | `1` | Total requests to send (per connection/payload). |
| `header` | `-H` | `str` | N/A | Custom HTTP headers (can be used multiple times). |
| `verbose` | `-v` | `bool` | `False` | List all responses with status codes and latency. |
| `no-log` | `N/A`| `bool` | `False` | Disable generation of the detailed TSV log file. |
| `wordlist` | `-w` | `str` | N/A | Path to a file for `{FUZZ}` replacement. |
| `race` | `N/A`| `bool`| `False` | Enable Gate/Barrier mode for synchronized firing. |

## 🗺️ Roadmap
Salvo is actively evolving to support modern web protocols while maintaining its performance-first philosophy.
- [x] **HTTP/1.1 Pipelining Engine:** Core engine with raw socket control.
- [x] **Burp-style Request Parsing:** Load and replay raw requests.
- [ ] **HTTP/2 Module:** Multi-stream support over single TCP connections.
- [ ] **HTTP/3 (QUIC) Module:** UDP-based ultra-fast delivery.
- [ ] **Automatic Protocol Negotiation (ALPN):** Seamlessly upgrade/downgrade based on target capability.

## Contributing
Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) (coming soon) for details on our code of conduct and the process for submitting pull requests.

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---
*Built for speed, accuracy, and concurrent power.*
