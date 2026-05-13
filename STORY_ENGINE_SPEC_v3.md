# Story Engine — v3 FINAL Spec
### One girl's stories → cartoon episodes → 10 Indian languages
**May 2026 | Python/Flask | SQLite | Sarvam from VaidyaBot**

---

## 0. North Star

Paste a story → app generates a cartoon episode folder →
20 mins in CapCut → upload English + 9 Indian language versions.

---

## 1. Pre-Flight Checklist (Do This Before Opening Cursor)

- [ ] `winget install ffmpeg` in a terminal — only external install needed
- [ ] Place her 6+ anime images in `story-engine/assets/narrator/`
      Required filenames: `front.png`, `three_quarter.png`, `side.png`,
      `back.png`, `face_closeup.png`, `full_body.png`
      (extra images can sit alongside — only these 6 are used)
- [ ] Populate `.env` (see Section 2)
- [ ] Add ₹500 to Sarvam account
- [ ] Add $20 to OpenRouter account
- [ ] Test Sarvam Dub API access with one short audio file before building dubAgent

---

## 2. Environment Variables (.env)

```env
# ── API Keys ──────────────────────────────────────────
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
SARVAM_API_KEY=                    # same key as VaidyaBot

# ── Sarvam endpoints (same as VaidyaBot) ──────────────
SARVAM_STT_ENDPOINT=https://api.sarvam.ai/speech-to-text
SARVAM_TTS_ENDPOINT=https://api.sarvam.ai/text-to-speech
SARVAM_DUB_ENDPOINT=https://api.sarvam.ai/dubbing       # confirm on Day 1

# ── Narrator (set once, never change) ─────────────────
NARRATOR_NAME=                     # her character's name e.g. Aanya
NARRATOR_VOICE=anand               # Bulbul V3 voice — test before locking
NARRATOR_PACE=0.85                 # slightly slower, better for kids

# ── Channel identity (set once, never change) ──────────
# This is the visual DNA of the channel. Do not edit between episodes.
ART_STYLE=soft watercolour illustration, warm pastel colours, Studio Ghibli inspired, child-friendly, clean outlines, gentle lighting, no scary elements, no photorealism, storybook aesthetic, bright warm backgrounds

# ── Distribution ──────────────────────────────────────
DUB_LANGUAGES=hi-IN,ta-IN,te-IN,bn-IN,kn-IN,ml-IN,mr-IN,gu-IN,pa-IN

# ── Safety ────────────────────────────────────────────
MAX_SPEND_PER_EPISODE_USD=6.00

# ── Output ────────────────────────────────────────────
OUTPUT_DIR=C:\StoryEngine\episodes
```

---

## 3. Tech Stack

```
Python 3.11        already in C:\VaidyaBot\.venv — confirmed working
Flask              already in requirements.txt
sqlite3            Python stdlib — confirmed working (v3.45.1)
requests           already in requirements.txt
python-dotenv      already in requirements.txt
concurrent.futures Python stdlib — used for job parallelism
subprocess         Python stdlib — used for ffmpeg calls

React + Vite       frontend at localhost:3000
Flask              backend at localhost:5000
```

**Nothing new to install except ffmpeg.**

---

## 4. What Copies Directly From VaidyaBot

| VaidyaBot file | Story Engine destination | Action |
|---|---|---|
| `backend/voice/sarvam_stt.py` | `backend/voice/sarvam_stt.py` | Copy verbatim |
| `backend/logger/latency_logger.py` | `backend/logger/cost_logger.py` | Copy, rename stages (see Section 9) |
| `backend/main.py` | `backend/main.py` | Use as template — same Flask app factory pattern |
| `.cursorrules` | `.cursorrules` | Rewrite for Story Engine scope (Section 11) |
| `.env` structure | `.env` | Already compatible — same SARVAM_* var names |

**Do NOT copy:** Redis session logic, orchestrator, chunker, TTS streaming,
WhatsApp adapter, RAG — none of that applies here.

---

## 5. Folder Structure

