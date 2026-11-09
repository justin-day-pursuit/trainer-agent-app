# Team Reference & Living Project Log

> **Living collaboration log and development reference for the Trainer Progression App builders and their AI coding assistants.**

---

## 🧭 1. Project Direction & Core Objectives

The Trainer Progression App is built to eliminate hours of weekly administrative overhead for independent personal trainers while keeping them in full control of their clients' training programs.

### Guiding Engineering Principles
1. **Deterministic Progression Before LLM**: The AI never invents or calculates exercise weights. A deterministic Python math engine handles progression calculations, while AI agents cross-check safety, extract logs, and draft reviews.
2. **Trainer Retains Human-in-the-Loop Authority**: No AI-drafted workout plan, progression increase, or client-facing message is delivered without explicit trainer review and one-tap approval.
3. **Mobile-First In-Gym Usability**: Client interactions are optimized for one-handed mobile use in sweaty gym environments: large tap targets ($\ge 44\text{px}$), safe-area insets, free-form voice/chat entry, and client-side `localStorage` state persistence to prevent lost data during app refreshes.
4. **Frictionless Client Identity**: Trainers create accounts using Supabase Auth. Clients do not register accounts; they access their personal workout and logging views via a unique, non-guessable session link (`/s/:token`).

---

## 📋 2. Active Work Log & Task Tracker

### ✅ What Has Been Done
- [x] **Project Scaffolding**: Initialized decoupled monorepo architecture with Next.js (App Router) on the frontend and FastAPI on the backend.
- [x] **Documentation & Architecture Standards**: Established `README.md`, `team-reference.md`, `agents.md`, and `CLAUDE.md`.
- [x] **Comprehensive Project Documentation (`documents/`)**: Authored 9 foundational reference manuals covering project scope, refined PRD with eval cards, visual user flows (Mermaid), database schema with ER diagram, REST API reference, technology stack ADRs, security & safety threat models, cloud deployment guide, and the multi-wave two-builder implementation plan ([`09-implementation-plan.md`](./documents/09-implementation-plan.md)).
- [x] **Environment & Secret Hygiene**: Configured `.gitignore` and comprehensive `.env.example` templates covering Supabase, PostgreSQL, and Anthropic Claude configurations.
- [x] **Data & Model Specifications**: Created async SQLAlchemy models and Pydantic schemas for `Trainer`, `ClientProfile`, `ClientSession`, `WorkoutPlan`, `WorkoutLog`, and `AgentTrace`.
- [x] **Auth Architecture**: Built dual authentication dependencies—Supabase PyJWT verification for trainers and secure UUID session-token resolution for clients.
- [x] **Modular Progression Engine**: Implemented Protocol-based deterministic progression engine ready for custom progression algorithms.
- [x] **3-Agent Interfaces**: Defined system prompt templates, tool schemas, and harness structures for the 3 agents: Workout Logger, Progression Planner, and Trainer Assistant.
- [x] **Mobile Frontend Shells**: Created mobile-first layouts, safe-area CSS utilities, client workout logging screen with local persistence, and trainer review dashboard.

### 🎯 What To Do (Active Sprints & Waves)
> Refer to the detailed breakdown in [**`documents/09-implementation-plan.md`**](./documents/09-implementation-plan.md).

- [ ] **Wave 0: Foundation Setup, DB Materialization & Contract Freeze** *(In Progress)*
  - Justin: Alembic migration (port 5432), seed data script against live Supabase, `/log/preview` split, backend test suite, doc contract alignment.
  - Yadan: Local workspace setup on her machine (`npm install`, `frontend/.env.local`, `npm run build`, `npm run lint`).
  - **Joint Sync Gate 0**: Verify live DB, health check, frozen exercise vocabulary (`ex_bench`, `ex_squat`, `ex_row`).
- [ ] **Wave 1: In-Gym Logging Loop & Workout Logger (Extraction & Pain Detection)**
  - Justin: Backend endpoints (`/log/preview`, `/log`), idempotency validation, deterministic eval test suite.
  - Yadan: Workout Logger agent harness (Claude Sonnet 5.5), confirmation card UI, Web Speech API dictation, `localStorage` buffer, mobile-browser-compatible client UX.
  - **Joint Sync Gate 1**: End-to-end mobile logging with inline typo correction and idempotency check.
- [ ] **Wave 2: Deterministic Progression Engine & Progression Planner (Safety Cross-Check & Trainer Review)**
  - Yadan: Formulate progression calculation rules/math; trainer plan review queue, visual delta cards (+5 lbs / held), 1-click approve & inline edit UI.
  - Justin: Implement progression calculation engine to Yadan's specifications, Progression Planner safety harness (Claude Haiku 5.5), weekly planning service, archive-on-approve API.
  - **Joint Sync Gate 2**: End-to-end progression loop with shoulder pain hold and trainer approval.
- [ ] **Wave 3: Trainer Assistant (Triage, Adherence & Outreach) & Trainer Admin Suite**
  - Justin: Trainer Assistant backend service (Claude Sonnet 5.5, urgency in Python), triage feed & dismissal API, client session generation endpoint.
  - Yadan: Trainer triage feed UI, dismiss alerts, client roster table, add client & link generator modal (PC-browser-optimized with mobile responsiveness).
  - **Joint Sync Gate 3**: Inactivity detection, outreach message drafting, session link generation.
- [ ] **Wave 4: Security Hardening & Production Deployment**
  - Justin: Audit trace review, Render backend deployment, full test suite execution.
  - Yadan: Mobile cross-browser QA, Vercel frontend deployment.
  - **Joint Sync Gate 4 / Final Handshake**: Live production demo flow.

