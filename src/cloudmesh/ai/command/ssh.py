import click
import time
import sys
import requests
import yaml
from pathlib import Path
from cloudmesh.ai.common.io import console, path_expand, Table
from cloudmesh.ai.common.logging_utils import get_contextual_logger
from cloudmesh.ai.common.telemetry import Telemetry
from cloudmesh.ai.ssh.tunnel import Tunnel
from cloudmesh.ai.ssh.exceptions import SSHTunnelError
from cloudmesh.ai.ssh.ssh_config import SSHConfig

# Initialize Logger and Telemetry
logger = get_contextual_logger("ssh")
telemetry = Telemetry("ssh")
def load_llm_config():
    """Load LLM configuration from ~/.config/cloudmesh/ai/llm.yaml, creating it if missing."""
    config_path = Path("~/.config/cloudmesh/ai/llm.yaml").expanduser()
    
    if not config_path.exists():
        console.info(f"Creating default LLM config at {config_path}...")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            "url": "http://localhost:17704/v1",
            "model": "google/gemma-4-31B-it",
            "key": ""
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        console.info("Default config created. Please edit the file to add your API key.")
        return default_config
    
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading LLM config: {e}")
        return {}



def _render_table(rows):
    """Helper to render a list of dictionaries as a rich table."""
    if not rows:
        return None
    
    table = Table()
    
    # Use keys of the first dictionary as headers
    headers = list(rows[0].keys())
    for header in headers:
        table.add_column(header)
    
    # Add rows
    for row in rows:
        table.add_row(*[str(row.get(h, "")) for h in headers])
    
    return table

# Define the group for the command
@click.group(name="ssh")
def ssh_group():
    """ssh command group."""
    pass

@click.group(name="list", invoke_without_command=True)
@click.pass_context
def list_group(ctx):
    """List SSH configurations and active tunnels."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(hosts_cmd)

@list_group.command(name="hosts")
def hosts_cmd():
    """List all hosts defined in the SSH config file."""
    cfg = SSHConfig()
    hosts = cfg.list()
    
    if not hosts:
        console.info("No hosts found in SSH config.")
        return

    rows = []
    for host in hosts:
        rows.append({
            "Host": host,
            "Hostname": cfg.hostname(host),
            "User": cfg.username(host),
            "Details": cfg.get_options(host)
        })
    
    table = _render_table(rows)
    if table:
        console.print(table)

@list_group.command(name="tunnel")
def tunnel_list_cmd():
    """List all tunnels defined in config and their active status."""
    cfg = SSHConfig()
    tunnels = cfg.get_tunnels()
    
    if not tunnels:
        console.info("No tunnels defined in SSH config.")
        return

    from cloudmesh.ai.ssh.base import SSHBase
    checker = SSHBase()
    
    rows = []
    for t in tunnels:
        status = "Unknown"
        if t["type"] == "Local":
            try:
                is_open = checker.is_port_open("localhost", int(t["local_port"]))
                status = "Active" if is_open else "Inactive"
            except Exception:
                status = "Error"
        
        rows.append({
            "Host": t["host"],
            "Type": t["type"],
            "Local Port": t["local_port"],
            "Remote Target": t["remote_target"],
            "Status": status
        })
    
    table = _render_table(rows)
    if table:
        console.print(table)

ssh_group.add_command(list_group)

@ssh_group.command(name="run")
def run_cmd():
    """Run the main functionality of ssh."""
    logger.info("Executing ssh run command")
    console.ok(f"The ssh extension is running successfully!")

@ssh_group.command(name="tunnel")
@click.argument("target")
@click.option("--local-port", type=int, help="Local port to bind to. Defaults to remote port.")
@click.option("--remote-host", default="localhost", help="Remote host relative to the SSH server. Defaults to localhost.")
@click.option("--ssh-user", help="SSH username to use.")
def tunnel_cmd(target, local_port, remote_host, ssh_user):
    """Create an SSH tunnel.
    
    Target should be in the format HOST:PORT (e.g., my-server:8000).
    """
    try:
        if ":" not in target:
            raise click.BadParameter("Target must be in the format HOST:PORT")
        
        ssh_host, remote_port_str = target.split(":", 1)
        remote_port = int(remote_port_str)
        
        # Default local port to remote port if not provided
        l_port = local_port if local_port else remote_port
        
        console.info(f"Setting up tunnel: localhost:{l_port} -> {remote_host}:{remote_port} via {ssh_host}")
        
        tunnel = Tunnel(
            local_port=l_port,
            remote_host=remote_host,
            remote_port=remote_port,
            ssh_host=ssh_host,
            ssh_user=ssh_user
        )
        
        if tunnel.start():
            console.ok(f"Tunnel is active. Press Ctrl+C to stop it.")
            try:
                while True:
                    if not tunnel.is_active():
                        console.warn("Tunnel process terminated unexpectedly.")
                        break
                    time.sleep(1)
            except KeyboardInterrupt:
                console.info("\nStopping tunnel...")
                tunnel.stop()
                console.ok("Tunnel closed.")
        else:
            console.error("Failed to start tunnel.")
            sys.exit(1)
            
    except ValueError:
        raise click.BadParameter("Port must be a valid integer.")
    except SSHTunnelError as e:
        console.error(f"SSH Tunnel Error: {e}")
        sys.exit(1)
    except Exception as e:
        console.error(f"Unexpected error: {e}")
        sys.exit(1)

@ssh_group.command(name="test-path")
@click.argument("path")
def test_path_cmd(path):
    """Example command showing path expansion."""
    expanded = path_expand(path)
    console.info(f"Expanded path: {expanded}")

@click.group(name="check", invoke_without_command=True)
@click.pass_context
def check_group(ctx):
    """Check the SSH config file for malformed entries."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(check_basic)

