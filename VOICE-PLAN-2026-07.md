# Voice channel plan — 2026-07-08 (research-backed)

## Recommendation
Pilot **Twilio ConversationRelay**, wrapping the existing `chat_core.run_turn` behind ONE
FastAPI WebSocket, with **Deepgram (Arabic STT) + ElevenLabs (Arabic TTS)**, positioned
**after-hours** via call-forwarding from the client's existing e&/du line.

Why this specifically: we already own the brain (persona, booking slot-math, caller memory,
lead capture, handoff) and must keep Gemini for Gulf Arabic. ConversationRelay is the only
option where Twilio does ALL the hard real-time audio (STT, TTS, barge-in, μ-law transport,
endpointing) while our Gemini brain stays 100% ours and unchanged — pump transcribed text
into `run_turn`, return text. No audio DSP, lowest lock-in, cheapest managed path (~$0.08/min).
Vapi/Retell = easiest polished agent but 2-4x cost + more lock-in for orchestration we already
have. Gemini Live = cheapest audio + native barge-in BUT not native telephony and is
speech-to-speech (doesn't reuse our text+tools `run_turn`) — a v2 experiment, not the pilot.

## Per-minute cost (USD; AED at 3.6725)
| Stack | All-in USD/min | AED/min |
|---|---|---|
| Cheapest (Twilio Media Streams + own loop) | ~$0.03-0.045 | ~0.11-0.17 |
| **Recommended pilot (ConversationRelay + Deepgram + ElevenLabs, BYO Gemini)** | **~$0.08** | **~0.29** |
| Easiest (Vapi, BYO Gemini) | ~$0.15-0.33 | ~0.55-1.21 |
| Easiest alt (Retell, BYO Gemini) | ~$0.13-0.31 | ~0.48-1.14 |
Gemini 2.5 Flash: $0.30/1M in, $2.50/1M out. **Dominant unlisted cost = UAE telephony
(~10-25x US; inbound rates unpublished — get a written quote).**

## Arabic verdict
Keep **Gemini** for the brain (tops cross-dialect Arabic incl. Gulf). STT: **Deepgram Nova-3**
(ar-AE/SA/QA/KW; the CR default) or **ElevenLabs Scribe v2** (best code-switch, but not a CR
STT option). TTS: **ElevenLabs** (good Arabic; the CR option). NOTE: only **Azure** has true
dedicated Emirati voices (ar-AE-Fatima/Hamdan) but Azure TTS is NOT available in CR — a
Khaleeji-voice-demanding client is the one reason to prefer Vapi/Retell (which can use Azure).
AVOID for Gulf: Google TTS (MSA-only, no ar-AE), OpenAI Realtime/Whisper (transcribes Arabic
as English).

## UAE (+971) numbers — the messy part
TDRA restricts VoIP to licensed operators (e&/du); foreign +971 numbers are commercially sold
but **not clearly compliant**; local DIDs need a UAE trade license + establishment card and are
**not self-serve**. **For the pilot: forward the client's existing e&/du line** (conditional
forwarding: no-answer `*61*<n>#`, busy `*67*<n>#`) to the AI endpoint. TRAP: forwarding a UAE
line to a NON-UAE number bills the client international/min (AED 1-2+/min, can dwarf AI cost) —
terminate domestically.

## Smallest viable build (reuses run_turn; ~a few hundred lines, brain unchanged)
1. Twilio number Voice webhook → `POST /voice/incoming`.
2. TwiML: `<Connect><ConversationRelay url="wss://<app>/voice/relay"
   transcriptionProvider="Deepgram" language="ar-AE" ttsProvider="ElevenLabs" interruptible="any"
   interruptSensitivity="high" welcomeGreeting="…"/></Connect>`; pass business_id via dialed `To`.
3. WebSocket `/voice/relay`: on `setup` resolve business_id from `To`, map caller `From` →
   conversation_id via existing caller memory; on `prompt` (final transcript) call
   `run_turn(business_id, conversation_id, text, schedule)` and return the reply as `text`
   tokens (tools already execute inside run_turn); on `interrupt` trim history via
   `utteranceUntilInterrupt`; handoff tool → `<Dial>` the owner; call end → persist via lead path.
4. After-hours gating: client forwards their line after-hours, or TwiML checks open-hours.

## Traps
TDRA VoIP restriction (biggest); UAE-number KYC not self-serve; international-forward hidden
fee; UAE telephony 10-25x US (unpublished inbound); CR premium-TTS surcharge unconfirmed; CR
was public beta Dec 2024 (confirm GA + pricing); CR can't use Azure Emirati voices; expect
~1-1.5s voice-to-voice (cache the system prompt, trim history). Prior research holds:
after-hours/overflow ONLY (callers dislike AI for primary reception).

## Sequencing
Defer voice until the retention core (reminders, deposits, reviews — see
FEATURES-ROADMAP-2026-07.md) is banking. Voice is the only item that can consume a solo dev
whole; it's a quarter, not a sprint, and carries per-minute cost + on-call ops.
