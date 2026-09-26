# Handoff — Voice, part 1: Telegram voice in/out (DONE 2026-09-26)

## Setup (CT101 Hermes; backup config.yaml.before-voice-*)
- Speech-to-text: faster-whisper 1.2.1 installed into the Hermes venv with /root/.hermes/bin/uv
  (**re-install after Hermes updates**, like the Opus 5.5 patch). stt: local model "base" (CPU), language auto,
  initial_prompt with names (Felo, Dogo Group, Lucas Osorio, Zubaloop, Odalyake, THE REBUILD, Daniel Tamayo).
  Test: 6-second notes in ~9 s, Spanish and English correct ("small" = 3x slower, barely better).
- Text-to-speech: tts.provider edge (free Microsoft neural voice; the text goes to Microsoft's speech service),
  voice en-US-AvaMultilingualNeural (speaks English and Spanish). ElevenLabs later (needs Daniel's key).
- voice.auto_tts: true — a voice note from Daniel gets a voice-note answer.
- tts toolset enabled for telegram and cron platforms.
- Morning briefing prompt: adds a spoken version (<= 45 s) via text_to_speech; the tool's [[audio_as_voice]] + MEDIA lines
  make Telegram show a voice bubble.
- Test voice message sent to Daniel's Telegram (hermes send, ogg/opus).

## HQ (Felo app) voice today
- Mic button already works in Chrome/Edge (browser speech recognition); replies are spoken with the browser's own voice
  (Settings → Sound and Voice). Part 2 (next): same natural voice (Ava) in HQ via a small TTS sidecar on box 100.
