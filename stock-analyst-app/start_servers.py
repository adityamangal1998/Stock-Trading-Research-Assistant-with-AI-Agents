#!/usr/bin/env python3
"""
Start all MCP servers for the Stock Analyst App
"""

import subprocess
import sys
import time
import signal
import os
from multiprocessing import Process

def start_server(server_file, port):
    """Start a single MCP server."""
    try:
        print(f"Starting {server_file} on port {port}...")
        subprocess.run([sys.executable, server_file, str(port)], cwd="mcp_servers")
    except KeyboardInterrupt:
        print(f"\nStopping {server_file}...")
    except Exception as e:
        print(f"Error starting {server_file}: {e}")

def main():
    """Start all MCP servers in parallel."""
    servers = [
        ("finance_server.py", 8001),
        ("rss_server.py", 8002),
        ("db_server.py", 8003)
    ]
    
    processes = []
    
    try:
        # Start each server in a separate process
        for server_file, port in servers:
            process = Process(target=start_server, args=(server_file, port))
            process.start()
            processes.append(process)
            time.sleep(1)  # Small delay between server starts
        
        print("\nAll MCP servers started successfully!")
        print("Press Ctrl+C to stop all servers...")
        
        # Wait for all processes
        for process in processes:
            process.join()
            
    except KeyboardInterrupt:
        print("\nShutting down all MCP servers...")
        
        # Terminate all processes
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                
                if process.is_alive():
                    process.kill()
        
        print("All servers stopped.")

if __name__ == "__main__":
    main()
