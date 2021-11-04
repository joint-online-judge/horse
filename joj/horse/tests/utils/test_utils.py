import pytest
from click.testing import CliRunner

from joj.horse.__main__ import main


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUtils")
class TestUtils:
    @pytest.mark.parametrize("arg", ["-h", "--help"])
    def test_cli_help(self, arg: str) -> None:
        runner = CliRunner()
        result = runner.invoke(main, [arg])
        assert result.exit_code == 0
