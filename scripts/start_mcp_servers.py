"""
Starts all 5 MCP tool servers as background processes.
Run this once before running any agent scenarios.
Usage: python scripts/start_mcp_servers.py
"""

import subprocess
import sys
import time
import requests
import os

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

SERVERS = [
    {"name": "account_mcp",     "port": 8001, "module": "mcp_servers.account_mcp.main:app"},
    {"name": "card_mcp",        "port": 8002, "module": "mcp_servers.card_mcp.main:app"},
    {"name": "transaction_mcp", "port": 8003, "module": "mcp_servers.transaction_mcp.main:app"},
    {"name": "crm_mcp",         "port": 8004, "module": "mcp_servers.crm_mcp.main:app"},
    {"name": "compliance_mcp",  "port": 8005, "module": "mcp_servers.compliance_mcp.main:app"},
]

processes = []

def start_servers():
    print("Starting MCP tool servers...\n")
    for server in SERVERS:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", server["module"],
             "--port", str(server["port"]), "--log-level", "error"],
            cwd=BASE_DIR
        )
        processes.append(proc)
        print(f"  [started] {server['name']} on port {server['port']} (PID {proc.pid})")

    # Wait for all servers to be ready
    print("\nWaiting for servers to be ready...")
    time.sleep(3)

    all_ok = True
    for server in SERVERS:
        try:
            resp = requests.get(f"http://localhost:{server['port']}/health", timeout=3)
            status = "OK" if resp.status_code == 200 else "ERROR"
        except Exception:
            status = "UNREACHABLE"
            all_ok = False
        print(f"  [{status}] {server['name']} — http://localhost:{server['port']}")

    if all_ok:
        print("\nAll MCP servers are running. Press Ctrl+C to stop.\n")
    else:
        print("\nWARNING: Some servers failed to start. Check the output above.\n")

    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down MCP servers...")
        for proc in processes:
            proc.terminate()
        print("All servers stopped.")

if __name__ == "__main__":
    start_servers()
