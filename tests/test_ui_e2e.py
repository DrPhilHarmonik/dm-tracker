"""One continuous happy-path session through the real DMApp, covering every
core workflow in sequence: create an adventurer via the wizard, assign sheet
values, roll dice, apply an effect, run a combat round, and export a vault.
Each step's assertions check that the *previous* steps' state actually
carried through, not just that the current step didn't crash.
"""
import asyncio

import db
from app import DMApp


def test_full_happy_path_session(monkeypatch, tmp_path):
    monkeypatch.setenv("DM_DB_PATH", str(tmp_path / "campaign.db"))
    db.init_db()

    async def scenario():
        app = DMApp()
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()

            # 1. Create an adventurer via the quick wizard.
            await pilot.press("a")
            await pilot.pause()
            list_screen = app.screen
            list_screen.action_wizard("quick")
            await pilot.pause()
            wiz = app.screen
            wiz.query_one("#wiz-name").value = "Mira Thorn"
            wiz.query_one("#wiz-alignment").value = "Chaotic Good"
            await wiz._go_next()
            await pilot.pause()
            wiz.query_one("#wiz-level").value = "5"
            await wiz._go_next()
            await pilot.pause()
            await wiz._go_next()  # accept the default Standard Array
            await pilot.pause()
            review = app.screen
            await review._go_next()
            await pilot.pause()

            adv_id = db.list_entities("adventurer")[0]["id"]
            assert db.get_entity(adv_id)["name"] == "Mira Thorn"
            cs = app.screen  # quick mode lands on the Character Sheet

            # 2. Assign sheet values.
            cs.query_one("#sheet-ac").value = "16"
            cs.query_one("#sheet-hp-max").value = "40"
            cs.query_one("#sheet-hp-current").value = "40"
            cs.action_save()
            await pilot.pause()
            saved_sheet = db.get_entity(adv_id)["fields"]["sheet"]
            assert saved_sheet["ac"] == 16 and saved_sheet["hp_max"] == 40

            # 3. Roll dice -- confirm it uses the sheet we just saved.
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            detail = app.screen
            detail.action_open_roll()
            await pilot.pause()
            roll_screen = app.screen
            roll_screen.query_one("#btn-roll-ability-check").press()
            await pilot.pause()
            assert "Strength Check" in str(roll_screen.query_one("#roll-result").content)
            await pilot.press("escape")
            await pilot.pause()

            # 4. Apply an effect and confirm it shows on the detail screen.
            detail.action_open_effects()
            await pilot.pause()
            fxscreen = app.screen
            fxscreen.query_one("#input-effect-source").value = "Potion of Speed"
            fxscreen.query_one("#sel-effect-stat").value = "dex"
            fxscreen.query_one("#input-effect-modifier").value = "2"
            fxscreen.query_one("#btn-add-effect").press()
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert "Potion of Speed" in detail.query_one("#detail-body").content

            # 5. Run a combat round and confirm the sheet values + effect
            #    carry into the roster summary.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            enc_list = app.screen
            enc_list.action_add()
            await pilot.pause()
            enc_form = app.screen
            enc_form.query_one("#field-name").value = "Tavern Brawl"
            enc_form.action_save()
            await pilot.pause()
            table = app.screen.query_one("#entity-table")
            table.move_cursor(row=0)
            await pilot.pause()
            app.screen.action_open_selected()
            await pilot.pause()
            app.screen.action_open_combat()
            await pilot.pause()
            combat_screen = app.screen
            combat_screen.query_one("#sel-add-combatant").value = str(adv_id)
            combat_screen.query_one("#btn-add-combatant").press()
            await pilot.pause()
            combat_screen.query_one("#btn-start-encounter").press()
            await pilot.pause()
            combat_screen.query_one("#btn-next-round").press()
            await pilot.pause()
            summary = str(combat_screen.query_one("#combat-summary").content)
            assert "HP 40/40" in summary
            assert "AC 16" in summary
            assert "Round 2" in summary

            # 6. Export a vault and confirm the file reflects everything above.
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            app.screen.action_export()
            await pilot.pause()
            export_screen = app.screen
            vault_dir = tmp_path / "vault"
            export_screen.query_one("#export-path").value = str(vault_dir)
            export_screen.query_one("#btn-export").press()
            await pilot.pause()
            assert "Exported 2 entities" in str(export_screen.query_one("#export-status").content)

            mira_md = (vault_dir / "Adventurer" / "Mira Thorn.md").read_text(encoding="utf-8")
            assert "ac: 16" in mira_md
            assert "hp_max: 40" in mira_md
            assert "Potion of Speed" in mira_md

    asyncio.run(scenario())
