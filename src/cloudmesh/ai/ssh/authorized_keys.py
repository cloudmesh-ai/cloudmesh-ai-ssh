# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import io
from pathlib import Path
from typing import Dict, List, Optional, Union

from cloudmesh.ai.common import logging as ai_log
from .base import SSHBase
from .exceptions import SSHError

logger = ai_log.get_logger("ai.ssh.authorized_keys")


class AuthorizedKeys(SSHBase):
    """Class to manage authorized keys."""

    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        self._order: Dict[int, str] = {}
        self._keys: Dict[str, str] = {}

    def get_fingerprint_from_public_key(self, pubkey: str) -> str:
        """Generate the fingerprint of a public key.

        Args:
            pubkey (str): the value of the public key

        Returns:
            str: fingerprint
        """
        try:
            # Use ssh-keygen -l -f /dev/stdin to avoid creating temporary files
            process = self._execute(
                ["ssh-keygen", "-l", "-f", "/dev/stdin"],
                input_data=pubkey
            )
            output = process.stdout.strip()
            # Output format: "2048 SHA256:abc... user@host (RSA)"
            parts = output.split(' ')
            if len(parts) >= 2:
                return parts[1]
            return output
        except Exception as e:
            logger.error(f"Failed to get fingerprint for public key: {e}")
            return ""

    def load(self, path: Union[str, Path]) -> None:
        """Load the keys from a path.

        Args:
            path: the filename (path) in which we find the keys
        """
        path = self.resolve_path(str(path))
        if not path.exists():
            logger.warning(f"Authorized keys file not found: {path}")
            return

        try:
            with path.open('r') as fd:
                for pubkey in map(str.strip, fd):
                    # skip empty lines and comments
                    if not pubkey or pubkey.startswith('#'):
                        continue
                    self.add(pubkey)
        except Exception as e:
            logger.error(f"Error loading authorized keys from {path}: {e}")

    def add(self, pubkey: str):
        """Add a public key.

        Args:
            pubkey: the public key string.
        """
        fingerprint = self.get_fingerprint_from_public_key(pubkey)
        if not fingerprint:
            logger.warning("Could not generate fingerprint for public key; skipping.")
            return

        if fingerprint not in self._keys:
            self._order[len(self._keys)] = fingerprint
            self._keys[fingerprint] = pubkey

    def remove(self, fingerprint: str):
        """Removes the public key by its fingerprint.

        Args:
            fingerprint: the fingerprint of the public key to remove.
        """
        if fingerprint in self._keys:
            del self._keys[fingerprint]
            # Rebuild order to keep it contiguous
            new_order = {}
            for i, f in enumerate(self._order.values()):
                if f != fingerprint:
                    new_order[i] = f
            self._order = new_order
        else:
            logger.warning(f"Fingerprint {fingerprint} not found in authorized keys.")

    def __str__(self) -> str:
        with io.StringIO() as sio:
            for fingerprint in self._order.values():
                key = self._keys.get(fingerprint)
                if key:
                    sio.write(key)
                    sio.write('\n')
            return sio.getvalue().strip()

    def __repr__(self) -> str:
        return f"AuthorizedKeys(keys={len(self._keys)})"


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python authorized_keys.py <path_to_authorized_keys>")
        sys.exit(1)

    path = sys.argv[1]
    auth = AuthorizedKeys()
    auth.load(path)
    print(auth)