```
story-engine/
├── .env
├── .cursorrules
├── requirements.txt
├── README.md
│
├── assets/
│   └── narrator/                  ← PUT HER IMAGES HERE BEFORE FIRST RUN
│       ├── front.png
│       ├── three_quarter.png
│       ├── side.png
│       ├── back.png
│       ├── face_closeup.png
│       └── full_body.png
│
├── backend/
│   ├── main.py                    ← Flask app factory (copy VaidyaBot pattern)
│   ├── db.py                      ← SQLite setup + all queries
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── script_agent.py        ← Claude: story → shot list JSON
│   │   ├── image_agent.py         ← OpenRouter image gen
│   │   ├── video_agent.py         ← OpenRouter video gen + async polling
│   │   ├── voice_agent.py         ← Sarvam TTS (Bulbul V3)
│   │   └── dub_agent.py           ← Sarvam Dub + ffmpeg mux
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── episodes.py            ← POST /api/episodes, GET /api/episodes
│   │   ├── shots.py               ← PATCH /api/shots/:id, POST /api/shots/:id/retry
│   │   └── characters.py          ← GET/POST /api/characters
│   │
│   ├── voice/
│   │   ├── sarvam_stt.py          ← COPIED FROM VAIDYABOT (verbatim)
│   │   └── __init__.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py      ← resolves [STYLE] and [CHAR:x] tokens
│   │   ├── job_queue.py           ← ThreadPoolExecutor, max 8 workers
│   │   ├── file_writer.py         ← download URLs → disk
│   │   ├── cost_estimator.py      ← estimate USD from shot list before generating
│   │   └── assembler.py           ← writes EDIT_ORDER.txt + episode_data.json
│   │
│   └── logger/
│       ├── __init__.py
│       └── cost_logger.py         ← adapted from VaidyaBot latency_logger
│
├── frontend/
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── screens/
│       │   ├── Home.jsx
│       │   ├── NewEpisode.jsx
│       │   ├── ShotReview.jsx
│       │   ├── Production.jsx
│       │   └── Complete.jsx
│       └── components/
│           ├── ShotCard.jsx
│           ├── CostEstimate.jsx
│           ├── JobProgress.jsx
│           └── CharacterCard.jsx
│
└── logs/
    ├── .gitkeep
    └── costs.jsonl                ← per-job cost log (never committed)
```

---

## 6. Database Schema (SQLite — db.py)

`sqlite3` from stdlib. One `.db` file at project root: `story_engine.db`.
Created automatically on first run.

```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id                   TEXT PRIMARY KEY,
    title                TEXT,
    raw_story            TEXT,
    status               TEXT DEFAULT 'draft',
    -- draft → scripted → approved → generating → assembling → dubbing → done
    estimated_cost_usd   REAL,
    actual_cost_usd      REAL DEFAULT 0.0,
    created_at           INTEGER
);

CREATE TABLE IF NOT EXISTS shots (
    id                   TEXT PRIMARY KEY,
    episode_id           TEXT NOT NULL,
    sequence             INTEGER NOT NULL,
    description          TEXT,
    image_prompt         TEXT,
    video_prompt         TEXT,
    model                TEXT,       -- seedance|kling|wan|veo-lite
    duration_sec         INTEGER,    -- 5, 6, 8, or 10
    dialogue             TEXT,       -- spoken line or NULL
    characters_used      TEXT,       -- JSON array: ["Dragon","Pip"]

    image_status         TEXT DEFAULT 'pending',
    image_url            TEXT,
    image_local_path     TEXT,

    video_job_id         TEXT,
    video_status         TEXT DEFAULT 'pending',
    -- pending → queued → running → done → failed
    video_local_path     TEXT,

    voice_status         TEXT DEFAULT 'pending',
    voice_local_path     TEXT,

    retry_count          INTEGER DEFAULT 0,
    error_msg            TEXT,

    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS characters (
    id               TEXT PRIMARY KEY,   -- slugified name: "purple-dragon"
    name             TEXT NOT NULL,
    description      TEXT,
    voice_speaker    TEXT,               -- Bulbul V3 voice name
    ref_images       TEXT,               -- JSON: {"front":"path","three_quarter":"path",...}
    episode_count    INTEGER DEFAULT 0,
    created_at       INTEGER
);

CREATE TABLE IF NOT EXISTS narration (
    id             TEXT PRIMARY KEY,
    episode_id     TEXT NOT NULL,
    position       TEXT NOT NULL,    -- 'intro' | 'outro'
    script         TEXT,
    voice_status   TEXT DEFAULT 'pending',
    local_path     TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS dubs (
    id             TEXT PRIMARY KEY,
    episode_id     TEXT NOT NULL,
    language_code  TEXT NOT NULL,
    status         TEXT DEFAULT 'pending',
    local_path     TEXT,
    error_msg      TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodes(id)
);

CREATE TABLE IF NOT EXISTS cost_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id   TEXT,
    service      TEXT,
    -- 'openrouter-image'|'openrouter-video'|'sarvam-tts'|'sarvam-dub'|'anthropic'
    amount_usd   REAL,
    logged_at    INTEGER
);
"""
```

