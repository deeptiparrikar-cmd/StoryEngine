# Story Engine — Revised Sprint Plan
### Reflecting all stack decisions as of May 2026
**Stack: Python/Flask · SQLite · OpenRouter (Claude + Images + Video) · ElevenLabs · No Sarvam**

---

## Stack Summary (locked)

| Layer | Tool | Notes |
|---|---|---|
| LLM | Claude 3.5 Haiku via OpenRouter | `anthropic/claude-3-5-haiku` |
| Image gen | OpenRouter image models | Gemini 2.5 Flash Image |
| Video gen | OpenRouter video models | Seedance / Kling / WAN / Veo-Lite |
| TTS + Dubbing | ElevenLabs | Starter plan $6/mo — upgrade before Sprint 7 |
| Narrator voice | ElevenLabs Voice Library | Voice ID: `hO2yZ8lxM3axUxL8OeKX` (Mini) |
| Transcription | Wispr Flow (external) | User speaks → Wispr types → paste into app |
| DB | SQLite (stdlib) | `story_engine.db` at project root |
| Frontend | React + Vite | localhost:3000 |
| Backend | Flask | localhost:5000 |

**No Sarvam anywhere. No Anthropic direct API. No HeyGen.**

---

## Sprint 1 — ✅ COMPLETE
**Skeleton + Database**
- Flask app factory
- SQLite schema + db.py
- `/api/health` returns `{"status": "ok"}`
- `story_engine.db` created on startup

---

## Sprint 2 — Claude Reads a Story
**Goal:** Paste a story → get JSON shot list + cost estimate back from the API

### What to build:
1. `backend/agents/script_agent.py`
   - Calls Claude 3.5 Haiku via OpenRouter
   - Base URL: `https://openrouter.ai/api/v1`
   - Returns parsed JSON shot list (see spec for full schema)
   - Includes cinematic fields: `emotional_tone`, `motion_intent`,
     `sound_design`, `transition_to_next`, `cinematic_reference`

2. `backend/utils/cost_estimator.py`
   - Takes shot list JSON
   - Returns itemised cost breakdown + total USD

3. `POST /api/episodes/new`
   - Receives `{ "story": "..." }`
   - Calls script_agent
   - Saves episode + shots to SQLite
   - Returns shot list + cost estimate JSON

### NOT in this sprint:
- No UI
- No image generation
- No Sarvam (dropped entirely)
- No ElevenLabs yet

### Done when:
Curl or Postman: `POST /api/episodes/new` with a story →
returns clean JSON shot list with cost estimate in terminal.

### Cursor instruction:
> "Sprint 1 is complete. We are on Sprint 2. There is no STT
> in this app — Wispr Flow handles that externally. Build only:
> script_agent.py calling Claude via OpenRouter at
> https://openrouter.ai/api/v1 using model
> anthropic/claude-3-5-haiku, cost_estimator.py, and the
> POST /api/episodes/new route. Done when a pasted story
> returns a JSON shot list with cost estimate."

---

## Sprint 3 — Shot Review UI
**Goal:** See the shot list in a browser, edit it, approve it

### What to build:
1. React + Vite frontend scaffold
   - Basic routing: Home screen + New Episode screen + Shot Review screen
   - No other screens yet

2. `frontend/src/screens/NewEpisode.jsx`
   - Large textarea: "Paste your story here"
   - Button: "✨ Turn Into Episode"
   - Calls `POST /api/episodes/new`
   - On response: navigates to Shot Review screen

3. `frontend/src/screens/ShotReview.jsx`
   - Episode title (editable inline)
   - Cost estimate breakdown card
   - Shot cards — each shows:
     - Sequence number
     - Description
     - Model badge (colour coded)
     - Duration
     - Emotional tone
     - Dialogue line if present
   - NEW CHARACTER cards in amber
   - [✎ Edit] and [✕ Remove] on each shot card
   - [✅ Generate Episode — ~$X.XX] button
     (button does nothing yet — just logs to console)

4. `frontend/src/screens/Home.jsx`
   - List of past episodes from `GET /api/episodes`
   - Status badges
   - [+ New Episode] button

5. `GET /api/episodes` route (backend)
   - Returns list of all episodes with status + cost

### NOT in this sprint:
- Generate button does not fire any generation yet
- No image calls
- No video calls
- No ElevenLabs calls

### Done when:
Paste a story in the browser → see shot cards with cost
breakdown → can edit/remove shots → approve button visible.
This is the first thing that looks like a real app.

### Cursor instruction:
> "Sprint 2 is complete. We are on Sprint 3. Build the React
> frontend with three screens: Home, NewEpisode, and
> ShotReview. NewEpisode pastes a story and calls
> POST /api/episodes/new. ShotReview displays the shot list
> returned, with editable cards, cost estimate, and an Approve
> button that only logs to console for now. Also add
> GET /api/episodes to the backend. No generation logic yet."

---

