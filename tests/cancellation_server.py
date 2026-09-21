"""Test server whose analysis worker waits until its MCP request is cancelled."""

from droidasc_mcp.config import Settings
from droidasc_mcp.runner import DroidAscRunner
from droidasc_mcp.server import build_server


def main():
    settings = Settings.from_env()
    runner = DroidAscRunner(settings, module_name="process_fixture")
    build_server(settings, runner).run()


if __name__ == "__main__":
    main()
