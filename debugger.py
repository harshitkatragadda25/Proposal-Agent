#!/usr/bin/env python3
"""
debug_chatbot_perf.py

Measures latency and error rates of your chatbot API:
  POST http://<host>:<port>/api/chat/

Usage:
  python debug_chatbot_perf.py --host 127.0.0.1 --port 8000 --iterations 20 --timeout 30
"""

import time
import argparse
import requests
import statistics
import sys

def test_endpoint(host, port, session_id, query, timeout):
    url = f"http://{host}:{port}/api/chat/"
    payload = {"query": query, "session_id": session_id}
    start = time.monotonic()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.monotonic() - start
        r.raise_for_status()
        data = r.json()
        return elapsed, r.status_code, data, None
    except Exception as e:
        elapsed = time.monotonic() - start
        return elapsed, getattr(e, 'response', None) and e.response.status_code or None, None, str(e)

def main():
    parser = argparse.ArgumentParser(description="Benchmark your chatbot API")
    parser.add_argument("--host",       default="127.0.0.1", help="Chatbot server host")
    parser.add_argument("--port",       default="8000",      help="Chatbot server port")
    parser.add_argument("--iterations", type=int, default=5,  help="Number of test calls")
    parser.add_argument("--timeout",    type=int, default=15, help="Per-call timeout (seconds)")
    parser.add_argument("--query",      default="Hello!",    help="Test query to send")
    args = parser.parse_args()

    session_id = str(int(time.time() * 1000))  # unique per run
    latencies = []
    errors = []

    print(f"→ Testing {args.iterations} calls to http://{args.host}:{args.port}/api/chat/")
    print(f"  Timeout per call: {args.timeout}s\n")

    for i in range(1, args.iterations + 1):
        print(f"[{i}/{args.iterations}] Sending query...", end=" ", flush=True)
        elapsed, status, data, err = test_endpoint(
            args.host, args.port, session_id, args.query, args.timeout
        )
        latencies.append(elapsed)

        if err:
            errors.append((i, err))
            print(f"ERROR ({err}) after {elapsed:.2f}s")
        else:
            wait = data.get("wait_for_input", None)
            node = data.get("node", None)
            print(f"OK [{status}] in {elapsed:.2f}s | wait_for_input={wait} | node={node}")

    print("\n--- Summary ---")
    print(f"Total calls:    {args.iterations}")
    print(f"Successful:     {args.iterations - len(errors)}")
    print(f"Errors:         {len(errors)}")
    if errors:
        print("Error details:")
        for idx, msg in errors:
            print(f"  • Call {idx}: {msg}")

    print("\nLatency (s):")
    print(f"  Min   = {min(latencies):.2f}")
    print(f"  Max   = {max(latencies):.2f}")
    print(f"  Avg   = {statistics.mean(latencies):.2f}")
    print(f"  Median= {statistics.median(latencies):.2f}")

    # Exit non-zero if any errors
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