Key db.py functions to build:
```python
def get_db() -> sqlite3.Connection   # returns conn with row_factory=sqlite3.Row
def init_db()                        # runs SCHEMA on first launch
def get_episode(episode_id)
def create_episode(id, title, raw_story) -> episode
def update_episode_status(episode_id, status)
def create_shots(episode_id, shots_list)
def update_shot(shot_id, **kwargs)
def get_shots(episode_id) -> list
def get_pending_video_jobs() -> list  # all shots with video_status='running'
def upsert_character(id, name, description, voice_speaker)
def get_character(character_id)
def get_all_characters() -> list
def create_narration(episode_id, position, script)
def update_narration(id, **kwargs)
def create_dubs(episode_id, language_codes)
def update_dub(id, **kwargs)
def log_cost(episode_id, service, amount_usd)
def get_episode_cost(episode_id) -> float
```

---

## 7. The Full Pipeline

### STEP 1 — Story Pasted

`POST /api/episodes/new`
Body: `{ "story": "Once there was a dragon..." }`

- Generate episode `id` as slugified first 5 words + timestamp
- Save `raw_story` to SQLite, status=`draft`
- Return episode_id

---

### STEP 2 — Claude Plans the Episode

`script_agent.py`

```python
def plan_episode(raw_story: str, existing_characters: list) -> dict:
    """
    Calls Claude API. Returns parsed JSON shot list.
    existing_characters: list of {name, description} from characters table
    — passed in so Claude knows which characters already exist.
    """
```

**System prompt** (hardcoded in `script_agent.py`, never in UI):

```
You are the creative director for a children's animated short film channel.

The show stars a 6-year-old Indian girl named {NARRATOR_NAME}. She narrates every
episode in warm, excited English. The show is made for children aged 3-8 across
India and the Indian diaspora.

Each episode is based on a story the real girl told. Turn it into a shot list.

RULES — NEVER BREAK THESE:
1. All content appropriate for ages 3-8. No exceptions.
2. Dark/scary/violent elements → transform gently.
   Monster → grumpy-but-friendly creature.
   Fight → misunderstanding that gets resolved.
   Death → never appears.
3. 6–12 shots per episode. No more. No less.
4. Each shot: 5–10 seconds screen time.
5. Shot 1: always a wide establishing shot of the setting.
6. Last shot: always warm and resolved. Everyone happy.
7. Dialogue: maximum 10 words per line. Short. Like a real child says it.
8. Use [STYLE] token in every image_prompt — do not write the style yourself.
9. Use [CHAR:name] token for every character reference in image_prompt.
10. {NARRATOR_NAME} never appears in scene shots — only in narrator scripts.

MODEL RULES — assign the right tool per shot type:
- "kling"     → action: running, jumping, flying, animals in fast motion
- "seedance"  → character focus: close-ups, reactions, talking, gentle movement
- "wan"       → environment: establishing shots, backgrounds, no character needed
- "veo-lite"  → magic only: max 2 per episode, for sparkles/VFX/transformations

EXISTING CHARACTERS (do not mark these as new):
{existing_characters_json}

RETURN ONLY VALID JSON. NO MARKDOWN. NO PREAMBLE.

{
  "episode_title": "string",
  "narrator_intro": "2-3 warm sentences, age 5-6 reading level",
  "narrator_outro": "2-3 sentences — lesson or warm feeling to leave with",
  "characters_needed": [
    {
      "name": "string",
      "is_new": true,
      "description": "physical look + personality, 2-3 sentences. Only if is_new:true."
    }
  ],
  "shots": [
    {
      "sequence": 1,
      "description": "one plain English sentence — for human review",
      "image_prompt": "[STYLE], detailed visual scene, [CHAR:name] for any character present",
      "video_prompt": "what moves, camera behaviour, duration note",
      "model": "wan|seedance|kling|veo-lite",
      "duration_sec": 5|6|8|10,
      "dialogue": "spoken line or null",
      "characters_used": ["name1"]
    }
  ]
}
```

On success:
- Save shots to SQLite
- Save narration rows (intro/outro) to SQLite
- Save any new characters (is_new:true) to SQLite with status `needs_images`
- Update episode status → `scripted`
- Return full shot list + cost estimate to frontend

---

### STEP 3 — Cost Estimation (cost_estimator.py)

Called immediately after Claude returns the shot list.
Shown on the Shot Review screen before any generation.

```python
# Approximate unit costs — update from OpenRouter pricing page
IMAGE_COST_USD     = 0.04   # per image (Gemini 2.5 Flash)
VIDEO_COSTS_USD    = {      # per second of video
    "seedance":  0.015,
    "kling":     0.05,
    "wan":       0.01,
    "veo-lite":  0.025,
}
SARVAM_TTS_USD     = 0.0002  # per narrator segment (negligible)
SARVAM_DUB_USD     = 0.012   # per language per minute of audio

def estimate(shot_list, new_characters, dub_language_count,
             episode_duration_sec) -> dict:
    """Returns itemised cost breakdown + total."""
```

---

### STEP 4 — Human Checkpoint (Shot Review Screen)

