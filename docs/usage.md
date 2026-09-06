# Usage Guide: cloudmesh-ai-ssh

This guide provides practical, easy-to-follow examples for using the `cloudmesh-ai-ssh` library.

## 🚀 SSH Tunneling Made Simple

An SSH tunnel allows you to securely access a service on a remote network as if it were running on your own machine.

### The "Quick & Easy" Way
If you just want to get a tunnel up and running quickly:

```python
from cloudmesh.ai.ssh.tunnel import Tunnel

# 1. Define the tunnel
# "I want local port 8000 to connect to localhost:8000 on my-server"
tunnel = Tunnel(
    local_port=8000, 
    remote_host="localhost", 
    remote_port=8000, 
    ssh_host="my-server"
)

# 2. Start it
tunnel.start()

print("Tunnel is open! Visit http://localhost:8000")

# 3. Stop it when you are done
tunnel.stop()
```

### The "Professional" Way (Recommended)
Using a `with` block (context manager) is the best practice because it **automatically closes the tunnel** for you, even if your code crashes.

```python
from cloudmesh.ai.ssh.tunnel import Tunnel

with Tunnel(8080, "localhost", 80, "jump-box") as tunnel:
    print("Securely connected to remote port 80 via jump-box on localhost:8080")
    # Your code here...
# Tunnel is automatically closed here!
```

### What do the Tunnel arguments mean?
| Argument | Simple Explanation | Example |
| :--- | :--- | :--- |
| `local_port` | The port you type into your browser. | `8080` $\rightarrow$ `http://localhost:8080` |
| `remote_host` | The destination address *from the perspective of the server*. | `"localhost"` (the server itself) or `"db.internal"` |
| `remote_port` | The port the service is actually running on remotely. | `80` (HTTP) or `5432` (Postgres) |
| `ssh_host` | The server you have SSH access to (the "Jump Box"). | `"my-server"` or `"ubuntu@1.2.3.4"` |

---


### Listing Hosts with Details
The `list` command provides a comprehensive overview of your SSH configuration.
```bash
# List all hosts with Hostname, User, and detailed options
cmc ssh list
```

### AI-Powered Configuration Repair
If your SSH config is malformed or you're seeing connection errors, you can use the AI diagnostic tool to find and fix them.

```bash
# Basic check using default vLLM server
cmc ssh check ai

# Advanced check specifying a custom server and API key
cmc ssh check ai --url http://your-vllm-server:17704 --api-key your-api-key-here
```
This command:
1. Scans your `~/.ssh/config` for syntax errors.
2. Sends the problematic block to a vLLM AI server.
3. Returns a corrected version of the config block with an explanation of the fix.

## ⚙️ Managing SSH Configs

You can manage your `~/.ssh/config` file without opening a text editor.

### Adding a New Server
```python
from cloudmesh.ai.ssh.ssh_config import SSHConfig

cfg = SSHConfig()
cfg.generate(
    host="work-server", 
    hostname="10.0.0.5", 
    user="dev-user"
)
```

---

## 🔐 Secure Encryption

Use this to encrypt sensitive files before uploading them to a cloud environment.

### Encrypting a Secret File
```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

# Setup: input file, output file
enc = SSHEncryption("passwords.txt", "passwords.enc")

enc.pem_create() # Prepare the keys
enc.encrypt()    # Create the encrypted file
```

### Decrypting a Secret File
```python
from cloudmesh.ai.ssh.encryption import SSHEncryption

enc = SSHEncryption("temp.txt", "passwords.enc")
enc.decrypt()    # Content is printed to the console
```
