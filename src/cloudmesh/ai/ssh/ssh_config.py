# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import json
import os
import yaml
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Dict, List, Optional, Union

from cloudmesh.ai.common import logging as ai_log
from .base import SSHBase, CommandResult
from .exceptions import SSHConfigError
from sshconf import SshConfig as SshConf

logger = ai_log.get_logger("ai.ssh.ssh_config")

class SSHConfig(SSHBase):
    """Managing the SSH config file (usually ~/.ssh/config)."""

    def __init__(self, filename: Optional[Union[str, Path]] = None, debug: bool = False):
        super().__init__(debug=debug)
        if filename is not None:
            self.filename = self.resolve_path(str(filename))
        else:
            self.filename = self.resolve_path("~/.ssh/config")
        
        self.conf: Optional[SshConf] = None
        self._resolved_cache: Dict[str, Dict[str, str]] = {}
        self.load()
    def get_content(self) -> str:
        """Return the raw content of the SSH config file."""
        try:
            with open(self.filename, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Could not read config file {self.filename}: {e}")
            return ""

        self.load()

    def names(self) -> List[str]:
        """The names defined in the SSH config.

        Returns:
            List[str]: the host names.
        """
        return self.list()

    def load(self):
        """Parse the SSH config file using sshconf."""
        try:
            self.conf = SshConf(str(self.filename))
        except Exception as e:
            raise SSHConfigError(f"Could not load ssh config file {self.filename}: {e}")
            self.conf = None

    def _get_resolved_config(self, host: str) -> Dict[str, str]:
        """Use 'ssh -G' to get the fully resolved configuration for a host, with caching."""
        if host in self._resolved_cache:
            return self._resolved_cache[host]

        try:
            # -G: print resolved configuration for this host
            # -F: use specific config file
            result = subprocess.run(
                ["ssh", "-F", str(self.filename), "-G", host],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                config = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # ssh -G output is typically 'option value'
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        k, v = parts
                        config[k.strip()] = v.strip()
                self._resolved_cache[host] = config
                return config
        except Exception as e:
            logger.error(f"Error resolving config for host {host} via ssh -G: {e}")
        
        return {}


    def _get_explicit_keys(self, host: str) -> List[str]:
        """Identify all keys explicitly defined in the config file for a host.
        
        This includes keys defined in the specific host block and the 'Host *' block.
        """
        explicit_keys = set()
        try:
            with open(self.filename, "r") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Could not read config file for key extraction: {e}")
            return []

        current_hosts = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.lower().startswith("host "):
                # Start of a new block
                current_hosts = line[5:].strip().split()
            elif current_hosts:
                # Inside a host block
                # Check if this block applies to the target host or is a wildcard
                if any(h.lower() == host.lower() or h == "*" for h in current_hosts):
                    # Extract the key from 'Key Value'
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        explicit_keys.add(parts[0])
        
        return list(explicit_keys)

    def get_options(self, host: str) -> str:
        """Get configuration options for a host that are explicitly defined in the config file.

        Args:
            host: the host name.

        Returns:
            str: comma-separated string of options.
        """
        explicit_keys = self._get_explicit_keys(host)
        if not explicit_keys:
            return ""

        # Get fully resolved configuration from ssh -G
        resolved_config = self._get_resolved_config(host)

        # Only keep options that were explicit in the config, and filter out HostName/User
        filtered = {}
        for k in explicit_keys:
            k_lower = k.lower()
            if k_lower not in ["hostname", "user"]:
                # Prefer the resolved value from ssh -G
                # ssh -G output keys are lowercase
                if k_lower in resolved_config:
                    filtered[k] = resolved_config[k_lower]
                else:
                    # Fallback to raw value from config if ssh -G didn't return it
                    # (this is rare for valid options)
                    try:
                        # We can't easily get the raw value without a real parser, 
                        # so we'll just use the key name or skip it.
                        # But for now, let's just use the resolved config.
                        pass
                    except Exception:
                        pass

        if not filtered:
            return ""
        return ", ".join([f"{k}={v}" for k, v in filtered.items()])

    def list(self) -> List[str]:
        """List the hosts defined in the config file.

        Returns:
            List[str]: list of host names.
        """
        hosts = []
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    trimmed = line.strip()
                    if trimmed.lower().startswith("host "):
                        # Extract the host part, handling multiple hosts on one line
                        # e.g., "Host host1 host2"
                        parts = trimmed.split()
                        hosts.extend(parts[1:])
        except Exception as e:
            logger.error(f"Error reading hosts from {self.filename}: {e}")
        
        return hosts

    def __str__(self) -> str:
        """The string representation of the config as JSON."""
        self._ensure_loaded()
        if not self.conf:
            return "{}"
        
        # Convert sshconf to a dictionary for JSON representation
        hosts_dict = {}
        try:
            for host in self.conf.hosts():
                hosts_dict[host] = self.conf.get_all(host)
        except Exception as e:
            logger.error(f"Error parsing config for JSON representation: {e}")
        
        return json.dumps(hosts_dict, indent=4)

    def login(self, name: str):
        """Login to the host defined in .ssh/config by name.

        Args:
            name: the name of the host as defined in the config file.
        """
        logger.info(f"Logging into host: {name}")
        try:
            self._execute(["ssh", name], capture_output=False)
        except Exception as e:
            logger.error(f"Failed to login to {name}: {e}")

    def execute(self, name: str, command: str, use_pty: bool = False) -> Union[CommandResult, str]:
        """Execute the command on the named host.

        Args:
            name: the name of the host in config.
            command: the command to be executed.
            use_pty: whether to allocate a pseudo-terminal.

        Returns:
            Union[CommandResult, str]: CommandResult for remote, stdout for local.
        """
        if name == "localhost":
            # Execute locally
            result = self._execute(["sh", "-c", command])
            return result.stdout if result.stdout else result.stderr
        
        # Execute via Fabric
        user = self.username(name)
        return self._run_remote(name, command, user=user, use_pty=use_pty)

    def sudo_execute(self, name: str, command: str, use_pty: bool = False) -> CommandResult:
        """Execute the command on the named host with sudo.

        Args:
            name: the name of the host in config.
            command: the command to be executed.
            use_pty: whether to allocate a pseudo-terminal.

        Returns:
            CommandResult: structured result of the execution.
        """
        user = self.username(name)
        return self._run_remote(name, command, user=user, use_sudo=True, use_pty=use_pty)

    def execute_parallel(self, hosts: List[str], command: str) -> Dict[str, CommandResult]:
        """Execute the same command on multiple hosts in parallel.

        Args:
            hosts: list of host names.
            command: the command to execute.

        Returns:
            Dict[str, CommandResult]: mapping of host to its result.
        """
        from concurrent.futures import ThreadPoolExecutor
        
        results = {}
        with ThreadPoolExecutor() as executor:
            future_to_host = {executor.submit(self.execute, host, command): host for host in hosts}
            for future in future_to_host:
                host = future_to_host[future]
                try:
                    results[host] = future.result()
                except Exception as e:
                    logger.error(f"Parallel execution failed for {host}: {e}")
        
        return results

    def local(self, command: str) -> str:
        """Execute the command on the localhost.

        Args:
            command: the command to execute.

        Returns:
            str: the output of the command.
        """
        return self.execute("localhost", command)

    def username(self, host: str) -> Optional[str]:
        """Returns the username for a given host, falling back to local user."""
        opts = self._get_resolved_config(host)
        user = opts.get("user", opts.get("User", ""))
        if user:
            return user
        return os.environ.get("USER", "user")
    def hostname(self, host: str) -> str:
        """Returns the actual HostName for the given host."""
        opts = self._get_resolved_config(host)
        hostname = opts.get("hostname", opts.get("HostName", ""))
        return hostname if hostname else host

    def yaml(self) -> str:
        """Returns the parsed SSH configuration in YAML format.

        Returns:
            A YAML string representation of the parsed hosts dictionary.
        """
        if not self.conf:
            return "{}"
        
        hosts_dict = {}
        for host in self.conf.hosts():
            hosts_dict[host] = self.conf.get_all(host)
        return yaml.dump(hosts_dict, default_flow_style=False)

    def get_tunnels(self) -> List[Dict]:
        """Extract all tunnel forwards (LocalForward, RemoteForward) from the config.
        
        Returns:
            List[Dict]: A list of tunnel definitions.
        """
        tunnels = []
        if not self.conf:
            return tunnels
            
        try:
            hosts = self.conf.hosts()
        except Exception as e:
            logger.error(f"Error parsing hosts for tunnels from {self.filename}: {e}")
            return tunnels

        for host in hosts:
            try:
                # sshconf stores forwards in the config dict for the host
                all_conf = self.conf.get_all(host)
                
                # LocalForward and RemoteForward can be lists or single strings
                for key in ['localforward', 'remoteforward']:
                    forward = all_conf.get(key)
                    if not forward:
                        continue
                    
                    forwards = forward if isinstance(forward, list) else [forward]
                    for f in forwards:
                        # Forward format: "local_port remote_host:remote_port"
                        parts = f.split()
                        if len(parts) >= 2:
                            local_port = parts[0]
                            remote_target = parts[1]
                            tunnels.append({
                                "host": host,
                                "type": "Local" if key == 'localforward' else "Remote",
                                "local_port": local_port,
                                "remote_target": remote_target
                            })
            except Exception as e:
                logger.warn(f"Skipping host {host} due to parsing error: {e}")
                continue
        return tunnels

    def delete(self, name: str):
        """Removes a host entry from the SSH config file.

        Args:
            name: the name of the host to remove.
        """
        if not self.conf:
            return

        try:
            self.conf.remove(name)
            self.conf.save()
        except Exception as e:
            raise SSHConfigError(f"Failed to delete host {name} from {self.filename}: {e}")

    def generate(
        self,
        host: str,
        hostname: str,
        identity: Optional[str] = None,
        user: Optional[str] = None,
        verbose: bool = False,
    ):
        """Adds a host to the config file with given parameters.

        Args:
            host: the alias for the host.
            hostname: the actual hostname or IP.
            identity: the path to the identity file.
            user: the username for the host.
            verbose: prints debug messages.
        """
        if not self.conf:
            return

    def _friendly_error(self, e: Exception) -> str:
        """Convert technical exceptions into user-friendly error messages."""
        msg = str(e)
        if "not enough values to unpack" in msg:
            return "Configuration syntax error: a line in this block is missing a required value (expected 'Key Value' format)."
        return msg


    def check(self) -> List[Dict]:
        """Check the SSH config file for malformed entries.
        
        Returns:
            List[Dict]: A list of errors found. Each error contains 'line' and 'message'.
        """
        errors = []
        if not self.filename.exists():
            return [{"line": 0, "message": f"Config file not found: {self.filename}"}]

        # Deep dive: isolate blocks to find the culprit
        try:
            with open(self.filename, "r") as f:
                lines = f.readlines()
        except Exception as e:
            return [{"line": 0, "message": f"Could not read file: {e}"}]

        current_host = None
        current_block = []
        start_line = 0

        for i, line in enumerate(lines, 1):
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#"):
                continue
            
            if trimmed.lower().startswith("host "):
                # Process previous block
                if current_host:
                    block_res = self._validate_block(current_host, current_block)
                    if not block_res["valid"]:
                        errors.append({"line": start_line, "message": f"Host {current_host}: {block_res['error']}"})
                
                current_host = trimmed[5:].strip()
                current_block = [line]
                start_line = i
            elif current_host:
                current_block.append(line)
            else:
                # Line before any Host block
                if trimmed:
                    errors.append({"line": i, "message": f"Global configuration line (applies to all hosts): {trimmed}"})

        # Process the last block
        if current_host:
            block_res = self._validate_block(current_host, current_block)
            if not block_res["valid"]:
                errors.append({"line": start_line, "message": f"Host {current_host}: {block_res['error']}"})

        return errors

    def _validate_block(self, host: str, block_lines: List[str]) -> Dict:
        """Validate a single host block by using the actual ssh binary.
        
        This is 100% compatible with OpenSSH syntax as it uses the real parser.
        """
        import tempfile
        import os
        import subprocess
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                tmp.writelines(block_lines)
                tmp_path = tmp.name
            
            try:
                # -F: use specific config file
                # -G: print configuration for this host (parses the config)
                # We use 'localhost' as a dummy host because ssh -G will parse the 
                # entire config file and fail if there are syntax errors, regardless 
                # of the host provided.
                result = subprocess.run(
                    ["ssh", "-F", tmp_path, "-G", "localhost"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    return {"valid": True}
                else:
                    # Use stderr for the error message, fallback to stdout
                    error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown SSH configuration error"
                    return {"valid": False, "error": error_msg}
                    
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            return {"valid": False, "error": f"Internal validation error: {e}"}


