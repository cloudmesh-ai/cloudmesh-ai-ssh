import pytest
from click.testing import CliRunner
from cloudmesh.ai.cmc.main import cli

def test_hello():
    runner = CliRunner()
    result = runner.invoke(cli, ["ssh", "hello"])
    assert result.exit_code == 0
    assert "Hello from ssh!" in result.output