# cloudmesh-ai-ssh

**Code:** [GitHub](https://github.com/cloudmesh-ai/cloudmesh-ai-ssh) | **Documentation:** [Docs](https://cloudmesh-ai.github.io/cloudmesh-ai-ssh/)

!!! info "Learning Objectives"

    * Install and configure the `cloudmesh-ai-ssh` package.
    * Create and manage SSH tunnels for remote service access.
    * Programmatically manipulate the SSH configuration file.
    * Use AI to diagnose and repair malformed SSH configuration entries.
    * Encrypt and decrypt files using RSA keys.

The `cloudmesh-ai-ssh` library provides a Python API and CLI tools for managing SSH tunnels, configuration files, authorized keys, and RSA encryption. It is designed for use in automation pipelines and by AI agents.

## Installation

Install the package from PyPI:

```bash
pip install cloudmesh-ai-ssh
```

Install the package in editable mode for local development:

```bash
pip install -e .
```

## SSH Tunneling

SSH tunnels allow secure access to remote services by forwarding a local port to a remote host via a jump server.

### Creating a tunnel via CLI

Use the `cmc ssh tunnel` command. The basic format is `SSH_HOST:REMOTE_PORT`.

```bash
cmc ssh tunnel "my-server:8000"
```

This forwards `localhost:8000` to `localhost:8000` on `my-server`.

### Advanced tunnel configuration

You can specify custom local ports and remote hosts:

```bash
cmc ssh tunnel "my-server:8000" --local-port 9000 --remote-host "db-internal.local" --ssh-user "admin"
```

### Using the Python API

The `Tunnel` class supports the context manager pattern to ensure tunnels are closed automatically.

```python
from cloudmesh.ai.ssh.tunnel import Tunnel

with Tunnel(local_port=8080, remote_host="localhost", remote_port=80, ssh_host="jump-box") as tunnel:
    print("Tunnel is active. Access the remote service at http://localhost:8080")
```

## SSH Configuration Management

The library allows reading and modifying the `~/.ssh/config` file without manual text editing.

### Listing hosts

Use the `list` command to see a detailed table of all defined hosts, including their hostnames, users, and options.

```bash
cmc ssh list
```

### Generating config entries

Use the `SSHConfig` class to add new hosts to the configuration.

```python
from cloudmesh.ai.ssh.ssh_config import SSHConfig

cfg = SSHConfig()
cfg.generate(host="my-server", hostname="1.2.3.4", user="ubuntu")
```

## AI-Powered Configuration Repair

The `cloudmesh-ai-ssh` tool can detect syntax errors in your SSH configuration and use a vLLM AI server to suggest precise repairs.

### How it Works

1.  **Diagnostics**: The tool scans `~/.ssh/config` for malformed entries and extracts the raw configuration content.
2.  **AI Analysis**: It sends this diagnostic data to a vLLM server (which uses an OpenAI-compatible API).
3.  **Repair Suggestion**: The AI analyzes the errors and provides a corrected version of the configuration block with an explanation of the fix.

### Running diagnostics

Use the `check ai` command to begin the process. By default, the tool looks for an API key in `~/gemma/server_master_key.txt` and connects to a local vLLM server.

```bash
cmc ssh check ai
```

### Custom AI server configuration

If your vLLM server is hosted on a different URL or requires a specific API key, use the following options:

```bash
cmc ssh check ai --url http://ai-server:17704 --api-key YOUR_API_KEY
```

!!! note "Fallback Behavior"
    If the tool cannot connect to the vLLM server, it will automatically save the gathered diagnostic data to `ssh_diag.json` in your current directory so you can analyze the errors manually.

## RSA Encryption

The `SSHEncryption` class provides wrappers for RSA encryption and decryption using OpenSSL.

### Encrypting a file

```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption(file_in="secrets.txt", file_out="secrets.enc")
enc.pem_create()
enc.encrypt()
```

### Decrypting a file

```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption(file_in="temp.txt", file_out="secrets.enc")
enc.decrypt()
```

## Summary Checklist

* Installed `cloudmesh-ai-ssh`.
* Created a local-to-remote SSH tunnel.
* Listed and generated SSH configuration entries.
* Repaired a malformed config using the AI diagnostic tool.
* Encrypted and decrypted a file using RSA.

## Practical Assignments

!!! note "Assignment 1: Basic Tunneling"

    Create a tunnel that forwards local port 8081 to a remote service running on port 80 at `internal-web.local` via a jump host named `bastion`.

!!! note "Assignment 2: Config Automation"

    Write a Python script that checks if a host named `dev-server` exists in the SSH config. If it does not, generate a new entry with hostname `192.168.1.10` and user `devuser`.

!!! note "Assignment 3: AI Repair"

    Intentionally introduce a syntax error into your `~/.ssh/config` (e.g., an invalid keyword). Use `cmc ssh check ai` to detect the error and apply the AI-suggested fix.

## Core Dependencies

This project depends on the following components:

* [cloudmesh-ai-common](https://github.com/cloudmesh-ai/cloudmesh-ai-common)
* [cloudmesh-ai-cmc](https://github.com/cloudmesh-ai/cloudmesh-ai-cmc)
* `fabric` for SSH connections.
* `sshconf` for config parsing.
* `openssl` CLI tool for encryption.
