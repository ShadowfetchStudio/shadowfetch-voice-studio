# Third-party checkouts

`VoiceStudio/` is created by `scripts/fetch-voicestudio.sh`. It is the upstream
project at <https://github.com/debpalash/VoiceStudio>, licensed AGPL-3.0-only.
Do not relicense those files. Shadowfetch Voice Studio does not import them;
the Studio screen talks to VoiceStudio's local HTTP API on `127.0.0.1:3901`.
The Studio page at `http://127.0.0.1:3900/` (`scripts/serve-studio.sh`) is this
app and forwards speech to that address.

The directory is gitignored so this repository stays MIT. Run the fetch script
when you want the engine source on disk.
