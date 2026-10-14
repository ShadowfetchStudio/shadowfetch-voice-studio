# Shadowfetch Voice Studio and VoiceStudio

v0.3.0 is one desktop app. It keeps Shadowfetch's local cloning studio and adds the jobs people use VoiceStudio for: designing a voice from a description, dubbing a recording, dictation, transcription, and audiobook chapters.

| Job | Where it runs |
| --- | --- |
| Clone a voice, Speak, save audio | This app. Qwen3-TTS (and optional Chatterbox) on your GPU. |
| Design notes from a description | This app. A small local word list. No model, no network. |
| Dub cues, dictation, transcription | This app. Local faster-whisper, then Speak for the new audio. |
| Audiobook chapters | This app splits the script. Speak generates each chapter. |
| Speak a designed voice with OmniVoice and the other VoiceStudio engines | VoiceStudio's own API on this computer, if you start it. |

VoiceStudio is [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio), AGPL-3.0-only. Its source is not copied into this MIT tree.

```bash
scripts/fetch-voicestudio.sh      # git clone into third_party/VoiceStudio
scripts/run-voicestudio-api.sh    # API on 127.0.0.1:3900
```

Open **Studio → VoiceStudio**, check the address, then use **Design → Speak with VoiceStudio**. Plain HTTP is allowed only on localhost. Offline mode blocks a remote engine.

The VoiceStudio checkout needs its own Python environment before the API will stay up. Follow that project's setup (`bun run setup:api` from the VoiceStudio tree, or its documented `uv` flow). Model weights stay under VoiceStudio's own license notices, separate from this app's Qwen and Whisper downloads.
