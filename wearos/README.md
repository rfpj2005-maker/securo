# Securo — Wear OS companion (Galaxy Watch)

Native Kotlin/Jetpack-Compose-for-Wear-OS app talking to the same
FastAPI backend the web app uses. Separate Gradle project from
`backend/`/`frontend/` — see `SETUP.md` for how to build and install it
(nothing here has been build-tested; there's no Android toolchain in the
environment this was written from).

## Status: Phase 1

- `app/` — pairing (6-digit code, see backend `app/api/watch_pairing.py`),
  Tasks (list + complete), Calendar (agenda, read-only).
- `watchface/` — simple digital face, time + date, no complications.

## Not built yet

- Siprov by voice (Android `SpeechRecognizer`/`TextToSpeech` around the
  existing SSE chat endpoint, `backend/app/agents/api/chat.py`).
- General AI assistant chat (same mechanism, different agent).
- Meeting recording (`MediaRecorder` → multipart upload to
  `POST /api/meetings`).

Each of these was scoped during planning but deliberately left out of
Phase 1 so pairing + the simplest data round-trip could be proven working
on real hardware first.

## Known open question

Whether the watch can actually reach the backend's Tailscale hostname
(`ServerSettings.baseUrl`, defaults to the same URL the web app uses)
depends on how Wear OS routes network traffic when off Wi-Fi — via the
paired phone's Bluetooth relay, it may or may not carry the phone's
Tailscale VPN routing. Untested; this is the first thing to verify once
pairing works, before investing in more screens.
