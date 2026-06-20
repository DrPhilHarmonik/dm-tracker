import json

import yaml
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Label, Button, DataTable, Input, Select, TextArea, Static, ListView, ListItem, TabbedContent, TabPane, Switch
from textual.screen import Screen, ModalScreen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual import on
from rich.text import Text
from pathlib import Path

import db
import export as exp
import sheet as shm
import dice
import combat as cbt
import effects as fx
import classes
from models import ENTITY_TYPES, ENTITY_LABELS, ENTITY_LABELS_PLURAL, ENTITY_SCHEMAS, RELATIONSHIP_TYPES

PALETTE = {
    "npc":        "#c792ea",
    "adventurer": "#89ddff",
    "enemy":      "#ff5370",
    "location":   "#c3e88d",
    "quest":      "#ffcb6b",
    "faction":    "#f78c6c",
    "item":       "#82aaff",
    "session":    "#b2ccd6",
    "encounter":  "#f07178",
}


class DismissableScreen(Screen):
    """Screen base for the common 'Escape to go back' binding.

    Plain app.pop_screen() silently discards any callback registered via
    push_screen(..., callback=...) without calling it -- only
    Screen.dismiss() actually invokes it. Screens that need their caller to
    refresh on return must dismiss(), not pop_screen(), so this is the
    binding target every such screen should use instead.
    """

    def action_dismiss_screen(self):
        self.dismiss()


def schema_choices(entity_type: str, key: str) -> list[str]:
    for field_key, _, _, choices in ENTITY_SCHEMAS.get(entity_type, []):
        if field_key == key:
            return choices or []
    return []


def format_io_error(ex: Exception) -> str:
    """Categorize export/import/backup failures into a clearer UI message.

    json.JSONDecodeError is a ValueError subclass, so it's checked first;
    the permission/missing-path/directory cases are all OSError subclasses
    and likewise need to come before the generic OSError fallback.
    """
    if isinstance(ex, json.JSONDecodeError):
        return f"Could not parse JSON: {ex}"
    if isinstance(ex, yaml.YAMLError):
        return f"Could not parse vault YAML frontmatter: {ex}"
    if isinstance(ex, PermissionError):
        return f"Permission denied: {ex.filename or ex}"
    if isinstance(ex, FileNotFoundError):
        return f"Path not found: {ex.filename or ex}"
    if isinstance(ex, IsADirectoryError):
        return f"Expected a file but found a directory: {ex.filename or ex}"
    if isinstance(ex, NotADirectoryError):
        return f"Expected a directory but found a file: {ex.filename or ex}"
    if isinstance(ex, ValueError):
        return f"Validation error: {ex}"
    if isinstance(ex, OSError):
        return f"Filesystem error: {ex}"
    return f"Unexpected error: {ex}"
