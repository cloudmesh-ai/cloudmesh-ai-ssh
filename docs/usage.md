# Usage Guide: cloudmesh-ai-ssh

This guide provides a comprehensive technical reference for the `cloudmesh-ai-ssh` CLI commands and Python API.

## SSH Tunneling

SSH tunnels allow secure access to remote services by forwarding a local port to a remote host via a jump server.

### CLI Reference

The primary command for tunneling is `cmc ssh tunnel`.

#### Basic Tunnel
Forward a local port to the same port on a remote host.

```bash
cmc ssh tunnel "my-server:8000"
```

This forwards `localhost:8000` to `localhost:8000` on `my-server`.

#### Advanced Tunnel
Specify a different local port, remote host, and SSH user.

```bash
cmc ssh tunnel "my-server:8000" --local-port 9000 --remote-host "db-internal.local" --ssh-user "admin"
```

#### Command Options
| Option | Description | Example |
| :--- | :--- | :--- |
| `--local-port` | The port to open on the local machine. | `--local-port 9000` |
| `--remote-host` | The target host from the jump server's perspective. | `--remote-host "localhost"` |
| `--ssh-user` | The user used to connect to the jump server. | `--ssh-user "ubuntu"` |

### Python API Reference

Use the `Tunnel` class to manage tunnels programmatically.

```python
from cloudmesh.ai.ssh.tunnel import Tunnel

# Using the context manager ensures the tunnel is closed on exit
with Tunnel(local_port=8080, remote_host="localhost", remote_port=80, ssh_host="jump-box") as tunnel:
    # Tunnel is now active
    pass
```

## SSH Configuration Management

The library provides tools to inspect and modify the `~/.ssh/config` file.

### CLI Reference

#### List Hosts
Display all hosts defined in the SSH configuration with their associated hostnames, users, and options.

```bash
cmc ssh list
```

### Python API Reference

Use the `SSHConfig` class to manipulate the configuration file.

#### Generating a Host Entry
Add a new host entry to the configuration.

```python
from cloudmesh.ai.ssh.ssh_config import SSHConfig

cfg = SSHConfig()
cfg.generate(host="work-server", hostname="10.0.0.5", user="dev-user")
```

#### Listing Host Names
Retrieve a list of all host identifiers defined in the config.

```python
names = cfg.names()
```

## AI-Powered Configuration Repair

The `cloudmesh-ai-ssh` library can diagnose syntax errors in the SSH configuration and suggest precise fixes via a vLLM AI server.

### How it Works

1.  **Configuration Scanning**: The tool identifies malformed entries in `~/.ssh/config` using the `SSHConfig` parser.
2.  **Data Packaging**: It bundles the identified errors and the raw configuration content into a diagnostic payload.
3.  **AI Analysis**: This payload is submitted to a vLLM server (OpenAI-compatible API). The server analyzes the syntax errors and generates a corrected version of the configuration.
4.  **Repair Suggestion**: The AI's analysis and the corrected configuration block are printed directly to the console.

### CLI Reference

#### Run AI Diagnostics
Scan the SSH config for errors and submit them for AI repair.

```bash
cmc ssh check ai
```

#### Custom Server Configuration
Specify a custom vLLM server URL and API key.

```bash
cmc ssh check ai --url http://ai-server:17704 --api-key YOUR_API_KEY
```

!!! warning "API Key Requirement"

The `check ai` command requires an API key. By default, it looks for a key in `~/gemma/server_master_key.txt`.

!!! note "Fallback Diagnostics"

If the tool cannot connect to the vLLM server, it automatically saves the diagnostic data to `ssh_diag.json` in the current working directory for manual inspection.

## RSA Encryption

The `SSHEncryption` class provides a wrapper for encrypting and decrypting files using RSA keys via OpenSSL.

### Python API Reference

#### Encrypting a File
This process involves creating a public PEM from a private key and then encrypting the target file.

```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption(file_in="secrets.txt", file_out="secrets.enc")
enc.pem_create()
enc.encrypt()
```

#### Decrypting a File
Decrypts the encrypted file and prints the content.

```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption(file_in="temp.txt", file_out="secrets.enc")
enc.decrypt()
```
