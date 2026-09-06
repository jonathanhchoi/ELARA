"""Windows command construction for explicit host adapters and synthetic probes.

No invocation, file mutation, configuration inference, or model choice occurs here.
Callers provide an already authorized argv; literal TOML gives explicit settings
that survive the tested cmd.exe and batch percent-star forwarding boundaries.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def literal_toml_setting(key: str, value: str) -> str:
    if not key or not all(c.isalnum() or c in "_." for c in key):
        raise ValueError("invalid_config_key")
    if any(c in value for c in "'\r\n\x00"):
        raise ValueError("invalid_literal_value")
    return f"{key}='{value}'"


def backend_overrides() -> list[str]:
    """Explicit operational contract; presence alone is not host verification."""
    settings = ["features.multi_agent_v2.enabled=true",
        literal_toml_setting("features.multi_agent_v2.tool_namespace", "collaboration"),
        "features.multi_agent_v2.expose_spawn_agent_model_overrides=true",
        "features.multi_agent_v2.wait_agent_enabled=true"]
    return [item for setting in settings for item in ("-c", setting)]


def cmd_wrapper(argv: list[str]) -> str:
    if not argv or not all(isinstance(value, str) and value and not any(c in value for c in "\r\n\x00") for value in argv):
        raise ValueError("invalid_command_arguments")
    # Only spaces are shell-quoted here. Literal double quotes, expansion, and
    # grouping characters need a different transport; reject rather than guess.
    if any(any(c in value for c in '%!&|<>^()"') for value in argv):
        raise ValueError("shell_metacharacter_in_argument")
    comspec = Path(os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe"))
    if comspec.name.casefold() != "cmd.exe" or not comspec.is_file():
        raise ValueError("comspec_drift")
    # Popen must receive this raw command line. Returning a list would serialize
    # it a second time and escape the quote marks around a spaced executable.
    # /s strips exactly the outer pair while retaining each argument's quotes.
    return subprocess.list2cmdline([str(comspec)]) + ' /d /s /c "' + subprocess.list2cmdline(argv) + '"'


def quote_free_atom(value: object) -> str:
    """Hooks use a deliberately narrower no-spaces/no-quotes command contract."""
    text = str(value)
    if not text or any(c.isspace() or c in "\"'&|<>^()%!" for c in text):
        raise ValueError("unsafe_hook_command_atom")
    return text


def hook_command(wrapper: Path, arguments: list[str]) -> str:
    return "cmd.exe /d /s /c " + " ".join(quote_free_atom(v) for v in [str(wrapper.resolve()), *arguments])
