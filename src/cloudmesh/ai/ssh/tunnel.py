# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#

import subprocess
import os
import signal
import time
from typing import List, Optional, Union
from pathlib import Path
from cloudmesh.ai.common.io import console
from .base import SSHBase
from .exceptions import SSHTunnelError
from .ssh_config import SSHConfig

class Tunnel(SSHBase):
    """Manages an SSH tunnel for port forwarding."""

    def __init__(
        self, 
        local_port: int, 
        remote_host: str, 
        remote_port: int, 
        ssh_host: str, 
        ssh_user: Optional[str] = None, 
        identity_file: Optional[Union[str, Path]] = None, 
        extra_args: Optional[List[str]] = None,
        debug: bool = False
    ):
        super().__init__(debug=debug)
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.identity_file = identity_file
        self.extra_args = extra_args or []
        self.process = None

    def _get_resolved_ssh_host(self) -> str:
        """Resolve ssh_host using SSHConfig if it's an alias."""
        cfg = SSHConfig()
        # If ssh_user is not provided, try to get it from config
        user = self.ssh_user or cfg.username(self.ssh_host)
        hostname = cfg.hostname(self.ssh_host)
        
        if user:
            return f"{user}@{hostname}"
        return hostname

    def start(self, timeout: int = 10) -> bool:
        """Starts the SSH tunnel in the background.

        Args:
            timeout: seconds to wait for the port to open.
        """
        if self.process and self.process.poll() is None:
            console.warn(f"Tunnel for port {self.local_port} is already running.")
            return True

        try:
            ssh_host = self._get_resolved_ssh_host()
            
            # -L local_port:remote_host:remote_port ssh_host -N
            # -N tells SSH not to execute a remote command.
            # ExitOnForwardFailure ensures the process exits if port forwarding fails.
            cmd = [
                "ssh",
                "-o", "ExitOnForwardFailure=yes",
                "-L", f"{self.local_port}:{self.remote_host}:{self.remote_port}",
            ]

            if self.identity_file:
                cmd.extend(["-i", self.identity_file])

            cmd.extend(self.extra_args)
            cmd.append(ssh_host)
            cmd.append("-N")

            if self.debug:
                console.debug(f"Executing: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE, 
                text=True,
                preexec_fn=os.setpgrp
            )

            # Wait for the port to become active
            if self._wait_for_port(timeout):
                console.ok(f"SSH tunnel established: localhost:{self.local_port} -> {self.remote_host}:{self.remote_port} via {self.ssh_host}")
                return True
            else:
                # If it didn't open, check for errors in stderr
                stderr = self.process.stderr.read() if self.process.stderr else "No stderr available"
                console.error(f"SSH tunnel failed to open port {self.local_port} within {timeout}s.")
                if stderr:
                    console.error(f"SSH Error: {stderr.strip()}")
                self.stop()
                return False

        except Exception as e:
            raise SSHTunnelError(f"Failed to start SSH tunnel: {e}")
            self.stop()
            return False

    def _wait_for_port(self, timeout: int) -> bool:
        """Polls the local port until it's open or timeout is reached."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_port_open("localhost", self.local_port):
                return True
            if self.process and self.process.poll() is not None:
                return False
            time.sleep(0.5)
        return False

    def stop(self):
        """Stops the SSH tunnel process."""
        if not self.process or self.process.poll() is not None:
            return False

        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            console.ok(f"SSH tunnel on port {self.local_port} stopped.")
            return True
        except Exception as e:
            raise SSHTunnelError(f"Failed to stop SSH tunnel: {e}")
            return False

    def force_stop(self) -> bool:
        """Forcefully terminates any process bound to the local port using lsof.
        
        This is useful for cleaning up zombie tunnels that were not started by this 
        specific Tunnel instance.
        """
        if not self.is_port_open("localhost", self.local_port):
            console.debug(f"No active tunnel found on port {self.local_port}.")
            return False

        try:
            # -t: terse output (only PID), -i: port
            result = subprocess.run(
                ["lsof", "-t", f"-i:{self.local_port}"],
                capture_output=True,
                text=True,
                check=True
            )
            pids = result.stdout.strip().split()
            if pids:
                console.warn(f"Forcefully terminating process(es) {', '.join(pids)} on port {self.local_port}...")
                subprocess.run(["kill", "-9"] + pids, check=True)
                self.process = None
                console.ok(f"Successfully terminated tunnel process(es) on port {self.local_port}.")
                return True
        except subprocess.CalledProcessError:
            # lsof returns non-zero if no process is found
            console.debug(f"No process found on port {self.local_port} by lsof.")
        except Exception as e:
            raise SSHTunnelError(f"Error during force_stop on port {self.local_port}: {e}")
        
        return False


    def is_active(self) -> bool:
        """Checks if the tunnel process is still running and port is open."""
        return self.process is not None and self.process.poll() is None and self.is_port_open("localhost", self.local_port)

    def __enter__(self):
        """Context manager enter."""
        if self.start():
            return self
        raise RuntimeError(f"Could not start SSH tunnel on port {self.local_port}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