**Nothing has been generated. Nothing has been charged.**

Frontend displays:
- Episode title (editable inline)
- Cost breakdown card (itemised)
- Shot cards — each shows: sequence, description, model badge,
  duration, dialogue line if any
- NEW CHARACTER cards in amber — name, description, voice selector
- [✎ Edit] and [✕ Remove] on every shot card
- **[✅ Generate Episode — ~$X.XX]** — green if under MAX_SPEND,
  amber with warning if over

User clicks Generate → everything from here is fully autonomous.

`POST /api/episodes/:id/generate`

---

### STEP 5 — Generate Character Reference Images

`image_agent.py` — only for characters where `is_new: true`

```python
ANGLES = [
    ("front",          "facing camera, full body, neutral expression"),
    ("three_quarter",  "3/4 view, slight turn right, full body"),
    ("side",           "side profile, full body"),
    ("back",           "back view, full body"),
    ("face_closeup",   "face close-up, looking at camera, warm expression"),
    ("full_body_arms", "full body, arms slightly out, welcoming pose"),
]

def generate_character_images(character: dict) -> dict:
    """
    Fires 6 parallel requests via ThreadPoolExecutor.
    Each prompt: f"{ART_STYLE}, character model sheet, {character['description']},
                  {angle_description}, white background, clean illustration"
    Model: google/gemini-2.5-flash-image via OpenRouter
    Returns: {angle_name: local_path} for all 6 angles
    """
```

Narrator images are in `assets/narrator/` — never regenerated, never touched.

---

### STEP 6 — Generate Scene Images (First Frames)

One per shot. Parallel via `ThreadPoolExecutor`.

**prompt_builder.py** resolves tokens before each API call:

```python
def resolve_prompt(raw_prompt: str, characters: dict) -> dict:
    """
    Replaces [STYLE] with ART_STYLE env var.
    Replaces [CHAR:name] with the character's ref image paths
    — these are passed as input_references to the video API later.
    Returns: { "resolved_prompt": str, "char_refs": {name: [image_paths]} }
    """
```

OpenRouter image API call:
```python
POST https://openrouter.ai/api/v1/images/generations
Headers: { Authorization: f"Bearer {OPENROUTER_API_KEY}" }
Body: {
    "model": "google/gemini-2.5-flash-image",
    "prompt": resolved_prompt,
    "size": "1920x1080"
}
```

Download → `OUTPUT_DIR/{episode_id}/frames/{sequence:02d}-frame.png`

---

### STEP 7 — Generate Video Clips

`video_agent.py` — core of the pipeline.

```python
MODEL_MAP = {
    "seedance":  "bytedance/seedance-2.0",
    "kling":     "kuaishou/kling-3.0-pro",
    "wan":       "alibaba/wan-2.7",
    "veo-lite":  "google/veo-3.1-lite",
}

def submit_video_job(shot: dict, first_frame_url: str,
                     char_ref_urls: list) -> str:
    """
    Submits to OpenRouter POST /api/v1/videos.
    Writes job_id to SQLite immediately (before return).
    Returns job_id.
    """
    payload = {
        "model": MODEL_MAP[shot["model"]],
        "prompt": shot["video_prompt"],
        "frame_images": [{"frame_type": "first_frame", "url": first_frame_url}],
        "input_references": char_ref_urls,
        "duration": shot["duration_sec"],
        "aspect_ratio": "16:9",
        "resolution": "1080p",
    }
    # For Veo calls only: add personGeneration: dont_allow
    if shot["model"] == "veo-lite":
        payload["personGeneration"] = "dont_allow"

def poll_video_jobs(episode_id: str):
    """
    Polls all running jobs for this episode every 30 seconds.
    On complete: downloads MP4, updates SQLite.
    On failed: increments retry_count, auto-retries up to 2x.
    Runs in background thread — does not block the main Flask process.
    """
```

**Concurrency:** `ThreadPoolExecutor(max_workers=8)` — matches OpenRouter
safe concurrency limit.

**Resilience:** On app restart, `get_pending_video_jobs()` returns all rows
with `video_status IN ('running', 'queued')`. Polling resumes automatically
on startup. This is the reason SQLite exists — job IDs survive restarts.

**Output:** `OUTPUT_DIR/{episode_id}/clips/{sequence:02d}-{slug}.mp4`

---

### STEP 8 — Generate Voices (Sarvam Bulbul V3)

`voice_agent.py` — runs in parallel with video generation (not after).

