# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

class SSHError(Exception):
    """Base exception for all SSH utilities."""
    pass

class SSHConnectionError(SSHError):
    """Raised when a connection to a remote host fails."""
    pass

class SSHConfigError(SSHError):
    """Raised when there is an error reading or writing the SSH config."""
    pass

class SSHTunnelError(SSHError):
    """Raised when an SSH tunnel fails to start, stop, or maintain connectivity."""
    pass

class SSHEncryptionError(SSHError):
    """Raised when encryption or decryption operations fail."""
    pass