## Sprint 4 — First Image Generated
**Goal:** Click Approve → one character reference image downloads to disk

### What to build:
1. `backend/utils/prompt_builder.py`
   - Resolves `[STYLE]` token → `ART_STYLE` from `.env`
   - Resolves `[CHAR:name]` tokens → character ref image paths
   - Unit test with dummy data before wiring to agents

2. `backend/agents/image_agent.py`
   - Single image call to OpenRouter
   - Model: `google/gemini-2.5-flash-image`
   - Downloads image to correct path on disk
   - For new characters: generates 6 angles in parallel
     via `ThreadPoolExecutor`

3. `backend/utils/file_writer.py`
   - Downloads URL → disk with correct folder structure

4. `backend/utils/job_queue.py`
   - `ThreadPoolExecutor(max_workers=8)` wrapper

5. `POST /api/episodes/:id/generate` route (partial)
   - Triggers character image generation only
   - Updates shot/character status in SQLite

6. Wire Approve button in `ShotReview.jsx`
   - Calls `POST /api/episodes/:id/generate`
   - Shows spinner while running

### Done when:
Click Approve in browser → character reference images
appear in `OUTPUT_DIR/characters/` on disk.

### Cursor instruction:
> "Sprint 3 is complete. We are on Sprint 4. Build
> prompt_builder.py (resolves [STYLE] and [CHAR:name] tokens),
> image_agent.py (single OpenRouter image call + 6-angle
> character generation in parallel), file_writer.py, and
> job_queue.py. Wire the Approve button to
> POST /api/episodes/:id/generate which triggers character
> image generation only. Done when clicking Approve downloads
> character images to disk."

---

## Sprint 5 — First Video Clip
**Goal:** One video clip generates, downloads to disk, pipeline is real

### What to build:
1. `backend/agents/video_agent.py`
   - `submit_video_job()` — submits to OpenRouter video API
   - Writes job_id to SQLite BEFORE API call returns
   - `poll_video_jobs()` — polls every 30 seconds
   - On complete: downloads MP4 to correct path
   - On fail: increments retry_count, auto-retries up to 2x
   - Runs in background thread

2. Extend `POST /api/episodes/:id/generate`
   - After character images: generate scene first-frame images
   - Then submit video jobs for all shots
   - All via job_queue (max 8 concurrent)

3. `GET /api/episodes/:id/status` route
   - Returns per-shot status for polling
   - Returns running cost total

4. On app startup: resume polling any jobs with
   `video_status IN ('running', 'queued')`

### Done when:
One Seedance clip generates and appears in
`OUTPUT_DIR/episodes/{id}/clips/` on disk.
Test with a single shot before running full episode.

### Cursor instruction:
> "Sprint 4 is complete. We are on Sprint 5. Build
> video_agent.py with submit_video_job() and poll_video_jobs().
> Critical: write job_id to SQLite before the API call returns.
> On app startup, resume polling any jobs with status running
> or queued. Extend the generate route to also submit video
> jobs after images. Add GET /api/episodes/:id/status for
> polling. Done when one Seedance clip downloads to disk."

---

## Sprint 6 — Full Episode + Production Dashboard
**Goal:** Full episode folder on disk, progress visible in browser

### What to build:
1. `frontend/src/screens/Production.jsx`
   - Live progress for each shot: image → video → done
   - Progress bar across all shots
   - Failed shots in red with [↺ Retry] button
   - Running cost total
   - Polls `GET /api/episodes/:id/status` every 10 seconds

2. `backend/logger/cost_logger.py`
   - Adapted from VaidyaBot latency_logger pattern
   - Logs every API spend to `logs/costs.jsonl`
   - Stages: `image_gen`, `video_gen`, `claude`

3. Full parallel generation
   - All 10 scene images fire in parallel
   - All 10 video jobs submit and poll concurrently
   - Max 8 workers enforced

4. `PATCH /api/shots/:id` — edit prompt/model/duration
5. `POST /api/shots/:id/retry` — manual retry of failed shot

### Done when:
Full episode folder appears on disk with all clips.
Production dashboard shows live progress.
Episode completes without manual intervention.

### Cursor instruction:
> "Sprint 5 is complete. We are on Sprint 6. Build the
> Production dashboard UI that polls GET /api/episodes/:id/status
> every 10 seconds and shows per-shot progress. Add
> cost_logger.py adapted from VaidyaBot's latency_logger.
> Enable full parallel generation for all images and video clips
> with max 8 concurrent workers. Add PATCH /api/shots/:id
> and POST /api/shots/:id/retry routes. Done when a full
> episode generates with progress visible in the browser."

---

## Sprint 7 — Voices (ElevenLabs)
**⚠️ UPGRADE TO ELEVENLABS STARTER ($6/mo) BEFORE THIS SPRINT**

**Goal:** Narrator intro/outro + character dialogue voices generated as .mp3 files

