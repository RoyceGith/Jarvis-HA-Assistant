import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis/app"
MAIN = (APP / "main.py").read_text(encoding="utf-8")
CONTACTS = (APP / "domains/contacts.py").read_text(encoding="utf-8")
GOOGLE = (APP / "domains/google_contacts.py").read_text(encoding="utf-8")
OAUTH = (APP / "services/google_oauth.py").read_text(encoding="utf-8")
INTENTS = (APP / "services/calendar_intents.py").read_text(encoding="utf-8")
HTML = (APP / "static/index.html").read_text(encoding="utf-8")
SCRIPT = (APP / "static/js/contacts.js").read_text(encoding="utf-8")
STYLES = (APP / "static/css/contacts.css").read_text(encoding="utf-8")
MANIFEST = json.loads((ROOT / "jarvis/release_manifest.json").read_text(encoding="utf-8"))


class ContactsReleaseTests(unittest.TestCase):
    def test_release_markers_are_aligned(self):
        self.assertIn('version="0.13.147"', MAIN)
        self.assertIn("HUD 0.13.147", HTML)
        self.assertEqual(MANIFEST["version"], "0.13.147")

    def test_local_contacts_crud_import_and_backup_are_wired(self):
        for marker in ("def contacts_store", "def create_contact", "def update_contact", "def delete_contact", "def import_contacts"):
            self.assertIn(marker, CONTACTS)
        for route in ('@app.get("/api/contacts")', '@app.post("/api/contacts")', '@app.put("/api/contacts/{contact_id}")', '@app.post("/api/contacts/import")'):
            self.assertIn(route, MAIN)
        self.assertIn('"contacts": contacts_store()', MAIN)

    def test_birthdays_and_contacts_share_stable_links(self):
        self.assertIn("def sync_contact_from_birthday", CONTACTS)
        self.assertIn("def reconcile_birthday_contacts", CONTACTS)
        self.assertIn('contact["birthday_id"]', CONTACTS)
        self.assertIn("contact_birthday_changed_fn=sync_contact_from_birthday", MAIN)

    def test_google_contacts_uses_explicit_read_only_oauth(self):
        self.assertIn("contacts.readonly", GOOGLE)
        self.assertIn("def import_google_contacts", GOOGLE)
        self.assertIn("validate_google_contacts_oauth_grant", OAUTH)
        self.assertIn('"contacts" if str(catalog_id) == "google-people-official"', MAIN)
        self.assertIn("Google People API is disabled", GOOGLE)
        self.assertIn("skipped_reasons", GOOGLE)
        self.assertIn("except (RuntimeError, httpx.HTTPError)", MAIN)

    def test_contacts_tab_and_sensitive_data_boundary_are_present(self):
        for marker in ('id="contacts-tab"', 'id="contacts-panel"', 'id="contacts-import-file"', 'id="google-contacts-import"', 'id="contacts-layout"'):
            self.assertIn(marker, HTML)
        self.assertIn("include_sensitive=true", SCRIPT)
        self.assertIn(".contacts-shell", STYLES)
        self.assertIn('localStorage.getItem("zbrano-contacts-layout")', SCRIPT)
        self.assertIn('#contacts-panel{padding:0;overflow:hidden}', STYLES)
        self.assertIn('.contacts-content{min-width:0;min-height:0', STYLES)

    def test_chat_requires_numbered_identity_disambiguation(self):
        self.assertIn("prefix every option with a number", MAIN)
        self.assertIn("show every plausible match as a numbered list", INTENTS)
        self.assertIn('"name": "list_contacts"', MAIN)
        self.assertIn('"name": "save_contact"', MAIN)

    def test_contacts_follows_calendar_in_primary_navigation(self):
        self.assertLess(HTML.index('id="calendar-tab"'), HTML.index('id="contacts-tab"'))


if __name__ == "__main__":
    unittest.main()
