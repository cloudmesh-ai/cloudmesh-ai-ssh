# Copyright 2026 Gregor von Laszewski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os
from pathlib import Path
from typing import Optional, Union

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cloudmesh.ai.common import logging as ai_log
from .base import SSHBase
from .exceptions import SSHEncryptionError

logger = ai_log.get_logger("ai.ssh.encryption")

class SSHEncryption(SSHBase):
    """Utility to encrypt and decrypt files using Hybrid RSA-AES encryption.
    
    This implementation uses RSA-OAEP to encrypt a random AES-GCM key,
    which in turn encrypts the actual file content. This allows for 
    files of any size to be encrypted securely.
    """

    def __init__(
        self, 
        file_in: Union[str, Path], 
        file_out: Union[str, Path], 
        key_path: Union[str, Path] = "~/.ssh/id_rsa", 
        pem_path: Union[str, Path] = "~/.ssh/id_rsa.pub.pem", 
        debug: bool = False
    ):
        super().__init__(debug=debug)
        self.file_in = self.resolve_path(file_in)
        self.file_out = self.resolve_path(file_out)
        self.key = self.resolve_path(key_path)
        self.pem = self.resolve_path(pem_path)

    def pem_create(self):
        """Create a PEM public key from the private key."""
        try:
            with open(self.key, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                )
            
            public_key = private_key.public_key()
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            with open(self.pem, "wb") as pem_file:
                pem_file.write(pem)
            
            if self.debug:
                logger.debug(f"Public PEM created at {self.pem}")
        except Exception as e:
            raise SSHEncryptionError(f"Failed to create PEM public key: {e}") from e

    def encrypt(self):
        """Encrypt the input file using Hybrid RSA-AES encryption."""
        try:
            if not self.file_in.exists():
                raise SSHEncryptionError(f"Input file not found: {self.file_in}")
            
            if not self.pem.exists():
                logger.warn(f"PEM file not found at {self.pem}, attempting to create it...")
                self.pem_create()

            # 1. Load the public key
            with open(self.pem, "rb") as pem_file:
                public_key = serialization.load_pem_public_key(pem_file.read())

            # 2. Generate a random AES-256 key and nonce
            aes_key = AESGCM.generate_key(bit_length=256)
            aesgcm = AESGCM(aes_key)
            nonce = os.urandom(12) # Standard GCM nonce size

            # 3. Encrypt the file content with AES-GCM
            with open(self.file_in, "rb") as f:
                data = f.read()
            
            ciphertext = aesgcm.encrypt(nonce, data, None)

            # 4. Encrypt the AES key with RSA-OAEP
            encrypted_aes_key = public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # 5. Store: [len(enc_key)][enc_key][nonce][ciphertext]
            with open(self.file_out, "wb") as f:
                f.write(len(encrypted_aes_key).to_bytes(4, byteorder='big'))
                f.write(encrypted_aes_key)
                f.write(nonce)
                f.write(ciphertext)

            if self.debug:
                logger.debug(f"File {self.file_in} encrypted to {self.file_out}")

        except Exception as e:
            raise SSHEncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, filename: Optional[Union[str, Path]] = None):
        """Decrypt the secret file using the private key."""
        try:
            secret_file = self.resolve_path(filename) if filename else self.file_out
            if not secret_file.exists():
                raise SSHEncryptionError(f"Secret file not found: {secret_file}")

            # 1. Load the private key
            with open(self.key, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None,
                )

            # 2. Read the encrypted file and extract components
            with open(secret_file, "rb") as f:
                key_len_bytes = f.read(4)
                if not key_len_bytes:
                    raise SSHEncryptionError("Invalid secret file: Empty file")
                key_len = int.from_bytes(key_len_bytes, byteorder='big')
                encrypted_aes_key = f.read(key_len)
                nonce = f.read(12)
                ciphertext = f.read()

            # 3. Decrypt the AES key using RSA-OAEP
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # 4. Decrypt the data using AES-GCM
            aesgcm = AESGCM(aes_key)
            decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
            
            print(decrypted_data.decode('utf-8'))

        except Exception as e:
            raise SSHEncryptionError(f"Decryption failed: {e}") from e

if __name__ == "__main__":
    # Professional test case
    test_file = Path("test_secret.txt")
    secret_file = Path("test_secret.enc")
    
    try:
        test_file.write_text("This is a professional secret that is now larger than 245 bytes. " * 10)
        
        # Use local path for key in test
        test_key = Path("test_id_rsa")
        test_pem = Path("test_id_rsa.pub.pem")
        
        # Generate a temporary test key
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(test_key, "wb") as f:
            f.write(priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        e = SSHEncryption(str(test_file), str(secret_file), key_path=str(test_key), pem_path=str(test_pem), debug=True)
        e.pem_create()
        e.encrypt()
        print("Encryption successful.")
        e.decrypt()
        print("Decryption successful.")
    except Exception as ex:
        logger.exception(f"Encryption test failed: {ex}")
    finally:
        test_file.unlink(missing_ok=True)
        secret_file.unlink(missing_ok=True)
        Path("test_id_rsa").unlink(missing_ok=True)
        Path("test_id_rsa.pub.pem").unlink(missing_ok=True)
