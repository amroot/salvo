import argparse
import sys
import base64
import time
from urllib.parse import urlparse

def main():
    from salvo.core.pipeline import Pipeline
    from salvo.protocols.h11 import Request
    
    parser = argparse.ArgumentParser(description="Salvo: High-speed HTTP/1.1 Pipelining")
    parser.add_argument("-u", "--url", help="Target URL (e.g., https://example.com/api/{FUZZ})")
    parser.add_argument("-w", "--wordlist", help="Wordlist for {FUZZ} placeholder")
    parser.add_argument("-c", "--connections", type=int, default=1, help="Number of parallel connections")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of requests to send (per payload if wordlist used)")
    parser.add_argument("-m", "--method", default="GET", help="HTTP method")
    parser.add_argument("-b", "--body", help="Request body")
    parser.add_argument("-H", "--header", action="append", help="Custom headers (e.g., 'Authorization: Bearer token')")
    parser.add_argument("-f", "--file", help="Load raw request from file (Burp style)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show all responses in detail")
    parser.add_argument("--no-log", action="store_true", help="Skip saving the detailed TSV output file")
    parser.add_argument("--race", action="store_true", help="Enable gate mode for race condition testing")
    
    args = parser.parse_args()

    if not args.url and not args.file:
        parser.error("either --url or --file is required")

    custom_headers = {}
    if args.header:
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                custom_headers[k.strip()] = v.strip()

    payloads = [""]
    if args.wordlist:
        with open(args.wordlist, "r") as f:
            payloads = [line.strip() for line in f]

    target_url = args.url
    method = args.method
    body = args.body
    headers = custom_headers

    if args.file:
        with open(args.file, "r") as f:
            raw_req = f.read()
        
        # Simple Burp-style parser
        lines = raw_req.splitlines()
        if lines:
            parts = lines[0].split()
            if len(parts) >= 2:
                method = parts[0]
                path = parts[1]
                
                # Parse headers
                headers = {}
                idx = 1
                while idx < len(lines) and lines[idx].strip():
                    if ":" in lines[idx]:
                        k, v = lines[idx].split(":", 1)
                        headers[k.strip()] = v.strip()
                    idx += 1
                
                # Update headers with CLI overrides
                if args.header:
                    headers.update(custom_headers)

                # Parse body
                if idx < len(lines):
                    body = "\n".join(lines[idx+1:])
                
                if not target_url:
                    host = headers.get("Host", "localhost")
                    scheme = "https" if "443" in host else "http" # Heuristic
                    target_url = f"{scheme}://{host}{path}"

    pipe = Pipeline(target_url.replace("{FUZZ}", ""), connections=args.connections, gate=args.race)
    
    request_to_url = {} # Map request object to full URL for logging
    
    for payload in payloads:
        parsed_base = urlparse(target_url)
        actual_path = parsed_base.path.replace("{FUZZ}", payload)
        if parsed_base.query:
            actual_path += "?" + parsed_base.query.replace("{FUZZ}", payload)
        
        full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{actual_path}"
        actual_body = body.replace("{FUZZ}", payload) if body else None
        
        for _ in range(args.count):
            req = Request(method, actual_path, headers=headers.copy(), body=actual_body)
            pipe.add(req)
            request_to_url[id(req)] = full_url

    print(f"[*] Firing {len(pipe.requests)} requests at {target_url}...")
    
    results = []
    if args.race:
        import threading
        def run_fire():
            results.extend(pipe.fire())
        
        t = threading.Thread(target=run_fire)
        t.start()
        
        print("[*] Waiting for all connections to be ready...")
        input("[!] All connections primed. Press Enter to release the salvo...")
        pipe.release()
        t.join()
    else:
        results = pipe.fire()

    # Process results
    summary = {}
    
    log_filename = f"salvo_log_{int(time.time())}.tsv"
    log_file = None
    if not args.no_log:
        log_file = open(log_filename, "w", encoding="utf-8")
        log_file.write("URL\tStatus\tReqBodyB64\tFullResB64\tElapsedMS\tReqTS\tResTS\n")

    for req, res in results:
        url = request_to_url.get(id(req), "Unknown")
        status = res.status if res else "NULL"
        summary[status] = summary.get(status, 0) + 1
        
        if args.verbose:
            print(f"[{status}] {url} - {res.elapsed_ms if res else 0:.2f}ms")

        if log_file:
            req_body_b64 = base64.b64encode(req.body.encode() if isinstance(req.body, str) else (req.body or b"")).decode()
            res_raw_b64 = base64.b64encode(res.raw_response if res else b"").decode()
            log_file.write(f"{url}\t{status}\t{req_body_b64}\t{res_raw_b64}\t{res.elapsed_ms if res else 0:.2f}\t{res.start_time if res else 0}\t{res.end_time if res else 0}\n")

    if log_file:
        log_file.close()
        print(f"[*] Detailed log saved to: {log_filename}")

    print("\n[+] Response Summary:")
    for status, count in sorted(summary.items(), key=lambda x: str(x[0])):
        print(f"  {status}: {count}")

if __name__ == "__main__":
    import pathlib
    # Add parent directory to path so 'import salvo' works when running directly
    sys.path.append(str(pathlib.Path(__file__).parent.parent))
    main()
