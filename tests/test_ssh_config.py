import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
from cloudmesh.ai.ssh.ssh_config import SSHConfig

def test_ssh_config_init():
    cfg = SSHConfig()
    assert cfg.filename.exists() or str(cfg.filename).endswith('.ssh/config')
    assert cfg._resolved_cache == {}

@patch('subprocess.run')
def test_get_resolved_config(mock_run):
    # Mock ssh -G output
    mock_stdout = "hostname=real.host.com\nuser=testuser\nport=2222\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout)

    cfg = SSHConfig()
    resolved = cfg._get_resolved_config("myhost")

    assert resolved == {"hostname": "real.host.com", "user": "testuser", "port": "2222"}
    mock_run.assert_called_once()

@patch('subprocess.run')
def test_get_resolved_config_cache(mock_run):
    mock_stdout = "hostname=real.host.com\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout)

    cfg = SSHConfig()
    # First call
    cfg._get_resolved_config("myhost")
    # Second call
    cfg._get_resolved_config("myhost")

    assert mock_run.call_count == 1

@patch('subprocess.run')
def test_hostname(mock_run):
    # Case 1: HostName defined
    mock_run.return_value = MagicMock(returncode=0, stdout="hostname=real.host.com\n")
    cfg = SSHConfig()
    assert cfg.hostname("myhost") == "real.host.com"

    # Case 2: HostName not defined (fallback to alias)
    mock_run.return_value = MagicMock(returncode=0, stdout="user=testuser\n")
    # Reset cache
    cfg._resolved_cache = {}
    assert cfg.hostname("myhost") == "myhost"

@patch('subprocess.run')
def test_username(mock_run):
    # Case 1: User defined
    mock_run.return_value = MagicMock(returncode=0, stdout="user=testuser\n")
    cfg = SSHConfig()
    assert cfg.username("myhost") == "testuser"

    # Case 2: User not defined (fallback to system user)
    mock_run.return_value = MagicMock(returncode=0, stdout="hostname=real.host.com\n")
    # Reset cache
    cfg._resolved_cache = {}
    expected_user = os.environ.get("USER", "user")
    assert cfg.username("myhost") == expected_user

@patch('subprocess.run')
def test_get_options(mock_run):
    # Mock resolved config: HostName and User should be filtered out
    mock_stdout = "hostname=real.host.com\nuser=testuser\nport=2222\nForwardAgent=yes\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout)

    cfg = SSHConfig()
    options = cfg.get_options("myhost")

    # Should contain port and ForwardAgent, but not hostname or user
    assert "port=2222" in options
    assert "ForwardAgent=yes" in options
    assert "hostname" not in options.lower()
    assert "user" not in options.lower()

@patch('subprocess.run')
def test_get_resolved_config_failure(mock_run):
    # Simulate ssh -G failure
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

    cfg = SSHConfig()
    resolved = cfg._get_resolved_config("myhost")
    assert resolved == {}

@patch('subprocess.run')
def test_get_options_empty(mock_run):
    # Only HostName and User defined
    mock_stdout = "hostname=real.host.com\nuser=testuser\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=mock_stdout)

    cfg = SSHConfig()
    assert cfg.get_options("myhost") == ""
