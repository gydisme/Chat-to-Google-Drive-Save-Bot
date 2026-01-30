import sys
import subprocess
import os
import re

def kill_port(port):
    """
    Finds the process ID (PID) occupying the specified port and kills it.
    Works on Windows.
    """
    print(f"Looking for process running on port {port}...")

    try:
        # Run netstat to find the PID
        # -a: Displays all active connections and the TCP and UDP ports on which the computer is listening.
        # -n: Displays active TCP connections, however, addresses and port numbers are expressed numerically and no attempt is made to determine names.
        # -o: Displays active TCP connections and includes the process ID (PID) for each connection.
        cmd = 'netstat -ano'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        output = result.stdout
        lines = output.splitlines()
        
        target_pid = None
        
        # Regex to match the line:  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       1234
        # We look for the specific port
        for line in lines:
            if f":{port}" in line:
                parts = line.split()
                # Default format: Proto Local Address Foreign Address State PID
                # Example: TCP 0.0.0.0:8080 0.0.0.0:0 LISTENING 15324
                # We want the last element which is PID
                if parts:
                    pid = parts[-1]
                    # Verify it's a number
                    if pid.isdigit():
                        target_pid = pid
                        break
        
        if target_pid:
            print(f"Found process with PID: {target_pid}")
            # Kill the process
            # /F: Forcefully terminate the process.
            # /PID: Specifies the PID of the process to be terminated.
            kill_cmd = f"taskkill /F /PID {target_pid}"
            kill_result = subprocess.run(kill_cmd, capture_output=True, text=True, shell=True)
            
            if kill_result.returncode == 0:
                print(f"Successfully killed process {target_pid} on port {port}.")
            else:
                print(f"Failed to kill process {target_pid}. Error: {kill_result.stderr}")
        else:
            print(f"No process found running on port {port}.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/kill_port.py <port>")
        sys.exit(1)
    
    port_arg = sys.argv[1]
    if not port_arg.isdigit():
        print("Error: Port must be a number.")
        sys.exit(1)
        
    kill_port(int(port_arg))
