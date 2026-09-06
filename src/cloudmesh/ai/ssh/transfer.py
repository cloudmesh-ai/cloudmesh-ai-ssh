# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

from pathlib import Path
from typing import Optional, Union
from cloudmesh.ai.common import logging as ai_log
from .base import SSHBase
from .exceptions import SSHConnectionError

logger = ai_log.get_logger("ai.ssh.transfer")

class SSHFileTransfer(SSHBase):
    """Utility to transfer files to and from remote hosts using Fabric/SFTP."""

    def upload(
        self, 
        local_path: Union[str, Path], 
        remote_path: Union[str, Path], 
        host: str, 
        user: Optional[str] = None
    ) -> None:
        """Upload a file to a remote host.

        Args:
            local_path: path to the local file.
            remote_path: path to the destination on the remote host.
            host: the remote host.
            user: optional username.

        Returns:
            bool: True if successful, False otherwise.
        """
        local_path = self.resolve_path(str(local_path))
        if not local_path.exists():
            logger.error(f"Local file not found: {local_path}")
            raise SSHConnectionError("Failed to upload file")

        if self.debug:
            logger.debug(f"Uploading {local_path} to {host}:{remote_path}")

        try:
            conn = self._get_connection(host, user)
            conn.put(str(local_path), str(remote_path))
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to {host}: {e}")
            raise SSHConnectionError("Failed to upload file")

    def download(
        self, 
        remote_path: Union[str, Path], 
        local_path: Union[str, Path], 
        host: str, 
        user: Optional[str] = None
    ) -> None:
        """Download a file from a remote host.

        Args:
            remote_path: path to the file on the remote host.
            local_path: path to the destination on the local system.
            host: the remote host.
            user: optional username.

        Returns:
            bool: True if successful, False otherwise.
        """
        local_path = self.resolve_path(str(local_path))
        if self.debug:
            logger.debug(f"Downloading {remote_path} from {host} to {local_path}")

        try:
            conn = self._get_connection(host, user)
            conn.get(str(remote_path), str(local_path))
            return True
        except Exception as e:
            logger.error(f"Failed to download file from {host}: {e}")
            raise SSHConnectionError("Failed to upload file")