### What to build:
1. `backend/agents/voice_agent.py`
   - ElevenLabs TTS via official Python SDK
   - Narrator voice: `hO2yZ8lxM3axUxL8OeKX` (Mini)
   - Character voices: assigned per character in DB
   - Model: `eleven_multilingual_v2`
   - Output format: `mp3_44100_128`
   - Runs concurrently with video generation (not after)

2. Character voice assignment
   - Each new character gets a voice assigned at creation
   - Stored in `characters.voice_speaker` in SQLite
   - Shown as dropdown in Shot Review NEW CHARACTER cards

3. `backend/utils/assembler.py`
   - Writes `EDIT_ORDER.txt` with full cinematic edit script
     (sound_design, transition_to_next, music notes per shot)
   - Writes `episode_data.json`
   - Creates final folder structure

4. `frontend/src/screens/Complete.jsx`
   - [📁 Open Folder] button
   - [📋 Copy Edit Order] button
   - Clip thumbnail grid
   - [▶ Dub into 9 languages] button (triggers Sprint 8)
   - Total spend display

### Done when:
Episode folder contains `narration/intro.mp3`,
`narration/outro.mp3`, `voices/` dialogue files,
and `EDIT_ORDER.txt`. Open in CapCut and first
edit takes under 20 minutes.

### ElevenLabs install:
```
pip install elevenlabs
```

### Cursor instruction:
> "Sprint 6 is complete. Upgrade ElevenLabs to Starter plan
> before proceeding. Build voice_agent.py using the official
> ElevenLabs Python SDK. Narrator voice ID is
> hO2yZ8lxM3axUxL8OeKX (Mini), model eleven_multilingual_v2,
> output mp3_44100_128. Voice generation runs concurrently
> with video generation. Build assembler.py to write
> EDIT_ORDER.txt with full cinematic edit notes per shot.
> Build the Complete screen. Done when the episode folder
> has all voice files and EDIT_ORDER.txt."

---

## Sprint 8 — Dubbing (ElevenLabs)
**Goal:** 9 Indian language versions of the episode, upload-ready

### What to build:
1. `backend/agents/dub_agent.py`
   - ElevenLabs Dubbing API
   - Input: assembled English episode audio + video
   - Output: dubbed audio per language
   - ffmpeg mux: dubbed audio onto original video
   - One MP4 per language in `languages/{lang-code}/`

2. YouTube metadata per language
   - Claude via OpenRouter translates title + description + tags
   - Saved as `languages/{lang-code}/youtube_metadata.txt`

3. Dubbing progress in Complete screen
   - Per-language status badges
   - Hindi ✅ Tamil ⏳ etc.

4. `POST /api/episodes/:id/dub` route

### Done when:
`languages/hi-IN/episode.mp4` exists and plays with
Hindi audio over the original visuals.

### Cursor instruction:
> "Sprint 7 is complete. Build dub_agent.py using the
> ElevenLabs Dubbing API. For each language in DUB_LANGUAGES
> env var, submit a dub job, poll until complete, download
> dubbed audio, mux onto original video using ffmpeg via
> subprocess. Generate YouTube metadata per language via
> Claude through OpenRouter. Add POST /api/episodes/:id/dub
> route. Done when hi-IN/episode.mp4 exists with Hindi audio."

---

## .env Reference (current final state)

```env
# OpenRouter
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-3-5-haiku

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_NARRATOR_VOICE_ID=hO2yZ8lxM3axUxL8OeKX
ELEVENLABS_MODEL=eleven_multilingual_v2
ELEVENLABS_DUB_ENDPOINT=https://api.elevenlabs.io/v1/dubbing

# Narrator
NARRATOR_NAME=Mini

# Channel identity
ART_STYLE=soft watercolour illustration, warm pastel colours,
          Studio Ghibli inspired, child-friendly, clean outlines,
          gentle lighting, no scary elements, no photorealism,
          storybook aesthetic, bright warm backgrounds

# Distribution
DUB_LANGUAGES=hi-IN,ta-IN,te-IN,bn-IN,kn-IN,ml-IN,mr-IN,gu-IN,pa-IN

# Safety
MAX_SPEND_PER_EPISODE_USD=6.00

# Output
OUTPUT_DIR=C:\StoryEngine\episodes
```

---

## What Was Dropped vs Original Spec

| Dropped | Reason |
|---|---|
| Sarvam STT | Wispr Flow handles transcription externally |
| Sarvam TTS | ElevenLabs has better kids voices |
| Sarvam Translate | ElevenLabs Dubbing handles translation + audio |
| Sarvam Dub | Not accessible on standard API key |
| Anthropic direct API | Using Claude via OpenRouter instead |
| HeyGen | Dropped — ElevenLabs covers all voice needs |
| Narrator avatar video | Style clash with illustrated scenes — voice only |

---

## Upgrade Reminder

| Sprint | ElevenLabs plan needed |
|---|---|
| 1–6 | Free tier fine — ElevenLabs not used |
| 7–8 | **Starter $6/mo required** — upgrade before Sprint 7 |