Sarvam TTS API (confirmed from VaidyaBot api_contracts.md):
```python
POST https://api.sarvam.ai/text-to-speech
Headers: { "api-subscription-key": SARVAM_API_KEY }
Body: {
    "inputs": [text],
    "target_language_code": "en-IN",
    "speaker": speaker_name,       # from .env or character.voice_speaker
    "model": "bulbul:v3",
    "speech_sample_rate": 24000,
    "pace": pace,                  # 0.85 for narrator, 0.9 for characters
    "enable_preprocessing": True
}
# Response: { "audios": ["<base64 wav>"] }
# Decode base64 → write .wav file
```

**Known from VaidyaBot smoke test:**
- Rate limit: 20 req/min → add `time.sleep(3)` between calls if >5 voices
- Latency: ~3–4 seconds per call — not a bottleneck since it runs
  concurrently with 20–40 min video generation
- Empty string → 400 error — always validate before calling

**Three voice types generated:**

A. **Narrator intro** → `narration/intro.wav`
   Speaker: `NARRATOR_VOICE` from `.env`, pace: 0.85

B. **Narrator outro** → `narration/outro.wav`
   Same as intro

C. **Character dialogue** (each shot where `dialogue` is not null)
   → `voices/{sequence:02d}-{character_slug}-line.wav`
   Speaker: `character.voice_speaker` from characters table
   pace: 0.9

---

### STEP 9 — Assemble Output Folder

`assembler.py` — runs when all clips + voices are downloaded.

```
OUTPUT_DIR/{episode_id}/
├── EDIT_ORDER.txt
├── narration/
│   ├── intro.wav
│   └── outro.wav
├── clips/
│   ├── 01-meadow-wide.mp4
│   ├── 02-dragon-appears.mp4
│   └── ...
├── voices/
│   ├── 03-dragon-hello-line.wav
│   └── ...
├── frames/
│   └── (first-frame PNGs — for thumbnail selection)
├── languages/
│   └── (populated in Step 10)
└── episode_data.json
```

**EDIT_ORDER.txt** (example):
```
== THE DRAGON WHO COULDN'T SNEEZE ==

VIDEO TRACK (drag into CapCut in this order):
1.  narration/intro.wav          [play over title card / narrator image]
2.  clips/01-meadow-wide.mp4
3.  clips/02-dragon-appears.mp4
4.  clips/03-dragon-waves.mp4    VOICE → voices/03-dragon-hello-line.wav at 0:01
5.  clips/04-sneeze-fire.mp4
6.  clips/05-everyone-runs.mp4
7.  clips/06-dragon-sad.mp4
8.  clips/07-pip-walks-over.mp4  VOICE → voices/07-pip-kind-line.wav at 0:00
9.  clips/08-friends-laugh.mp4
10. clips/09-sunset-wide.mp4
11. narration/outro.wav          [play over final clip or end card]

MUSIC: YouTube Audio Library → search "children instrumental warm" → 20% under voices

ESTIMATED RUNTIME: ~2 min 20 sec
```

**episode_data.json** — full metadata, shot list, cost summary, character list.
Used for future reference and potential Phase 2 features.

---

### STEP 10 — Dub Into Indian Languages

`dub_agent.py` — triggered manually from Complete screen (one click).

```python
def dub_episode(episode_id: str, language_code: str,
                master_audio_path: str, master_transcript: str):
    """
    1. Call Sarvam Dub API with master audio + transcript
    2. Receive dubbed audio in target language
    3. ffmpeg mux: replace audio track on master video
    4. Generate YouTube metadata in that language (Claude call)
    5. Save to languages/{language_code}/
    """

# ffmpeg mux (subprocess call):
# ffmpeg -i master.mp4 -i dubbed_audio.wav
#        -c:v copy -map 0:v -map 1:a
#        -shortest languages/hi-IN/episode.mp4
```

**Output per language:**
```
languages/hi-IN/
    episode.mp4            ← same visuals, Hindi audio
    youtube_metadata.txt   ← Hindi title, description, tags
```

**YouTube metadata generation** (Claude call, ~$0.01 for all 9 languages):
```python
prompt = f"""
Generate YouTube metadata for a children's animated episode in {language_name}.
Episode title (English): {title}
Episode summary (English): {summary}

Return JSON only:
{{
  "title": "translated/localised title (max 60 chars)",
  "description": "2-3 sentence description in {language_name} (100-150 chars)",
  "tags": ["tag1", "tag2", ...] (8-10 relevant tags in {language_name})
}}
"""
```

**Sarvam Dub risk mitigation:**
- Test API access before building this module (see Pre-Flight checklist)
- Fallback if Dub API unavailable: Claude translates scripts → Bulbul V3
  TTS generates audio in target language directly. Same output, just loses
  voice-identity preservation. Still produces 9 upload-ready versions.

---

## 8. API Routes

