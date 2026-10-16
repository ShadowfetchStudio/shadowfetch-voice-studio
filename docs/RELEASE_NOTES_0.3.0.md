# Shadowfetch Voice Studio 0.3.0

This release is one desktop app. Speak still clones a voice with Qwen3-TTS. **Studio** adds the longer jobs, and a browser page now answers at the documented loopback address.

This file is the draft for the GitHub release. It is not a git tag.

## Studio workspace (from #3)

The main window is **Speak | Studio | Voices**. Studio covers:

- **Design** — describe a voice in plain language. A local word list maps the description. No model download.
- **Dub** — transcribe a recording into timed lines, edit them, and open the script in Speak.
- **Dictate** — record with the microphone and turn it into text with local Whisper.
- **Transcribe** — turn an audio file into text without leaving Studio.
- **Audiobook** — split a script on Chapter, Part, or Markdown headings, then open a chapter in Speak.
- **VoiceStudio** — optional separate engine on this computer.

Worker methods: `studio.catalog`, `studio.design`, `studio.chapters`, `studio.dub_cues`, `studio.script`, `studio.voicestudio.status`, `studio.voicestudio.speak`.

## VoiceStudio bridge (from #3)

[VoiceStudio](https://github.com/debpalash/VoiceStudio) stays AGPL-3.0-only. This MIT tree does not vendor its Python. The app talks to it over loopback HTTP when you start it.

- Loopback `http://` is allowed. Remote plain HTTP is refused. Offline mode blocks a remote engine. A down server is a status result, not a crash.
- `scripts/fetch-voicestudio.sh` clones VoiceStudio into gitignored `third_party/VoiceStudio/`.
- `scripts/run-voicestudio-api.sh` starts VoiceStudio's own API (`python -m backend.main` with `OMNIVOICE_PORT`).

See [VOICESTUDIO.md](VOICESTUDIO.md). Shadowfetch Voice Studio stays MIT.

## Studio page at http://127.0.0.1:3900/ (from #4)

`http://127.0.0.1:3900/` used to return nothing, or VoiceStudio's API redirected a browser away from `/` when its frontend build was missing.

- `scripts/serve-studio.sh` serves this app's Studio page on `127.0.0.1:3900`. `GET /` is HTML and does not redirect. `/health` stays JSON.
- Design and chapter splitting run in this process.
- VoiceStudio's speech API, when you start it, listens on `127.0.0.1:3901`. The page forwards `POST /v1/audio/speech` only to that loopback process.
- The desktop **Studio → VoiceStudio** tab still defaults to `http://127.0.0.1:3900`. If the Studio page is open and the engine is not, status says so instead of treating the page as a ready speech engine. You can point the desktop at port 3901 directly.

```bash
chmod +x scripts/serve-studio.sh scripts/fetch-voicestudio.sh scripts/run-voicestudio-api.sh
scripts/serve-studio.sh                 # http://127.0.0.1:3900/
scripts/fetch-voicestudio.sh
scripts/run-voicestudio-api.sh          # http://127.0.0.1:3901/
```

## Version

0.3.0 in the worker, frontend package, and Tauri config.

## Not in this tag

A GitHub release and `v0.3.0` tag are not created with this draft.
