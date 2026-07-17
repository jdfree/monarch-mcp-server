"""Tests for read-only mode gating of mutating tools.

Each case runs in a fresh subprocess so the module-level FastMCP singleton
(built once at import time from MONARCH_READ_ONLY) is evaluated cleanly and
does not leak between cases or into the rest of the suite.
"""

import json
import os
import subprocess
import sys

import pytest

# A representative mutating tool from each domain module.
MUTATING_TOOLS = {
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    "bulk_categorize_transactions",
    "set_budget_amount",
    "create_transaction_category",
    "set_transaction_tags",
    "create_transaction_rule",
    "delete_transaction_rule",
    "split_transaction",
    "upload_account_balance_history",
    "refresh_accounts",
}

# Read/query and auth tools that must always remain available.
ALWAYS_ON_TOOLS = {
    "get_accounts",
    "get_transactions",
    "get_net_worth",
    "get_budgets",
    "monarch_login",
    "check_auth_status",
}

_SNIPPET = """
import asyncio, json
import monarch_mcp_server.app as app
names = [t.name for t in asyncio.run(app.mcp.list_tools())]
print(json.dumps({"read_only": app.READ_ONLY, "tools": names}))
"""


def _list_tools(read_only_env):
    env = dict(os.environ)
    env.pop("MONARCH_READ_ONLY", None)
    if read_only_env is not None:
        env["MONARCH_READ_ONLY"] = read_only_env
    out = subprocess.check_output([sys.executable, "-c", _SNIPPET], env=env, text=True)
    return json.loads(out.strip().splitlines()[-1])


def test_read_only_is_default():
    """With MONARCH_READ_ONLY unset the server comes up read-only."""
    result = _list_tools(None)
    assert result["read_only"] is True
    assert MUTATING_TOOLS.isdisjoint(result["tools"])
    assert ALWAYS_ON_TOOLS.issubset(result["tools"])


@pytest.mark.parametrize("value", ["false", "0", "no", "off"])
def test_falsey_values_enable_writes(value):
    """Explicit falsey values expose the mutating tools."""
    result = _list_tools(value)
    assert result["read_only"] is False
    assert MUTATING_TOOLS.issubset(result["tools"])


@pytest.mark.parametrize("value", ["true", "1", "yes", "anything_else", ""])
def test_truthy_and_unknown_values_stay_read_only(value):
    """Anything that is not an explicit falsey value stays read-only."""
    result = _list_tools(value)
    assert result["read_only"] is True
    assert MUTATING_TOOLS.isdisjoint(result["tools"])
