# Trainer Progression App

> **A mobile-first, agentic web application designed for independent personal trainers to automate weekly workout progression drafting and capture frictionless in-gym voice and chat logs from clients.**

---

## 🏋️‍♂️ Problem & Vision

Independent personal trainers lose hours every weekend manually rebuilding client workout spreadsheets, copying rows, and calculating load progressions from memory. Existing tools like Trainerize force repetitive, workout-by-workout editing and trap client data behind escalating subscription fees.

The **Trainer Progression App** solves manual programming fatigue through a decoupled, human-in-the-loop multi-agent architecture:
1. **Frictionless Client Logging**: Clients dictate or text their completed sets, reps, and feedback directly on their phone using a unique session link (no tedious account creation or tiny form-tapping with sweaty hands).
2. **Deterministic Progression Engine**: `EffortBasedProgression` drafts the weights and reps. Pain, missed reps, a missing set, a challenging effort, or no recorded effort holds the weight and the reps. An easy effort under 12 reps adds 2 reps, capped at 12. An easy effort at 12 reps adds 5 lb and resets reps to 8. An easy bodyweight lift at 12 reps holds, and the trainer decides.
3. **Planner flags, engine numbers**: The deterministic engine drafts the weights. The Progression Planner only flags held lifts and does not change them. A draft gets a [Planner] flag only for a held, pain-free, same-weight lift. A real planner call writes one `agent_traces` row. If that write fails, the log and the draft stay.
4. **Trainer Decides**: The trainer reviews the engine's draft and any planner flags on the dashboard and hits **Approve**, which pushes next week's plan to the client's phone.

---

## 🏛️ Architecture Overview

The application is structured as a decoupled monorepo split into a **mobile-optimized Next.js frontend** and a **FastAPI backend**:

```
+-------------------------------------------------------------+
|                     CLIENT MOBILE BROWSER                   |
|  - Accesses unique session URL: /s/:sessionToken            |
|  - Conversational voice/chat logging (Workout Logger)       |
|  - Week-over-week progress viewer                           |
|  - In-browser localStorage crash recovery                   |
+------------------------------+------------------------------+
                               |
                               | HTTPS / JSON
                               v
+-------------------------------------------------------------+
|                     TRAINER DASHBOARD                       |
|  - Protected by Supabase Auth (/trainer)                    |
|  - Review queue: engine drafts weights; planner flags holds|
|  - Triage feed planned for Wave 3 (not on the dashboard yet)|
|  - 1-click plan approval (Human-in-the-Loop)                |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    FRONTEND (Next.js / Vercel)              |
|  - TypeScript + Tailwind CSS (Mobile-First)                 |
|  - Supabase JS Client (Trainer sign-in only)                |
|  - Dedicated scrollable data containers                     |
+------------------------------+------------------------------+
                               |
                               | REST API
                               v
+-------------------------------------------------------------+
|                    BACKEND (FastAPI / Render)               |
|  - FastAPI + Uvicorn + Pydantic v2 Settings                 |
|  - SQLAlchemy 2.0 (Async) + Psycopg + Alembic               |
|  - PyJWT Supabase Token Verification                        |
|  - Anthropic Claude API via HTTPX                           |
|  - Modular Deterministic Progression Engine (Protocol)      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                    DATA & AUTH (Supabase)                   |
|  - Supabase PostgreSQL (Async connection pool)              |
|  - Supabase Auth (Trainer accounts only)                    |
|  - Unique UUID ClientSession tokens                         |
+-------------------------------------------------------------+
```

---

## 🤖 The 3 Specialized Agents

| Agent | Model | Responsibility | Trigger | Permissions & Safeguards |
| :--- | :--- | :--- | :--- | :--- |
| **Workout Logger** | `claude-sonnet-5-5` (Front-Facing) | Converses with clients during intake; parses conversational chat/voice logs into structured set rows (`exercise_id`, `weight_lbs`, `reps`, `pain_flag`). | On-demand (client sends a message or submits a workout note). | **Read**: Client profile & prescribed workout.<br>**Write**: Extracted sets, pain notes, intake data.<br>**Safeguard**: Never changes workout plans; inline confirmation allows client 1-tap edits. |
| **Progression Planner** | `claude-haiku-5-5` (Backend Safety) | Reviews held lifts. It does not change weights. Drafting appends a [Planner] flag only for a held, pain-free, same-weight lift. The engine still sets the numbers. A real planner call writes one `agent_traces` row. A failed write does not drop the log or the draft. | Scheduled / Trainer-initiated weekend batch. | **Read**: Completed logs, the engine draft, injury history.<br>**Write**: A [Planner] flag on the engine's draft, and one `agent_traces` audit row when the model is actually called.<br>**Safeguard**: Never changes weights or reps. Never messages the client. The trainer approves the draft. |
| **Trainer Assistant** | `claude-sonnet-5-5` (Front-Facing) | Planned for Wave 3. Will monitor adherence, detect missed workouts, and draft check-in messages. The triage feed is not on the dashboard today. | Scheduled daily / Trainer dashboard query, once Wave 3 lands. | **Read**: Client profiles, logs, and history, when built.<br>**Write**: Alert records and draft messages, only after trainer approval.<br>**Safeguard**: Cannot send messages or edit plans without explicit trainer approval. |

---

## 🛠️ Tech Stack

### Frontend (`frontend/`)
- **Framework**: Next.js 15+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS (mobile-first breakpoints, safe-area padding, touch targets $\ge 44\text{px}$)
- **Auth**: `@supabase/supabase-js` (Trainer sign-in only)
- **Icons**: `lucide-react`
- **Deployment**: Vercel

