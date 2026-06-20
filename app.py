from textual.app import App
from textual.binding import Binding

import db
from screens.dashboard import Dashboard


class DMApp(App):
    CSS_PATH = "dm.tcss"
    TITLE = "DM Tracker"
    SCREENS = {"dashboard": Dashboard}
    BINDINGS = [Binding("ctrl+q", "quit", "Quit")]

    def on_mount(self):
        db.init_db()
        self.push_screen("dashboard")


def main():
    app = DMApp()
    app.run()


if __name__ == "__main__":
    main()