### ⚠️ Issues Needing Resolution (Blockers & Decisions)
- [ ] **Decision 1: Mobile Speech-to-Text Strategy**: Evaluate browser-native Web Speech API vs server-side Whisper via HTTPX. *Recommendation*: Use Web Speech API for instant client-side dictation, fallback to audio upload if browser support is missing.
- [ ] **Decision 2: Progression Rule Nuances**: Yadan to define specific rep target bands and progression rules (e.g., compound lifts +5 lbs on $3 \times 10$, isolation lifts +2.5 lbs or rep progression before weight progression) for Justin to implement in the Python engine.
- [ ] **Decision 3: Trainer Client Import**: Determine whether an import parser for Google Sheets/CSV is needed in Phase 2 or deferred to post-MVP.

### 🔎 Open Items from Yadan's Repo Review (2026-11-09)
- [x] **1. Builder lanes (Decided 2026-11-09)**: Justin takes Trainer Assistant agent, Progression Planner agent, and backend development. Yadan takes Workout Logger agent, frontend development, and mobile-browser-compatible UX. UX distinction: client flow is mobile-first for gym floor; trainer dashboard is PC/desktop-first with mobile responsiveness for on the go. Progression nuance: Yadan decides how progression is calculated, and Justin integrates the math into the engine.
- [x] **2. Wave 0 Status & Setup (Decided 2026-11-09)**: Marked in progress. Justin completed backend migrations, live Supabase database materialization, seed script, and contract tests. Yadan confirmed `npm install`, `npm run build`, `npm run lint`, and `tsc` all pass on `develop`, and `/`, `/s/:token`, and `/trainer` load cleanly. Still open for Joint Sync Gate 0: populating `frontend/.env.local` with live Supabase values and verifying the client session link against the live backend/database.
- [x] **3. Intake Scope (Decided 2026-11-09 - Option B)**: Both trainer and client can enter goals and injury information. Clients can enter/update via the Workout Logger agent or session profile; trainers can enter/update via the Trainer Assistant agent or dashboard form. Autonomy exists for both sides to use agents, while Human-in-the-Loop stands: trainer retains ultimate authority to manually review and override goals and injury records.
- [x] **4. Integration branch (Decided 2026-11-09)**: Stay on `develop` until the app works, then merge to `main`. See section 4.

### 🎬 Final Project Submission (Due Wed, Nov 11, 12:00 PM, group)
A 5-minute presentation, submitted through the Google Form:
- [ ] **1. Record** a 2.5-minute working demo navigating the app.
- [ ] **2. Create** a 2.5-minute deck: the JD, what we address, how it improves the workflow.
- [ ] **3. Show** the architecture and a diagram of how the agent or workflow moves through.
- [ ] **4. Practice** to hit 5 minutes, then submit both.

The demo needs the core loop working on `develop`: the client logs a workout (Wave 1), the engine drafts next week, and the trainer approves it (Wave 2). Wave 3 and Wave 4 can wait until after the demo.

---

## 🚀 3. New Clone Onboarding Checklist

Follow this checklist whenever setting up a new local workspace:

1. **Clone the Repository**:
   ```bash
   git clone git@github-pursuit:justin-day-pursuit/trainer-agent-app.git
   cd trainer-agent-app
   ```

2. **Set Up Environment Variables**:
   Copy the example templates in both root subprojects:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
   Open both `.env` files and populate with shared project keys (Supabase URL, Anon Key, JWT Secret, Anthropic API Key).

3. **Verify Git Hygiene**:
   Run `git status` to ensure neither `.env` file is tracked by git:
   ```bash
   git status --ignored | grep .env
   ```

4. **Install Backend Dependencies**:
   ```bash
   cd backend
   # If using uv:
   uv sync
   # Or using standard venv:
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

5. **Install Frontend Dependencies**:
   ```bash
   cd ../frontend
   npm install
   ```

6. **Verify Service Health**:
   - Start backend: `uvicorn app.main:app --reload --port 8000`
   - Start frontend: `npm run dev`
   - Check `http://localhost:8000/health` (should return `{"status": "ok"}`)
   - Check `http://localhost:3000` (should display the landing page)

---

## 🤝 4. Collaboration & Branch Discipline

- **Integration Branch**: `develop` is the integration branch until the app works end to end. Only then does it merge to `main`.
- **Pull Request Workflow**: Feature development occurs on descriptive branches (e.g., `feat/workout-logger-extraction`, `feat/session-links`). Changes are merged into `develop` via PRs after automated tests and build checks pass.
- **Lane Ownership**: Respect module ownership during active development. Coordinate before refactoring another builder's active files to avoid merge friction.
- **Local Testing Before Pushing**: Always verify backend tests pass (`pytest tests/`) and frontend compiles (`npm run build`) before submitting pull requests.

---

## 🗺️ 5. Project Roadmap (5 Phases)

| Phase | Milestone | Focus Areas | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Scaffolding & Architecture** | Monorepo layout, Next.js, FastAPI, Supabase models, agent specs, docs | 🔄 Completed |
| **Phase 2** | **Database, Auth & Session Links** | Supabase migrations, trainer JWT auth, client session link resolution | ⬜ Next |
| **Phase 3** | **Workout Logger & Progression Planner** | Set extraction from chat/voice, deterministic math engine, injury cross-checks, eval harness | ⬜ Planned |
| **Phase 4** | **Trainer Dashboard & Trainer Assistant** | Triage review queue, one-tap plan approvals, missed check-in alerts, draft messaging | ⬜ Planned |
| **Phase 5** | **Mobile Gym Polish & Live Testing** | Voice transcription refinement, offline storage resilience, user testing with real trainer | ⬜ Planned |
