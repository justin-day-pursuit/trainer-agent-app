# 01. Project Scope & Overview

## 1. Product Vision & Executive Summary

The **Trainer Progression App** is a mobile-browser-first, agentic web application designed for independent personal trainers. 

Today, independent fitness trainers spend an estimated 3 to 8 hours every weekend performing administrative chores: manually reviewing text messages, parsing client workout logs, opening complex spreadsheets, and calculating next week's weights and sets for each client on their roster. When clients train on their own, capturing clean set-by-set data is fraught with friction; clients dislike navigating complex, multi-click mobile forms mid-workout with sweaty hands, often resorting to cryptic text messages ("did bench 135x10, squats felt ok") or logging nothing at all.

This application eliminates spreadsheet programming fatigue and logging friction through a coordinated system of:
1. **Frictionless Voice & Chat Logging**: Clients log training sessions using conversational language or voice-to-text without creating or logging into an app account.
2. **Deterministic Progression Engine**: Mathematical progression rules compute next week's baseline weights transparently with zero LLM hallucination.
3. **AI Safety Cross-Referencing**: Language models cross-reference client-reported pain, fatigue, and historical injuries against proposed progressions to warn trainers before heavy loads are assigned.
4. **Human-in-the-Loop Review**: Trainers maintain absolute clinical and athletic oversight, approving or modifying auto-drafted plans with a single tap.

---

## 2. Target Users & Stakeholders

### Primary User: The Independent Personal Trainer
- **Profile**: Self-employed coaches, private studio trainers, and hybrid (in-person + online) strength coaches managing 10 to 35+ active clients.
- **Key Characteristics**:
  - Values personal client relationships and customized programming over generic cookie-cutter templates.
  - Constrained by time: non-billable administrative hours directly reduce revenue and recovery time.
  - Relies on mobile devices between client sessions on the gym floor; values fast triage over bloated desktop dashboards.
  - Legally and professionally responsible for client safety; demands total transparency and veto power over programming decisions.

### Secondary User: The Personal Training Client
- **Profile**: Everyday fitness clients, strength athletes, and rehabilitation clients training either semi-privately or independently between coaching sessions.
- **Key Characteristics**:
  - Trains in busy gym environments where phone typing is awkward, slow, and prone to typos.
  - Dislikes account creation, password management, and downloading single-purpose native apps.
  - Needs immediate confirmation that their log was captured without tedious form validation errors.
  - Values their trainer's expertise and desires reassurance when experiencing physical discomfort or joint pain.

---

## 3. Core Value Propositions

| Value Proposition | Today's Friction | Trainer Progression App Solution |
| :--- | :--- | :--- |
| **Frictionless In-Gym Logging** | Form fatigue: dropdowns, set selectors, modal popups cause clients to stop logging. | Clients open a bookmarked session link (`/s/:token`) and send a quick chat or voice transcript. The Workout Logger extracts exercise IDs, weights, reps, and pain indicators instantly. |
| **Deterministic Weight Calculations** | Manual spreadsheet formulas take hours, and pure LLM weight generation risks unsafe hallucinated loads. | A modular Python progression engine calculates linear, deload, or custom progression math deterministically. The LLM never invents weights. |
| **Proactive Injury & Pain Triage** | In-workout pain notes get buried in text message threads until an injury occurs or progression fails. | The Progression Planner cross-references recent pain flags against client injury history and flags conflicting weight increases on the trainer's triage queue. |
| **Human-in-the-Loop Oversight** | "Black-box" AI fitness apps disempower the coach and threaten client trust. | All auto-drafted plans remain in draft state until explicitly signed off by the trainer with 1-click approval or inline modification. |
| **Zero-Account Client Identity** | Clients forget login passwords, drop off during onboarding, or abandon native app installs. | Clients use persistent, unguessable session URLs (`/s/:token`). Zero sign-up friction; bookmark once on mobile home screen. |

---

## 4. Business Case & Impact

