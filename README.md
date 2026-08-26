# ZBRANO for Home Assistant

This is the public Home Assistant installation and update repository for ZBRANO.
The application is delivered as a prebuilt container image. The current repository
tree contains no application source. Legacy commits that were already public and
the initial thin-distribution branch remain as merge ancestry for Home Assistant
update compatibility; post-split source and build history remain private.

## Installation

1. In Home Assistant, open **Settings → Apps → App store**.
2. Open the repository menu and add:
   `https://github.com/RoyceGith/ZBRANO_HA_Assistant`
3. Select **ZBRANO**, install it, configure the required credentials and entity
   permissions, then start the app.

Existing ZBRANO installations retain the same add-on slug, configuration, `/data`
storage, and `ghcr.io/roycegith/jarvis-ha-assistant` update image.