### Backend (`backend/`)
- **Framework**: FastAPI + Uvicorn
- **Language**: Python 3.10+
- **Database & ORM**: SQLAlchemy 2.0 (asyncio) + `psycopg` (binary) + Alembic
- **Validation**: Pydantic v2 + `pydantic-settings`
- **Auth Verification**: `PyJWT` (verifies Supabase tokens)
- **AI Integrations**: `httpx` (HTTP calls to Anthropic Claude API)
- **Dev & Test**: `pytest`, `pytest-asyncio`, `ruff`
- **Deployment**: Render (Docker)

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone git@github-pursuit:justin-day-pursuit/trainer-agent-app.git
cd trainer-agent-app
```

### 2. Environment Variables Setup
Copy the environment templates in both `backend` and `frontend`:
```bash
# Backend environment setup
cp backend/.env.example backend/.env

# Frontend environment setup
cp frontend/.env.example frontend/.env
```
Open each `.env` file and insert your Supabase project credentials and Anthropic API key.

---

### 3. Backend Setup & Run

#### Option A: Using `uv` (Recommended)
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

#### Option B: Using standard Python `venv`
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Backend will be live at `http://localhost:8000`. Test the health endpoint:
```bash
curl http://localhost:8000/health
# {"status":"ok","environment":"development"}
```

Run backend tests:
```bash
pytest tests/ -v
```

---

### 4. Frontend Setup & Run
```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:3000`.

- **Client Mobile Flow**: Navigate to `http://localhost:3000` and enter a session link or navigate to `/s/demo-client-session`.
- **Trainer Dashboard**: Navigate to `http://localhost:3000/trainer`.

---

### 5. Production Deployment

#### Render backend
1. Create a Render Blueprint from the repository's `render.yaml`. The service uses
   the Free instance (`plan: free`), `backend` as its Docker context, and checks
   `GET /health`. Free services sleep after 15 minutes without traffic and take
   about a minute to wake. If a service was already created on a paid plan, switch
   its instance type to Free in the Render dashboard.
2. Add these secret or environment-specific names in the Render dashboard:
   `DATABASE_URL`, `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
   `SUPABASE_JWT_SECRET`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS`, `ENVIRONMENT`,
   and `DEBUG`. Render supplies `PORT`; do not add credentials to the repository.
3. Keep the pre-deploy command as `alembic upgrade head`. Migrations require
   `DIRECT_URL`, and production deployment does not run a seed.

#### Vercel frontend
1. Import the repository into Vercel and set the Root Directory to `frontend`.
2. Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and
   `NEXT_PUBLIC_API_URL` in Vercel project settings. `NEXT_PUBLIC_API_URL` must
   point to the Render service and end in `/api/v1`.
3. Deploy the frontend. After its Vercel origin exists, set Render's
   `CORS_ORIGINS` to that exact origin: scheme and host only, with no path.
4. Confirm the Render `/health` endpoint and the Vercel site before production use.

No production values belong in this README or either committed environment example.

---

### 6. Running with Docker Compose (Optional Local DB)
If you prefer running a local PostgreSQL instance:
```bash
cd backend
docker-compose up -d
```

---

## ⏸️ Deferred Features (Post-MVP)
In line with project scope guidelines, the following capabilities are architected as interfaces but deferred from immediate implementation:
- Complex charting and visualization suites
- Heavy 3rd-party UI component libraries (retained clean Tailwind primitives)
- Distributed background job queues (Celery/Redis)
- Automated outbound SMS / push notifications
- External autonomous agent tools beyond internal model reasoning

---

## 📖 Team & Architecture Documentation

### Operational Team Docs
- [`team-reference.md`](./team-reference.md): Living team work log, active tasks, open decisions, and fresh clone onboarding instructions.
- [`agents.md`](./agents.md): Agent engineering doctrine, harness specifications, prompt injection defenses, eval cards, and permission boundaries.
- [`CLAUDE.md`](./CLAUDE.md): Direct instructions and quick rules for Claude Code and CLI users.

### Detailed Project Documentation (`documents/`)
- [`01-project-scope.md`](./documents/01-project-scope.md): Detailed project scope, target personas, business case, and boundary definitions.
- [`02-product-requirements.md`](./documents/02-product-requirements.md): Refined PRD with functional/non-functional requirements, eval cards, and blast radius safeguards.
- [`03-user-flows.md`](./documents/03-user-flows.md): Visual user flows and sequence diagrams (Mermaid) for logging, progression, triage, and recovery.
- [`04-data-model.md`](./documents/04-data-model.md): Database schema documentation, ER diagram, JSON schemas, indexes, and Alembic migration guide.
- [`05-api-reference.md`](./documents/05-api-reference.md): Complete REST API endpoint reference, authentication mechanisms, and request/response examples.
- [`06-tech-stack.md`](./documents/06-tech-stack.md): Technology stack selections, architectural decision records (ADRs), and version pins.
- [`07-security-and-safety.md`](./documents/07-security-and-safety.md): Threat models, token cryptography, tenant data isolation, and safety guardrails.
- [`08-deployment-guide.md`](./documents/08-deployment-guide.md): Operations manual for Vercel, Render, Supabase, environment variables, and observability.
- [`09-implementation-plan.md`](./documents/09-implementation-plan.md): Comprehensive two-builder implementation plan (Justin & Yadan) structured in 5 waves (Wave 0 to Wave 4) with explicit builder lanes, joint sync gates, and verification criteria.