```python
# Episodes
POST   /api/episodes/new              # paste story → create episode
GET    /api/episodes                  # list all episodes with status
GET    /api/episodes/:id              # full episode detail + shots
POST   /api/episodes/:id/generate     # start generation (after approval)
POST   /api/episodes/:id/dub          # trigger dubbing (after assembly)

# Shots (for Shot Review screen edits)
PATCH  /api/shots/:id                 # edit prompt/model/dialogue/duration
DELETE /api/shots/:id                 # remove shot from episode
POST   /api/shots/:id/retry           # manual retry of failed shot

# Characters
GET    /api/characters                # list all characters
POST   /api/characters                # add new character manually
GET    /api/characters/:id            # single character + ref images

# Status (polled by frontend every 10 seconds during generation)
GET    /api/episodes/:id/status       # returns shot-level statuses + cost so far

# Health
GET    /api/health
```

---

## 9. Cost Logger (adapted from VaidyaBot)

`backend/logger/cost_logger.py`

Copy `latency_logger.py` from VaidyaBot. Change:
- Log file: `logs/costs.jsonl`
- Stages: `image_gen`, `video_gen`, `tts`, `dub`, `claude`
  (remove: `stt`, `tts_first_byte`, `tts_complete`, `total`, `orchestrator`)
- Add: `episode_id` field to every record
- Keep: `estimated_cost_usd` field — same pattern

```python
def log_cost(episode_id: str, stage: str,
             amount_usd: float, model: str = None):
    """Append one cost line to logs/costs.jsonl."""

def get_episode_spend(episode_id: str) -> float:
    """Sum all cost_log rows for this episode_id."""
```

---

## 10. Frontend — Five Screens

### Screen 1: Home
```
┌──────────────────────────────────────────────┐
│  ✨ Story Engine              [Characters]    │
│                                               │
│  [+ New Episode]                              │
│                                               │
│  Episodes                                     │
│  ┌────────────────────────────────────────┐   │
│  │ 🟢 The Dragon Who Couldn't Sneeze      │   │
│  │    Done · 10 clips · $1.58 · 9 langs   │   │
│  │    [Open Folder]                        │   │
│  ├────────────────────────────────────────┤   │
│  │ 🟡 Pip and the Rainbow Cloud           │   │
│  │    Generating... 7/10 clips done       │   │
│  │    [Watch Progress]                     │   │
│  └────────────────────────────────────────┘   │
│                                               │
│  This month: 3 episodes · $4.21 spent         │
└──────────────────────────────────────────────┘
```

### Screen 2: New Episode
```
┌──────────────────────────────────────────────┐
│  ← Back      New Episode                     │
│                                               │
│  ┌──────────────────────────────────────────┐ │
│  │                                          │ │
│  │  Paste the story here...                 │ │
│  │                                          │ │
│  │  (Speak using Wispr Flow → copy → paste) │ │
│  │                                          │ │
│  └──────────────────────────────────────────┘ │
│                                               │
│           [✨ Turn Into Episode]              │
│                                               │
│  ── while loading ──                          │
│  "Reading the story... ✨"                    │
└──────────────────────────────────────────────┘
```

### Screen 3: Shot Review
```
┌──────────────────────────────────────────────┐
│  ← Back    The Dragon Who Couldn't Sneeze [✎] │
│                                               │
│  ┌── Cost Estimate ────────────────────────┐  │
│  │  Character images (1 new Dragon)  $0.24 │  │
│  │  Scene images (9 shots)            $0.36│  │
│  │  Video — Seedance (5 shots × 6s)   $0.45│  │
│  │  Video — Kling (3 shots × 6s)      $0.90│  │
│  │  Video — WAN (1 shot × 8s)         $0.08│  │
│  │  Voices + narration                $0.01│  │
│  │  Dubs × 9 languages                $0.09│  │
│  │  ─────────────────────────────────────  │  │
│  │  Total:                            $2.13│  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  NEW CHARACTER ──────────────────────────── │
│  🟠 Dragon · small purple dragon, big eyes   │
│     Voice: [kabir ▾]                         │
│                                               │
│  SHOTS ──────────────────────────────────── │
│  1 │🟢wan  │6s│ Wide sunny meadow, Pip plays  │
│  2 │🟠kling│5s│ Dragon flies in from clouds   │
│  3 │🔵seed │6s│ Dragon waves hello 💬"Hello!" │
│     [✎]  [✕]  on each card                   │
│  ...                                          │
│                                               │
│       [✅ Generate Episode — $2.13]           │
└──────────────────────────────────────────────┘
```

