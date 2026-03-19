from click.testing import CliRunner
from fakturoid_connector.cli import cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Fakturoid" in result.output

def test_cli_report_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["report", "--help"])
    assert result.exit_code == 0
    assert "monthly" in result.output
    assert "yearly" in result.output
