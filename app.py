import os

from textual.app import App
from textual.binding import Binding

import db
import campaign_manager as cm
from screens.dashboard import Dashboard


class DMApp(App):
    CSS_PATH = "dm.tcss"
    TITLE = "DM Tracker"
    SCREENS = {"dashboard": Dashboard}
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "quick_capture", "Quick Capture"),
    ]

    _active_session_id: int | None = None

    def on_mount(self):
        if not os.environ.get("DM_DB_PATH"):
            path = cm.ensure_default()
            db.set_db_path(path)
        db.init_db()
        self.push_screen("dashboard")

    def _resolve_session(self) -> int | None:
        if self._active_session_id is not None:
            if db.get_entity(self._active_session_id):
                return self._active_session_id
            self._active_session_id = None
        entity = db.latest_session()
        if entity:
            self._active_session_id = entity["id"]
            return entity["id"]
        return None

    def _get_combat_round(self) -> int | None:
        for screen in reversed(self.screen_stack):
            if type(screen).__name__ == "CombatTrackerScreen":
                try:
                    return screen.combat.get("round")
                except Exception:
                    pass
        return None

    def action_quick_capture(self):
        from screens.quick_capture import QuickCaptureModal
        session_id = self._resolve_session()
        round_num = self._get_combat_round()
        self.push_screen(
            QuickCaptureModal(session_id, round_num),
            callback=self._on_capture_result,
        )

    def _on_capture_result(self, result: dict | None):
        if result:
            saved = " + ".join(result["saved_to"])
            self.notify(f'Saved to {saved}', title="Captured")


def main():
    app = DMApp()
    app.run()


if __name__ == "__main__":
    main()
