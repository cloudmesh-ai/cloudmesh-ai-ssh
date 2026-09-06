# cloudmesh-ai-ssh

`cloudmesh-ai-ssh` is a professional SSH management extension for the Cloudmesh AI ecosystem. It provides a high-level Python API and CLI tools for managing SSH tunnels, configuration files, authorized keys, and RSA encryption, designed specifically for AI agents and cloud automation.

## 🚀 Key Features

- **AI-Powered Config Repair**: Automatically diagnose malformed `~/.ssh/config` entries and submit them to a vLLM server for expert AI-driven repair suggestions.

- **Advanced Tunneling**: Create and manage SSH port-forwarding tunnels with automatic lifecycle management and aggressive "force-stop" cleanup.
- **SSH Config Management**: Programmatically read, modify, and generate `~/.ssh/config` entries with a rich CLI list view.
- **Secure File Transfer**: High-level wrappers for SFTP uploads and downloads via Fabric.
- **Key Management**: Manage `authorized_keys` files and generate public key fingerprints.
- **RSA Encryption**: Encrypt and decrypt files using RSA keys via OpenSSL.
- **Robust Error Handling**: A dedicated exception hierarchy for precise error catching in automation pipelines.

## 📦 Installation

```bash
pip install .
```

## 🛠 Quick Start

### CLI Usage

The `cmc ssh` command group provides a convenient way to manage tunnels from the terminal.

**Create a tunnel:**
```bash
# Format: cmc ssh tunnel "SSH_HOST:REMOTE_PORT"
cmc ssh tunnel "my-server:8000"
```
*This creates a tunnel from `localhost:8000` $\rightarrow$ `localhost:8000` via `my-server`.*

**Advanced tunnel options:**
```bash
cmc ssh tunnel "my-server:8000" --local-port 9000 --remote-host "db-internal.local" --ssh-user "admin"
```


**List SSH Hosts (with details):**
```bash
cmc ssh list
```
*Displays a rich table of all hosts, their hostnames, users, and detailed configuration options.*

**Diagnose and Repair Config with AI:**
```bash
# Uses default vLLM server (localhost:17704) and master key from ~/gemma/server_master_key.txt
cmc ssh check ai

# Specify a custom vLLM server and API key
cmc ssh check ai --url http://ai-server:17704 --api-key YOUR_API_KEY
```
*Detects syntax errors in your SSH config and provides an AI-generated corrected version.*

**List SSH Hosts (with details):**
```bash
cmc ssh list
```
*Displays a rich table of all hosts, their hostnames, users, and detailed configuration options.*

**Diagnose and Repair Config with AI:**
```bash
# Uses default vLLM server (localhost:17704) and master key from ~/gemma/server_master_key.txt
cmc ssh check ai

# Specify a custom vLLM server and API key
cmc ssh check ai --url http://ai-server:17704 --api-key YOUR_API_KEY
```
*Detects syntax errors in your SSH config and provides an AI-generated corrected version.*


### Python API Usage

#### 1. SSH Tunneling
```python
from cloudmesh.ai.ssh.tunnel import Tunnel

# Using the context manager for automatic cleanup
with Tunnel(local_port=8080, remote_host="localhost", remote_port=80, ssh_host="jump-box") as tunnel:
    print("Tunnel is active! Access the remote service at http://localhost:8080")
    # Your application logic here
```

#### 2. SSH Configuration
```python
from cloudmesh.ai.ssh.ssh_config import SSHConfig

cfg = SSHConfig()
# Generic generation: no more hardcoded defaults!
cfg.generate(host="my-server", hostname="1.2.3.4", user="ubuntu")
print(f"Hosts defined in config: {cfg.names()}")
```

#### 3. RSA Encryption
```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption(file_in="secrets.txt", file_out="secrets.enc")
enc.pem_create() # Create public PEM from private key
enc.encrypt()    # Encrypt the file
enc.decrypt()    # Decrypt the file
```

## 📚 Documentation

For detailed technical information, please visit the [API Reference](docs/api.md) and [Usage Guides](docs/usage.md).

## ⚙️ Core Dependencies

This project is part of the Cloudmesh AI ecosystem and depends on:
- [cloudmesh-ai-common](https://github.com/cloudmesh-ai/cloudmesh-ai-common)
- [cloudmesh-ai-cmc](https://github.com/cloudmesh-ai/cloudmesh-ai-cmc)
- `fabric` (for SSH connections)
- `sshconf` (for config parsing)
- `openssl` (CLI tool for encryption)

