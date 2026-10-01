# Professional voice cloning (ElevenLabs PVC class)

> **Quick path:** `docs/GUIDE.md` §3. After `prepare-voice`, **always run
> `python cli.py voice-prompt --voice <id>`**. Chatterbox only conditions on ~10 s of
> reference audio, so picking the cleanest 10 s matters more than total length. Listen to
> the audition clips it writes and override with `--start` if another sounds more like you.
> Prefer recording the narration yourself? Use `python cli.py voice-import` (GUIDE §3 Path B).

You asked for narration that sounds like **you**, not a generic robot voice
(edge-tts / system TTS). This project targets that with **local voice cloning**
via [Chatterbox](https://github.com/resemble-ai/chatterbox) (Resemble AI, **MIT**),
which is designed for zero-shot cloning from a short reference recording.

ElevenLabs **Professional Voice Cloning (PVC)** is a cloud fine-tune on a large
dataset of your voice. Local Chatterbox is **zero-shot** (no long cloud training),
but with a strong reference pack it is the closest free/commercial-safe path and
has scored competitively vs ElevenLabs in public blind tests.

---

## How ElevenLabs PVC works (reference)

From ElevenLabs docs and guides:

| Item | PVC guidance |
|---|---|
| Minimum audio | ~**30 minutes** clean speech |
| Sweet spot | **1–3 hours** |
| Format | High quality, consistent mic/room |
| Content | Natural reading, varied sentences, target language |
| Avoid | Music beds, reverb, multi-speaker, heavy EQ/compression |
| Plan | Creator tier or above for PVC API/product |
| Also | Instant Voice Cloning (IVC) needs far less audio but is lower fidelity than PVC |

PVC is a **trained voice model** on their servers. You cannot export that model
into this repo. What you *can* do:

1. **Local pro path (recommended here):** Chatterbox + your reference audio (free, MIT).
2. **Paid cloud path:** Keep using ElevenLabs PVC `voice_id` via `voice.engine: elevenlabs`.

---

## What we need from you (local pro clone)

### Must have

1. **Your own voice recordings** (consent: only clone a voice you own/control).
2. **Clean audio** — quiet room, no music, single speaker, steady mic distance.
3. **Enough duration:**

| Tier | Duration | Expectation |
|---|---|---|
| Too short | under 8s | Unstable / “AI” artifacts |
| Minimal | 10–20s | Recognizable but uneven |
| Good (target) | **30–90 seconds** continuous clean speech | Natural YouTube narration for most people |
| Strong | **2–5 minutes** (one or multiple files) | More consistent prosody |
| PVC-like coverage | **30+ minutes** multi-file pack | Best local stability (still zero-shot, not a PVC fine-tune) |

4. **Hardware:** GPU strongly recommended (CUDA or Apple Silicon). CPU works but is slow.

### Nice to have

- 2–6 separate takes (neutral explainer, slightly energetic, slower technical reading)
- 48 kHz or 44.1 kHz WAV/FLAC preferred (MP3 OK if high bitrate)
- Same microphone for all takes
- Spoken content in the language you will narrate (usually English)

### Do not send

- Other people’s voices without rights
- Podcasts with music/laugh tracks
- Phone recordings next to a fan/AC
- Heavily processed “radio voice” FX

---

## Setup (one time)

```bash
# 1) Install Chatterbox (when your environment is ready)
pip install chatterbox-tts
# if that fails, follow https://github.com/resemble-ai/chatterbox

# 2) Prepare your voice profile from clean recordings
python cli.py prepare-voice --voice mohit \
  --audio ~/Recordings/me_take1.wav \
  --audio ~/Recordings/me_take2.wav \
  --name "Mohit" \
  --consent

# 3) Point config at cloning engine
# config.yaml:
#   voice:
#     engine: chatterbox
#     default_voice: mohit
```

This writes:

```
modules/voice/voices/mohit/
  profile.json
  reference.wav          # normalized mono clone prompt
  samples/sample_01.wav
  consent.txt
```

### Generate with your clone

```bash
python cli.py run --topic "Rust async" --voice mohit --from-stage voice
# or with imported slides:
python cli.py run --project 2026-07-09_my-deck --voice mohit --from-stage voice
```

---

## Quality tips (biggest wins)

1. **Speaker notes quality** matters as much as the clone. Write natural spoken sentences
   in the PPT notes pane (not bullet shorthand).
2. **Sentence length:** 1–3 sentences per breath; avoid walls of text in one slide note.
3. **Reference content:** read a varied paragraph (questions, lists, calm explanation).
4. **One acoustic environment** for all training samples.
5. If clone sounds flat, re-record a more expressive 45s sample; re-run `prepare-voice`.
6. Prefer `chatterbox` over `edge_tts` / `mac_say` for anything you would publish.

---

## Optional: ElevenLabs PVC still available

If you subscribe to ElevenLabs Creator+ and create a PVC in their UI:

```yaml
voice:
  engine: elevenlabs
  default_voice: YOUR_PVC_VOICE_ID
```

```bash
export ELEVENLABS_API_KEY=...
python cli.py run --project ... --voice YOUR_PVC_VOICE_ID --from-stage voice
```

---

## Honesty bar

| Approach | Sounds like you? | Cost | Needs from you |
|---|---|---|---|
| edge-tts / mac_say | No (generic) | Free | Nothing |
| Chatterbox + 10s ref | Somewhat | Free + GPU | Short clip |
| Chatterbox + 30–90s clean ref | Yes, strong | Free + GPU | Good recordings |
| Chatterbox + multi-minute pack | Closest local | Free + GPU | Studio-ish audio |
| ElevenLabs PVC (1–3h) | Best cloud PVC | Paid | Long clean corpus + plan |

**Default production recommendation for this repo:**  
`voice.engine: chatterbox` + `prepare-voice` with **at least 30–60 seconds** of your clean speech.