### Screen 4: Production Dashboard
```
┌──────────────────────────────────────────────┐
│  The Dragon Who Couldn't Sneeze               │
│  ████████████░░░░░░░  65%  ~11 min left       │
│                                               │
│  Characters ─────────────────────────────── │
│  Dragon    ✅ 6/6 images done                │
│                                               │
│  Narration ─────────────────────────────── │
│  Intro  🔊✅     Outro  🔊✅                 │
│                                               │
│  Clips ──────────────────────────────────── │
│  01 Meadow wide       🖼✅  🎬✅             │
│  02 Dragon flies in   🖼✅  🎬⏳ generating  │
│  03 Dragon waves      🖼✅  🎬⏳ queued  🔊✅│
│  04 Sneeze fire       🖼⏳  🎬⏳ waiting     │
│  05 Everyone runs     🖼⏳  🎬⏳ waiting     │
│  06 Dragon sad        🖼✅  🎬❌ failed [↺]  │
│  ...                                          │
│                                               │
│  Spent so far: $1.21                          │
└──────────────────────────────────────────────┘
```

### Screen 5: Complete
```
┌──────────────────────────────────────────────┐
│  ✅ The Dragon Who Couldn't Sneeze            │
│                                               │
│  [📁 Open Folder]  [📋 Copy Edit Order]       │
│                                               │
│  [thumbnail grid of 9 clips]                  │
│                                               │
│  ── Languages ─────────────────────────────  │
│  [▶ Dub into 9 languages — ~$0.09]            │
│                                               │
│  After dubbing:                               │
│  Hindi ✅  Tamil ✅  Telugu ⏳  Bengali ⏳    │
│  Kannada ⏳  Malayalam ⏳  ...                │
│                                               │
│  Total spent: $2.11                           │
│                                               │
│  [+ New Episode]                              │
└──────────────────────────────────────────────┘
```

---

## 11. .cursorrules for Story Engine

```
# Story Engine — Cursor Rules
# A personal short-film pipeline. One family. One girl's stories.
# Read before every Composer session.

## 1. WHAT THIS IS
A local Python/Flask app that turns a pasted story into a cartoon episode folder.
Single user. No authentication. No multi-tenancy. No cloud deployment.
Runs at localhost:5000 (backend) + localhost:3000 (frontend).

## 2. STACK — DO NOT DEVIATE
Backend:  Python 3.11, Flask, sqlite3 (stdlib), requests, concurrent.futures
Frontend: React + Vite
Database: SQLite — file: story_engine.db at project root
Queue:    ThreadPoolExecutor(max_workers=8) — no Celery, no Redis, no queuing library
Fonts:    No external CSS frameworks — plain CSS or Tailwind CDN only

## 3. WHAT IS HARDCODED (NEVER PUT IN UI)
- ART_STYLE (.env) — the channel's visual identity, never changes
- NARRATOR_NAME, NARRATOR_VOICE, NARRATOR_PACE (.env)
- DUB_LANGUAGES (.env)
- MODEL_MAP in video_agent.py — maps seedance/kling/wan/veo-lite to real model strings
- Claude system prompt in script_agent.py

## 4. COPY FROM VAIDYABOT — DO NOT REWRITE
- backend/voice/sarvam_stt.py → copy verbatim from C:\VaidyaBot\backend\voice\sarvam_stt.py
- backend/logger/cost_logger.py → adapt from C:\VaidyaBot\backend\logger\latency_logger.py
  Change stage names: image_gen, video_gen, tts, dub, claude
  Add episode_id field. Keep cost_usd pattern.

## 5. EXTERNAL API RULES
- All keys from .env only — never hardcode
- Every API wrapper: timeout, 1 retry on 5xx/timeout, structured error return
- Job IDs written to SQLite BEFORE the API call returns
- On app startup: resume polling all rows with video_status IN ('running','queued')

## 6. SARVAM TTS — KNOWN CONSTRAINTS (from VaidyaBot smoke tests)
- Rate limit: 20 req/min → add time.sleep(3) between calls if batching >5
- Response: { "audios": ["<base64 wav>"] } — decode base64, write .wav
- Empty string input → 400 error — validate before every call
- Latency: ~3-4 seconds per call — run concurrently with video generation

## 7. SQLITE RULES
- init_db() called on app startup — idempotent (CREATE TABLE IF NOT EXISTS)
- Row factory: sqlite3.Row on every connection (allows dict-style access)
- All db access through db.py functions — no raw SQL outside db.py
- Write job_id to SQLite before the API call, not after

## 8. COST GUARDRAIL
- estimate_cost() called after Claude returns shot list — before any generation
- If estimated cost > MAX_SPEND_PER_EPISODE_USD: warn in UI, do not block
- Log every API spend to cost_log table AND logs/costs.jsonl

## 9. FRONTEND POLLING
- Production dashboard polls GET /api/episodes/:id/status every 10 seconds
- Use SSE (Server-Sent Events) if available, fall back to setInterval polling
- Never poll faster than 10 seconds — OpenRouter job polling is 30s server-side

## 10. FILE OUTPUT
- All episode output to OUTPUT_DIR/{episode_id}/ (from .env)
- Narration: narration/intro.wav, narration/outro.wav
- Clips: clips/{sequence:02d}-{slug}.mp4
- Voices: voices/{sequence:02d}-{character}-line.wav
- Languages: languages/{lang-code}/episode.mp4
- Always write EDIT_ORDER.txt as last step of assembly

## 11. BUILD ONE THING AT A TIME
After completing each task, state which file was created or modified.
Do not scaffold future phases.
Do not create files not in the folder structure spec.
If a decision is ambiguous, state the assumption before proceeding.
```

