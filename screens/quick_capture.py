"""Quick Capture overlay -- Ctrl+N from anywhere in the app."""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Static, ListView, ListItem
from textual.containers import Container, Horizontal
from textual import on

import db


def _append_note(entity_id: int, text: str) -> None:
    entity = db.get_entity(entity_id)
    if not entity:
        return
    existing = entity["notes"] or ""
    sep = "\n\n" if existing else ""
    db.update_entity(entity_id, entity["name"], dict(entity["fields"]), existing + sep + text)


class QuickCaptureModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss_screen", "Cancel"),
        Binding("tab", "show_tag", "Tag Entity"),
    ]

    def __init__(self, active_session_id: int | None, round_number: int | None):
        super().__init__()
        self._session_id = active_session_id
        self._round = round_number
        self._all_entities: list[dict] = []
        self._filtered_entities: list[dict] = []

    def compose(self) -> ComposeResult:
        round_badge = f"  [Round {self._round}]" if self._round else ""
        session_label = ""
        if self._session_id:
            e = db.get_entity(self._session_id)
            if e:
                session_label = f"  |  {e['name']}"
        no_session_warning = "" if self._session_id else "  [yellow](no session -- tag an entity to save)[/yellow]"

        yield Container(
            Static(
                f"[bold]Quick Capture[/bold]{round_badge}{session_label}{no_session_warning}",
                id="qc-header",
            ),
            Label("Note:"),
            Input(placeholder="What just happened?", id="qc-note"),
            Static("[dim]Tab: tag this note to an entity[/dim]", id="qc-tag-hint"),
            Label("Tag entity (optional):", id="qc-tag-label"),
            Input(placeholder="Filter by name...", id="qc-tag-input"),
            ListView(id="qc-entity-list"),
            Static("", id="qc-status"),
            Horizontal(
                Button("Save", id="btn-qc-save", variant="primary"),
                Button("Cancel", id="btn-qc-cancel"),
                id="qc-actions",
            ),
            id="qc-box",
        )

    def on_mount(self):
        self._all_entities = db.list_entities()
        self.query_one("#qc-tag-label").display = False
        self.query_one("#qc-tag-input").display = False
        self.query_one("#qc-entity-list").display = False
        self.query_one("#qc-note", Input).focus()

    def action_dismiss_screen(self):
        self.dismiss(None)

    def action_show_tag(self):
        tag_input = self.query_one("#qc-tag-input", Input)
        if not tag_input.display:
            self.query_one("#qc-tag-hint").display = False
            self.query_one("#qc-tag-label").display = True
            tag_input.display = True
            self.query_one("#qc-entity-list").display = True
            self._refresh_entity_list("")
            tag_input.focus()
        else:
            self.focus_next()

    @on(Input.Changed, "#qc-tag-input")
    def on_tag_filter_changed(self, event: Input.Changed):
        self._refresh_entity_list(event.value)

    @on(Input.Submitted, "#qc-note")
    def on_note_submitted(self, _event: Input.Submitted):
        self._do_save()

    @on(Input.Submitted, "#qc-tag-input")
    def on_tag_submitted(self, _event: Input.Submitted):
        self._do_save()

    def _refresh_entity_list(self, query: str):
        lv = self.query_one("#qc-entity-list", ListView)
        lv.clear()
        q = query.strip().lower()
        self._filtered_entities = [
            e for e in self._all_entities if not q or q in e["name"].lower()
        ][:10]
        for entity in self._filtered_entities:
            lv.append(ListItem(Label(f"{entity['name']} ({entity['type']})")))

    def _selected_entity(self) -> dict | None:
        lv = self.query_one("#qc-entity-list", ListView)
        if not lv.display:
            return None
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._filtered_entities):
            return self._filtered_entities[idx]
        if len(self._filtered_entities) == 1:
            return self._filtered_entities[0]
        return None

    def _do_save(self):
        note = self.query_one("#qc-note", Input).value.strip()
        if not note:
            self.query_one("#qc-status", Static).update("[red]Note can't be empty[/red]")
            self.query_one("#qc-note", Input).focus()
            return

        prefix = f"[Round {self._round}] " if self._round else ""
        full_note = prefix + note
        saved_to: list[str] = []

        if self._session_id:
            _append_note(self._session_id, full_note)
            saved_to.append("session")

        tagged = self._selected_entity()
        if tagged and tagged["id"] != self._session_id:
            _append_note(tagged["id"], full_note)
            saved_to.append(tagged["name"])

        if not saved_to:
            self.query_one("#qc-status", Static).update(
                "[yellow]No session found -- tag an entity to save this note[/yellow]"
            )
            return

        self.dismiss({"note": full_note, "saved_to": saved_to})

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-qc-save":
            self._do_save()
        elif event.button.id == "btn-qc-cancel":
            self.dismiss(None)
