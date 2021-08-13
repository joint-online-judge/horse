import pytest
from click.testing import CliRunner

from joj.horse.__main__ import main


@pytest.mark.parametrize("arg", ["-h", "--help"])
def test_cli_help(arg: str) -> None:
    runner = CliRunner()
    result = runner.invoke(main, [arg])
    assert result.exit_code == 0
