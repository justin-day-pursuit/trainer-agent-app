# 06. Technology Stack Reference & Architecture Decision Records (ADRs)

This document provides a comprehensive analysis of the architectural choices, dependency selections, version pins, and design tradeoffs underlying the **Trainer Progression App**.

---

## 1. Architectural Philosophy

1. **Decoupled Monorepo**: Frontend (`frontend/`) and Backend (`backend/`) exist in a unified repository for synchronized versioning, shared schema validation, and cohesive CI/CD, but run as completely isolated runtime processes.
2. **API-First Protocol**: The Next.js frontend has zero direct database access. All data interactions flow through the authenticated FastAPI REST layer.
3. **Deterministic Core with AI Augmentation**: Math belongs in compiled deterministic algorithms; language synthesis and contextual safety analysis belong in LLMs.
4. **Mobile Browser Native**: High touch-target ergonomics, zero app-store download friction, and robust local offline resilience (`localStorage`).

---

## 2. Technology Selection & Alternatives Considered

### 2.1. Backend Framework: FastAPI
- **Choice**: **FastAPI** (`>=0.115.0`) with **Uvicorn** (`>=0.30.0`) on Python 3.10+
- **Rationale**:
  - Native Python `async`/`await` concurrency ideal for high-latency external LLM calls (Anthropic API).
  - First-class Pydantic v2 integration provides automatic request validation, serialization, and OpenAPI schema generation.
  - Seamless Python ecosystem compatibility for progression calculation engines, data analysis, and AI agent harnesses.
- **Alternatives Considered**:
  - *Django / DRF*: Overly heavyweight; synchronous heritage creates friction with high-concurrency LLM streaming and async database pools.
  - *Next.js Server Actions / API Routes*: Couples backend business logic to JavaScript; Python is vastly superior for data modeling, scientific calculations, and multi-agent harnesses.

### 2.2. Frontend Framework: Next.js 15 + React 19
- **Choice**: **Next.js 15 (App Router)** with **TypeScript** and **Tailwind CSS v4**
- **Rationale**:
  - Modern App Router architecture allows granular layout composition (separate `/trainer` and `/s/[token]` view layouts).
  - Exceptional mobile rendering performance on Vercel Edge networks.
  - TypeScript ensures strict type safety across API client responses.
- **Alternatives Considered**:
  - *Vite + React SPA*: Lacks built-in edge routing, image optimization, and server component capabilities; requires separate routing libraries.
  - *React Native / Expo*: High barrier to entry for gym clients who refuse to install an app; mobile-browser web apps provide zero-download instant access.

### 2.3. Styling & Ergonomics: Tailwind CSS v4
- **Choice**: **Tailwind CSS v4** with `@tailwindcss/postcss`
- **Rationale**:
  - High velocity for building mobile-first responsive layouts.
  - Direct support for safe-area insets (`env(safe-area-inset-top)`, etc.) and custom touch target utilities (`min-h-[44px]`).
  - Zero runtime overhead: CSS is compiled ahead of time.
- **Alternatives Considered**:
  - *CSS Modules*: Slower development cadence, larger CSS bundle footprint.
  - *UI Component Kits (MUI, Chakra)*: Bloated bundle size, heavy desktop bias, rigid design tokens poorly suited for sweaty-handed gym floor ergonomics.

### 2.4. Database & ORM: PostgreSQL + SQLAlchemy 2.0 (asyncio)
- **Choice**: **PostgreSQL** via **Supabase** with **SQLAlchemy 2.0 (asyncpg/psycopg3)**
- **Rationale**:
  - ACID compliance and relational integrity for financial, trainer, and client records.
  - Native `JSONB` support allows flexible schema evolution for workout plans (`exercises_json`) and agent trace steps (`trace_steps_json`) without sacrificing relational foreign keys.
  - SQLAlchemy 2.0 provides modern typed mappings (`Mapped[T]`) with full async support.
- **Alternatives Considered**:
  - *MongoDB / Document DBs*: Poor relational enforcement; difficult to ensure cascading deletions and client-trainer tenant isolation.
  - *Prisma*: Node.js focused; our backend is natively built in Python.

### 2.5. Authentication Model: Hybrid Supabase JWT + Session Tokens
- **Choice**: **Supabase Auth** for Trainers + **UUIDv4 Cryptographic Session Tokens** for Clients
- **Rationale**:
  - Trainers get secure, compliant identity management (email/password, OAuth, MFA, password reset) out of the box.
  - Clients get zero-friction instant access: a single bookmarked link provides full logging functionality with zero login drop-off.
- **Alternatives Considered**:
  - *Dual Account System (Clients create passwords)*: 40%+ drop-off during client onboarding; frequent forgotten passwords mid-workout.
  - *Magic Links via SMS/Email on every workout*: Excessive friction between sets; requires SMS gateway costs.

