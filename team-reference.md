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
- [x] **3-Agent Interfaces**: Defined system prompt templates, tool schemas, and harness structures for Agent 1 (Intake/Logging), Agent 2 (Progression/Planning), and Agent 3 (Trainer Monitoring).
- [x] **Mobile Frontend Shells**: Created mobile-first layouts, safe-area CSS utilities, client workout logging screen with local persistence, and trainer review dashboard.

### 🎯 What To Do (Active Sprints & Waves)
> Refer to the detailed breakdown in [**`documents/09-implementation-plan.md`**](./documents/09-implementation-plan.md).

- [x] **Wave 0: Foundation Setup, DB Materialization & Contract Freeze**
  - Justin: Alembic migration (port 5432), seed data script (real GoTrue user, real UUID session), `/log/preview` split, doc contract alignment.
  - Yadan: Frontend Node environment setup (`npm install`), `.env.local`, type verification.
  - **Joint Sync Gate 0**: Verify live DB, health check, frozen exercise vocabulary (`ex_bench`, `ex_squat`, `ex_row`).
- [ ] **Wave 1: In-Gym Logging Loop & Agent 1 (Extraction & Pain Detection)**
  - Justin: Live Claude Haiku wiring, preview/commit endpoints, deterministic eval test suite.
  - Yadan: Replace set grid with editable confirmation card, Web Speech API dictation button, `localStorage` buffer.
  - **Joint Sync Gate 1**: End-to-end mobile logging with inline typo correction and idempotency check.
- [ ] **Wave 2: Deterministic Progression Engine & Agent 2 (Safety Cross-Check & Trainer Review)**
  - Justin: Per-exercise progression engine (+5 lbs compound), weekly planning service, Agent 2 safety harness (Sonnet), archive-on-approve.
  - Yadan: Trainer plan review queue, visual delta cards (+5 lbs / held), 1-click approve & inline edit UI.
  - **Joint Sync Gate 2**: End-to-end progression loop with shoulder pain hold and trainer approval.
- [ ] **Wave 3: Agent 3 (Triage, Adherence & Outreach) & Trainer Admin Suite**
  - Justin: Agent 3 backend service (Haiku, urgency in Python), triage feed & dismissal API, client session generation endpoint.
  - Yadan: Trainer triage feed UI, dismiss alerts, client roster table, add client & link generator modal.
  - **Joint Sync Gate 3**: Inactivity detection, outreach message drafting, session link generation.
- [ ] **Wave 4: Security Hardening & Production Deployment**
  - Justin: Audit trace review, Render backend deployment, full test suite execution.
  - Yadan: Mobile cross-browser QA, Vercel frontend deployment.
  - **Joint Sync Gate 4 / Final Handshake**: Live production demo flow.

### ⚠️ Issues Needing Resolution (Blockers & Decisions)
- [ ] **Decision 1: Mobile Speech-to-Text Strategy**: Evaluate browser-native Web Speech API vs server-side Whisper via HTTPX. *Recommendation*: Use Web Speech API for instant client-side dictation, fallback to audio upload if browser support is missing.
- [ ] **Decision 2: Progression Rule Nuances**: Define specific rep target bands (e.g., compound lifts +5 lbs on $3 \times 10$, isolation lifts +2.5 lbs or rep progression before weight progression).
- [ ] **Decision 3: Trainer Client Import**: Determine whether an import parser for Google Sheets/CSV is needed in Phase 2 or deferred to post-MVP.

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

- **Integration Branch**: `main` serves as the primary integration branch.
- **Pull Request Workflow**: Feature development occurs on descriptive branches (e.g., `feat/agent1-extraction`, `feat/session-links`). Changes are merged into `main` via PRs after automated tests and build checks pass.
- **Lane Ownership**: Respect module ownership during active development. Coordinate before refactoring another builder's active files to avoid merge friction.
- **Local Testing Before Pushing**: Always verify backend tests pass (`pytest tests/`) and frontend compiles (`npm run build`) before submitting pull requests.

---

## 🗺️ 5. Project Roadmap (5 Phases)

| Phase | Milestone | Focus Areas | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Scaffolding & Architecture** | Monorepo layout, Next.js, FastAPI, Supabase models, agent specs, docs | 🔄 Completed |
| **Phase 2** | **Database, Auth & Session Links** | Supabase migrations, trainer JWT auth, client session link resolution | ⬜ Next |
| **Phase 3** | **Agent 1 & Agent 2 Progression Engine** | Set extraction from chat/voice, deterministic math engine, injury cross-checks, eval harness | ⬜ Planned |
| **Phase 4** | **Trainer Dashboard & Agent 3** | Triage review queue, one-tap plan approvals, missed check-in alerts, draft messaging | ⬜ Planned |
| **Phase 5** | **Mobile Gym Polish & Live Testing** | Voice transcription refinement, offline storage resilience, user testing with real trainer | ⬜ Planned |
