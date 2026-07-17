"""FastMCP application instance and entry point."""

import logging
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def _read_only_enabled() -> bool:
    """Resolve read-only mode from the MONARCH_READ_ONLY environment variable.

    Defaults to True (read-only) when the variable is unset, so a fresh
    install cannot modify Monarch data until write access is explicitly
    enabled. Only an explicit falsey word (0/false/no/off) turns writes on;
    an unset or empty value stays read-only so a stray ``MONARCH_READ_ONLY=``
    cannot silently enable writes.
    """
    raw = os.getenv("MONARCH_READ_ONLY")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


# Whether the server refuses to register state-changing (write) tools.
READ_ONLY = _read_only_enabled()

# Initialize FastMCP server
mcp = FastMCP("Monarch Money MCP Server")


def mutating_tool(*args, **kwargs):
    """Register a state-changing tool only when NOT in read-only mode.

    Drop-in replacement for ``@mcp.tool()`` on any tool that writes to
    Monarch (create/update/delete/set, or otherwise triggers a server-side
    change). In read-only mode (the default) the wrapped function is returned
    unregistered, so it never appears in the MCP tool list and cannot be
    invoked by a client. Set ``MONARCH_READ_ONLY=false`` to expose these tools.
    """

    def decorator(func):
        if READ_ONLY:
            return func
        return mcp.tool(*args, **kwargs)(func)

    return decorator


logger.info(
    "Monarch MCP read-only mode is %s (set MONARCH_READ_ONLY=false to enable writes)",
    "ON" if READ_ONLY else "OFF",
)

# Import tools package to trigger @mcp.tool() registration
import monarch_mcp_server.tools  # noqa: E402, F401

# Export for `mcp run`
app = mcp


def main() -> None:
    """Main entry point for the server."""
    logger.info("Starting Monarch Money MCP Server...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to run server: {str(e)}")
        raise


if __name__ == "__main__":
    main()
