"""Shared local runtime preferences and optimization policy.

All updated HTTP and local MCP processes read the same per-user SQLite settings.
No credentials, prompts, repository paths or connection claims are stored.
"""
from contextlib import closing
from pathlib import Path
import os
import sqlite3
from pydantic import BaseModel, ConfigDict, StrictBool
from typing import Literal

IDE = Literal["auto", "intellij", "vscode", "eclipse", "web", "other"]
Agent = Literal["auto", "copilot", "codex", "claude", "chatgpt", "gemini", "other"]

class ControlSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool = True
    preferred_ide: IDE = "auto"
    preferred_agent: Agent = "auto"


def control_path():
    return Path(os.environ.get("ATOF_CONTROL_DB") or Path.home()/".atof"/"control-v1.sqlite3").expanduser()


def _connect(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=3)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS control_settings (
          singleton INTEGER PRIMARY KEY CHECK(singleton=1),
          enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
          preferred_ide TEXT NOT NULL, preferred_agent TEXT NOT NULL)""")
        return conn
    except BaseException:
        conn.close()
        raise


def read_settings():
    path = control_path()
    if not path.exists():
        return ControlSettings()
    with closing(_connect(path)) as conn:
        row = conn.execute("SELECT enabled, preferred_ide, preferred_agent FROM control_settings WHERE singleton=1").fetchone()
    if row is None:
        return ControlSettings()
    if row[0] not in (0, 1):
        raise ValueError("Invalid stored optimization switch")
    return ControlSettings(enabled=bool(row[0]), preferred_ide=row[1], preferred_agent=row[2])


def save_settings(settings):
    settings = ControlSettings.model_validate(settings)
    with closing(_connect(control_path())) as conn, conn:
        conn.execute("""INSERT INTO control_settings VALUES (1,?,?,?)
          ON CONFLICT(singleton) DO UPDATE SET enabled=excluded.enabled,
          preferred_ide=excluded.preferred_ide, preferred_agent=excluded.preferred_agent""",
          (int(settings.enabled), settings.preferred_ide, settings.preferred_agent))
    return settings


def snapshot():
    try:
        settings = read_settings()
        return {"settings":settings.model_dump(), "available":True, "error":None,
                "connection_verified":False, "scope":"updated local HTTP and MCP request paths"}
    except (OSError, sqlite3.Error, ValueError):
        return {"settings":ControlSettings(enabled=False).model_dump(), "available":False,
                "error":"Local control settings unavailable; normal optimization disabled.",
                "connection_verified":False, "scope":"updated local HTTP and MCP request paths"}


def effective_request(request, *, diagnostic=False):
    # Explicit developer tests are isolated from the global setting. No public
    # optimize request field or agent label grants this exception.
    if diagnostic:
        return request, "diagnostic"
    state = snapshot()
    if not state["available"]:
        return request.model_copy(update={"optimization_enabled":False}), "settings_unavailable"
    if not state["settings"]["enabled"]:
        return request.model_copy(update={"optimization_enabled":False}), "disabled"
    return request, "enabled" if request.optimization_enabled else "request_disabled"