### 2.6. AI & Reasoning Engine: Anthropic Claude API
- **Choice**: **Anthropic Claude API** (via `httpx` async client)
  - **Agent 1 (Client Intake & Logging - Front-Facing)**: `claude-sonnet-4-5-20250929` (nuanced conversational reasoning for noisy gym chat/voice inputs, precise set extraction, pain signal detection, and single clarifying questions).
  - **Agent 2 (Progression Safety Cross-Check - Backend)**: `claude-haiku-4-5-20251001` (fast, cost-effective read-only validation; weekly weight deltas are computed deterministically by the Python math engine, so Haiku solely cross-references proposed deltas against logged injury profiles and pain notes).
  - **Agent 3 (Trainer Support & Adherence - Front-Facing)**: `claude-sonnet-4-5-20250929` (high-empathy outreach draft generation, sophisticated multi-client adherence analysis, and contextual triage summaries for the trainer review queue).
- **Rationale**:
  - Superior instruction following and strict adherence to negative boundaries (*"NEVER alter weight integers"*, *"NEVER message clients directly"*).
  - Front-facing user experiences (clients in noisy gyms, trainers reviewing client comms) receive the highest reasoning quality with Sonnet 4.5.
  - Backend progression logic keeps token costs and latency low with Haiku 4.5 because program progression is already deterministic in code.
  - Structured tool calling and reliable JSON outputs.
- **Alternatives Considered**:
  - *OpenAI GPT-4o / GPT-4o-mini*: Viable alternative, but Claude demonstrated higher fidelity in following negative system prompt constraints during evaluation.
  - *Local LLMs (Ollama / Llama 3)*: High GPU infrastructure costs; insufficient concurrency on shared cloud instances.

---

## 3. Dependency Version Matrix

### Backend Dependencies (`backend/pyproject.toml`)

| Package | Version Pin | Purpose | Upgrade Policy |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.115.0` | Asynchronous REST API framework | Minor upgrades permitted |
| `uvicorn[standard]`| `>=0.30.0` | ASGI production server | Minor upgrades permitted |
| `pydantic` | `>=2.0` | Data modeling & schema validation | Pinned to v2.x |
| `pydantic-settings`| `>=2.0` | Environment configuration | Pinned to v2.x |
| `sqlalchemy[asyncio]`| `>=2.0` | Typed async ORM | Pinned to v2.x |
| `psycopg[binary]` | `>=3.1` | Modern async PostgreSQL driver | Minor upgrades permitted |
| `alembic` | `>=1.13` | Database schema migrations | Minor upgrades permitted |
| `pyjwt[crypto]` | `>=2.8` | Supabase JWT token verification | Pinned |
| `httpx` | `>=0.27.0` | Async HTTP client for Anthropic API | Minor upgrades permitted |
| `pytest` | `>=8.0` | Test runner (Dev) | Minor upgrades permitted |
| `pytest-asyncio` | `>=0.23` | Async test fixtures (Dev) | Minor upgrades permitted |
| `ruff` | `>=0.5.0` | Fast Python linter & formatter (Dev)| Rolling latest |

### Frontend Dependencies (`frontend/package.json`)

| Package | Version Pin | Purpose | Upgrade Policy |
| :--- | :--- | :--- | :--- |
| `next` | `^15.0.0` | App Router web framework | Minor upgrades permitted |
| `react` | `^19.0.0` | UI rendering engine | Stable releases |
| `react-dom` | `^19.0.0` | Web DOM bindings | Stable releases |
| `typescript` | `^5.0.0` | Static type checking | Minor upgrades permitted |
| `tailwindcss` | `^4.0.0` | Utility CSS framework | Pinned to v4.x |
| `@tailwindcss/postcss`| `^4.0.0`| PostCSS integration | Pinned to v4.x |
| `@supabase/supabase-js`| `^2.45.0`| Supabase Auth client | Minor upgrades permitted |
| `lucide-react` | `^0.450.0`| Lightweight touch icons | Minor upgrades permitted |

---

## 4. Hosting & Infrastructure Architecture

```
                  ┌────────────────────────────────────────┐
                  │                 DNS                    │
                  │        (e.g., Cloudflare)              │
                  └───────────┬────────────────┬───────────┘
                              │                │
            https://app...    │                │  https://api...
                              ▼                ▼
                     ┌────────────────┐ ┌────────────────┐
                     │     Vercel     │ │     Render     │
                     │  (Next.js 15)  │ │ (Docker/FastAPI)│
                     └────────────────┘ └────────┬───────┘
                                                 │
                                                 ▼
                                        ┌────────────────┐
                                        │    Supabase    │
                                        │  (PostgreSQL)  │
                                        └────────────────┘
```

- **Frontend**: **Vercel** (Global Edge CDN, automatic preview deployments on PRs).
- **Backend**: **Render** (Docker Web Service, auto-deploying from `main` branch).
- **Database & Auth**: **Supabase** (Managed AWS PostgreSQL in `us-east-2`, connection pooled via Supavisor port `6543`).
