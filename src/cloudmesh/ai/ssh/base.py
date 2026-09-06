# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import subprocess
import socket

from pathlib import Path
from typing import List, Optional, Dict, Union
from dataclasses import dataclass
from fabric import Connection
from cloudmesh.ai.common import logging as ai_log
from .exceptions import SSHError, SSHConnectionError

logger = ai_log.get_logger("ai.ssh.base")

@dataclass
class CommandResult:
    """Structured result of a remote command execution."""
    stdout: str
    stderr: str
    exit_code: int
    command: str
    host: str

class SSHBase:
    """Base class for SSH utilities providing shared execution and path logic."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self._connection_pool: Dict[str, Connection] = {}

    def _execute(self, command: List[str], input_data: Optional[str] = None, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Execute a system command using subprocess.run.

        Args:
            command: The command and arguments as a list.
            input_data: Optional string to pass to stdin.
            capture_output: Whether to capture stdout and stderr.

        Returns:
            The CompletedProcess object.
        """
        if self.debug:
            logger.debug(f"Executing command: {' '.join(command)}")
        
        try:
            return subprocess.run(
                command,
                input=input_data,
                capture_output=capture_output,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            raise SSHError(f"System command failed: {e.stderr}") from e

    def resolve_path(self, path: Union[str, Path]) -> Path:
        """Expand and resolve a path."""
        return Path(path).expanduser().resolve()

    def is_port_open(self, host: str, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open on a given host.

        Args:
            host: the hostname or IP address.
            port: the port number.
            timeout: timeout in seconds.

        Returns:
            bool: True if the port is open, False otherwise.
        """
        try:
            import socket
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def _get_connection(self, host: str, user: Optional[str] = None) -> Connection:
        """Get a Fabric connection from the pool or create a new one, with health check.

        Args:
            host: the hostname or alias.
            user: optional username.

        Returns:
            Connection: a Fabric connection object.
        """
        pool_key = f"{user}@{host}" if user else host
        conn = self._connection_pool.get(pool_key)
        
        if conn:
            try:
                # Heartbeat check: run a lightweight command to verify connection
                conn.run("true", hide=True, timeout=5)
            except Exception:
                if self.debug:
                    logger.debug(f"Connection for {pool_key} is stale, recreating...")
                conn = None

        if conn is None:
            if self.debug:
                logger.debug(f"Creating new connection for {pool_key}")
            try:
                conn = Connection(host=host, user=user)
                self._connection_pool[pool_key] = conn
            except Exception as e:
                raise SSHConnectionError(f"Failed to create connection to {host}: {e}") from e
            
        return conn

    def _run_remote(self, host: str, command: str, user: Optional[str] = None, use_sudo: bool = False, use_pty: bool = False) -> CommandResult:
        """Execute a command on a remote host using Fabric.

        Args:
            host: the hostname or alias.
            command: the command to execute.
            user: optional username.
            use_sudo: whether to use sudo for execution.
            use_pty: whether to allocate a pseudo-terminal.

        Returns:
            CommandResult: structured result of the execution.
        """
        if self.debug:
            logger.debug(f"Executing {'sudo ' if use_sudo else ''}remote command on {host} (pty={use_pty}): {command}")

        try:
            conn = self._get_connection(host, user)
            if use_sudo:
                result = conn.sudo(command, hide=True, pty=use_pty)
            else:
                result = conn.run(command, hide=True, pty=use_pty)
            
            return CommandResult(
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                exit_code=result.exited,
                command=command,
                host=host
            )
        except Exception as e:
            logger.error(f"Fabric execution failed on {host}: {e}")
            raise SSHConnectionError(f"Fabric execution failed on {host}: {e}") from e

    def put(self, local_path: Union[str, Path], remote_path: Union[str, Path], host: str, user: Optional[str] = None) -> None:
        """Upload a local file to a remote host."""
        if self.debug:
            logger.debug(f"Uploading {local_path} to {host}:{remote_path}")
        try:
            conn = self._get_connection(host, user)
            conn.put(str(local_path), str(remote_path))
        except Exception as e:
            logger.error(f"Fabric put failed on {host}: {e}")
            raise SSHConnectionError(f"Fabric put failed on {host}: {e}") from e

    def get(self, remote_path: Union[str, Path], local_path: Union[str, Path], host: str, user: Optional[str] = None) -> None:
        """Download a remote file to a local path."""
        if self.debug:
            logger.debug(f"Downloading {remote_path} from {host} to {local_path}")
        try:
            conn = self._get_connection(host, user)
            conn.get(str(remote_path), str(local_path))
        except Exception as e:
            logger.error(f"Fabric get failed on {host}: {e}")
            raise SSHConnectionError(f"Fabric get failed on {host}: {e}") from e

    def close_connections(self) -> None:
        """Close all active connections in the pool."""
        if self.debug:
            logger.debug("Closing all SSH connections in pool.")
        for conn in self._connection_pool.values():
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self._connection_pool.clear()