---

## 12. Build Order for Cursor — 4 Sessions

### Session 1 (~3 hrs) — Data + Brain
1. `backend/db.py` — full schema + all query functions. Test with dummy data.
2. `backend/agents/script_agent.py` — Claude call + JSON parser.
   Test with: *"Once there was a small purple dragon who wanted to make friends"*
   Confirm JSON shape. Confirm [STYLE] and [CHAR:x] tokens appear.
3. `backend/utils/cost_estimator.py` — given shot list JSON → USD breakdown dict.
4. `backend/routes/episodes.py` — `POST /api/episodes/new` and `GET /api/episodes`.
5. `frontend ShotReview.jsx` — display shot list, cost breakdown, approve button.
   **No API calls fire yet. This screen is pure display.**
   ✅ Session 1 done when: paste story → see shot list + cost estimate on screen.

### Session 2 (~3 hrs) — Images + Queue
6. `backend/voice/sarvam_stt.py` — **copy from VaidyaBot verbatim**. No edits.
7. `backend/utils/prompt_builder.py` — [STYLE] and [CHAR:x] token resolution.
   Unit test with dummy character data before wiring to agents.
8. `backend/agents/image_agent.py` — single image call → file downloads correctly.
9. `backend/utils/job_queue.py` — ThreadPoolExecutor wrapper, max 8 workers.
10. `backend/utils/file_writer.py` — download URL → disk with correct path logic.
    ✅ Session 2 done when: one character generates 6 images, all downloaded.

### Session 3 (~3 hrs) — Video + Voice
11. `backend/agents/video_agent.py` — single Seedance shot, poll to completion,
    file downloads. Then add parallel submission for all shots.
    **Critical:** write job_id to SQLite before API call returns.
    **Critical:** on startup, resume polling pending jobs automatically.
12. `backend/agents/voice_agent.py` — narrator intro TTS → .wav downloaded.
    Then add character dialogue voices.
13. `backend/logger/cost_logger.py` — adapt from VaidyaBot, log every spend.
14. `backend/routes/episodes.py` — add `GET /api/episodes/:id/status` for polling.
15. `frontend Production.jsx` — live dashboard, polls status every 10s.
    ✅ Session 3 done when: full episode generates end-to-end, folder appears on disk.

### Session 4 (~2 hrs) — Dub + Polish
16. `backend/agents/dub_agent.py` — Sarvam Dub for one language, ffmpeg mux.
    Test Sarvam Dub API access first — if unavailable, build TTS fallback.
17. Loop dubbing across all DUB_LANGUAGES with YouTube metadata per language.
18. `backend/utils/assembler.py` — EDIT_ORDER.txt + episode_data.json.
19. `frontend Complete.jsx` — open folder button, dub trigger, language status.
20. End-to-end test: one complete 6-shot episode → full output folder →
    all language versions → open in CapCut and confirm EDIT_ORDER works.
    ✅ Session 4 done when: folder opens in CapCut and first edit takes under 20 mins.

**Total: ~11 hours across 4 sessions.**

---

## 13. Cost Per Episode

| Service | Detail | Cost |
|---|---|---|
| Claude — script gen | 1 call | ~$0.01 |
| OpenRouter images | 6 char ref + 10 scene frames | ~$0.64 |
| OpenRouter — Seedance (6 shots × 6s) | | ~$0.54 |
| OpenRouter — Kling Pro (3 shots × 6s) | | ~$0.90 |
| OpenRouter — WAN (1 shot × 8s) | | ~$0.08 |
| OpenRouter — Veo-Lite (1 shot × 6s) | | ~$0.15 |
| Sarvam TTS — voices + narration | ~1,000 chars | ~$0.02 |
| Sarvam Dub — 9 languages × 2 min | | ~$0.11 |
| Claude — YouTube metadata × 9 langs | | ~$0.01 |
| **Total per episode** | | **~$2.46** |

4 episodes/month = **~$10/month (~£8)**
= English master + 9 Indian language versions of every episode.

---

*v3 final. Hand to Cursor. Run Pre-Flight checklist. Start Session 1, Step 1.*
