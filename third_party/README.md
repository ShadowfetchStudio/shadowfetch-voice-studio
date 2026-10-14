# Third-party checkouts

`VoiceStudio/` is created by `scripts/fetch-voicestudio.sh`. It is the upstream
project at <https://github.com/debpalash/VoiceStudio>, licensed AGPL-3.0-only.
Do not relicense those files. Shadowfetch Voice Studio does not import them;
the Studio screen talks to VoiceStudio's local HTTP API.

The directory is gitignored so this repository stays MIT. Run the fetch script
when you want the engine source on disk.