```
Current Reality:
  20 Clients × 20 mins/week manual spreadsheet planning = ~6.7 hours/week administrative overhead.
  Capacity ceiling capped at ~20-25 clients before programming quality deteriorates.

With Trainer Progression App:
  20 Clients × 5 mins/week 1-click triage & review = ~1.7 hours/week administrative overhead.
  ~5.0 hours saved weekly (75% reduction in administrative time).
  Trainers can scale to 35+ clients while improving safety monitoring and client retention.
```

- **Retention Multiplier**: Proactive check-ins (facilitated by Trainer Assistant adherence tracking) catch disengaged clients before they cancel subscriptions.
- **Safety Assurance**: Systemic logging of pain indicators reduces re-injury rates, protecting trainer liability and client trust.

---

## 5. Scope Boundaries

```
+-----------------------------------------------------------------------------------+
|                                  PROJECT SCOPE                                    |
|                                                                                   |
|  [ IN-SCOPE: MVP FOUNDATION ]                     [ OUT-OF-SCOPE: FUTURE ]        |
|  - Trainer Auth via Supabase                      - Native iOS/Android app store  |
|  - Zero-account Client Session Links (/s/:token)    distribution                  |
|  - Workout Logger: Set & Pain Extraction          - Direct client payment billing |
|  - Deterministic Progression Engine (Protocol)    - Wearable/Smartwatch sync      |
|  - Progression Planner: Safety & Injury Flagging  - In-app video exercise library |
|  - Trainer Review Queue with 1-click approval     - Automated client SMS/email    |
|  - Trainer Assistant: Adherence Monitoring Triage   delivery without trainer approval |
|  - LocalStorage in-gym crash protection           - Complex multi-block periodization |
|  - Mobile-browser-first responsive layouts          (undulating, block, peaking)  |
|  - Comprehensive audit trace logging              - Group workout competitions    |
+-----------------------------------------------------------------------------------+
```

### In-Scope (MVP & Scaffolding)
- **Role-Delimited Access**: Supabase email/password authentication for trainers; cryptographic token routing for client workout sessions.
- **3-Agent Orchestration**: Workout Logger (intake/extraction), Progression Planner (safety analysis), and Trainer Assistant (administrative triage).
- **Client Web UI**: Mobile-first session page supporting natural language chat, quick-tap manual fallback, and real-time offline persistence via `localStorage`.
- **Trainer Web UI**: Responsive dashboard featuring an adherence triage queue, plan approval cards with visual delta indicators, and client session link generation.
- **Modular Progression Architecture**: Clean Python interface allowing linear progression for MVP and future rule engine swap-outs.

### Out-of-Scope (Deferred to Later Iterations)
- **Client Self-Registration**: No passwords, usernames, or account creation for clients.
- **Automated Messaging to Clients**: AI agents never contact clients directly; all messaging outputs are staged drafts requiring trainer approval.
- **Payment & Invoicing**: Billing management remains handled via external trainer systems (Stripe, Venmo, Mindbody).
- **Custom Exercise Video Streaming**: Heavy media storage and video streaming are deferred; exercises are tracked via standardized text identifiers and labels.

---

## 6. Key Architectural Principles

1. **Deterministic Before Generative**: Math belongs in compiled code, not token probabilities. Weights, rep targets, and dates are computed deterministically. LLMs are strictly leveraged for unstructured language understanding, synthesis, and safety reasoning.
2. **Trainer Always Decides (Human-in-the-Loop)**: AI outputs are recommendations and staged drafts. No modification to a client's live workout program or outreach message occurs without human verification.
3. **Mobile First, Not Mobile Ported**: Gym floors are hostile UI environments. All client interfaces prioritize touch targets $\ge 44\text{px}$, high-contrast typography, one-handed interaction zones, and persistent auto-saving.
4. **Prompt Injection Defense by Architecture**: Client inputs are treated as untrusted data wrapped in structured tags (`<CLIENT_CHAT_DATA>`). System prompts forbid interpreting user messages as operational commands.