@check_group.command(name="basic")
def check_basic():
    """Run basic SSH config validation."""
    cfg = SSHConfig()
    errors = cfg.check()
    
    if not errors:
        console.ok("SSH config is valid!")
        return

    console.print(f"[yellow]Found {len(errors)} issue(s) in {cfg.filename}:[/yellow]")
    
    rows = []
    for err in errors:
        message = err["message"]
        if ": " in message:
            category, details = message.split(": ", 1)
        else:
            category, details = message, ""
        
        rows.append({
            "Line": err["line"],
            "Category": category,
            "Details": details
        })
    
    table = _render_table(rows)
    if table:
        console.print(table)

@check_group.command(name="ai")
@click.option("--api-key", default=None, help="API key for the vLLM server.")
def check_ai(api_key):
    """Gather diagnostic data and submit it to the vLLM server for repair."""
    cfg = SSHConfig()
    
    console.info("Gathering SSH configuration diagnostics...")
    
    # 1. Get malformed entries
    errors = cfg.check()
    
    # 2. Get raw config content
    content = cfg.get_content()
    
    # 3. Package the data
    diag_data = {
        "config_file": str(cfg.filename),
        "raw_content": content,
        "errors": errors
    }
    
    # Load LLM config from YAML
    config = load_llm_config()
    
    # Determine base URL using url from config, default to http://localhost:17704/v1
    base_url = config.get("url", "http://localhost:17704/v1")
    
    # Determine API key priority: CLI -> YAML config -> legacy file
    if not api_key:
        api_key = config.get("key")
        if not api_key:
            try:
                key_path = Path("~/gemma/server_master_key.txt").expanduser()
                if key_path.exists():
                    api_key = key_path.read_text().strip()
            except Exception as e:
                logger.debug(f"Could not load default API key from ~/gemma/server_master_key.txt: {e}")
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        # a. Get the model name from the vLLM server
        model_response = requests.get(f"{base_url}/models", headers=headers, timeout=10)
        model_response.raise_for_status()
        models = model_response.json().get("data", [])
        
        # Use model from config if specified, otherwise use the first available model from server
        model_name = config.get("model")
        if not model_name and models:
            model_name = models[0]["id"]
        
        if not model_name:
            raise Exception("No model specified in config and no models found on the vLLM server.")
        
        # b. Construct the prompt for the LLM
        system_prompt = (
            "You are an expert SSH configuration assistant. Your goal is to analyze the provided "
            "SSH config diagnostics and provide a corrected version of the config file. "
            "Explain the issues found and provide the final corrected content clearly."
        )
        user_prompt = f"Please analyze these SSH config diagnostics and provide a fix:\n\n{diag_data}"
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        
        console.info(f"Sending diagnostics to vLLM model {model_name} at {base_url}/chat/completions...")
        
        response = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        answer = result["choices"][0]["message"]["content"]
        
        console.ok("AI Analysis complete!")
        console.print(f"\n[bold green]AI Repair Suggestion:[/bold green]\n\n{answer}")
            
    except requests.exceptions.ConnectionError:
        console.error(f"Could not connect to the vLLM server at {base_url}. Is it running?")
        _save_fallback(diag_data)
    except Exception as e:
        console.error(f"An error occurred during AI analysis: {e}")
        _save_fallback(diag_data)

def _save_fallback(diag_data):
    diag_file = Path("ssh_diag.json")
    import json
    with open(diag_file, "w") as f:
        json.dump(diag_data, f, indent=4)
    console.print(f"[yellow]Diagnostic data saved to {diag_file} as fallback.[/yellow]")

ssh_group.add_command(check_group)

entry_point = ssh_group

def register(cli):
    """Registers the ssh command group to the main CLI."""
    cli.add_command(ssh_group, name="ssh")
