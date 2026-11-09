# 03. User Flows & System Journey Diagrams

This document illustrates the end-to-end user journeys, system state transitions, and multi-agent orchestration flows within the **Trainer Progression App**.

---

## 1. Client Onboarding Flow

How a trainer creates a client record and delivers an instant-access session link without requiring the client to create an account.

```mermaid
flowchart TD
    A["Trainer logs into /trainer via Supabase Auth"] --> B["Navigate to Client Roster"]
    B --> C["Click 'Add New Client'"]
    C --> D["Enter Client Name, Goals, and Intake Injury Notes"]
    D --> E["FastAPI backend creates ClientProfile row"]
    E --> F["Backend generates cryptographically secure ClientSession token"]
    F --> G["Trainer Dashboard displays unique Session URL: /s/:token"]
    G --> H["Trainer copies link and texts/emails it to Client"]
    H --> I["Client opens /s/:token on mobile phone"]
    I --> J["Client bookmarks URL or adds to phone Home Screen"]
    J --> K["Client views active workout program immediately"]
```

---

## 2. Weekly Workout Logging Cycle

The in-gym mobile experience where a client logs training via chat or voice dictation, reviews extracted sets, and commits the log to the database.

```mermaid
flowchart TD
    A["Client opens bookmarked /s/:token on mobile browser"] --> B["Client reads today's prescribed workout plan"]
    B --> C["Client performs exercises in gym"]
    C --> D["Client enters chat message or dictates voice-to-text"]
    D --> E["Frontend auto-saves input to localStorage on every keystroke"]
    E --> F["Client taps 'Send / Log Sets'"]
    F --> G["POST /api/v1/s/:token/log sends message wrapped in CLIENT_CHAT_DATA"]
    G --> H["Workout Logger parses text into structured JSON sets and pain indicators"]
    H --> I{"Did client mention pain or discomfort?"}
    I -- "Yes" --> J["Set pain_flag=true with summarized pain note"]
    I -- "No" --> K["Set pain_flag=false"]
    J --> L["Return extracted sets and flags to mobile UI"]
    K --> L
    L --> M["Frontend renders Inline Confirmation Card under chat"]
    M --> N{"Does client need to edit any values?"}
    N -- "Yes (e.g. voice typo)" --> O["Client taps number and edits inline"]
    N -- "No" --> P["Client taps 'Confirm & Save Log'"]
    O --> P
    P --> Q["WorkoutLog committed to PostgreSQL"]
    Q --> R["localStorage buffer cleared; success checkmark shown"]
```

---

## 3. Weekly Progression & Planning Cycle

How the system combines deterministic weight math with AI safety reasoning to generate a staged weekly plan for trainer review.

```mermaid
flowchart TD
    A["Weekly Planning Trigger (End of Week or Trainer Tap)"] --> B["Fetch all WorkoutLogs for current week"]
    B --> C["Progression Engine executes deterministic Python rules"]
    C --> D{"Did client hit all prescribed sets and reps?"}
    D -- "Yes" --> E["Compute proposed weight: +5 lbs (or +2.5 lbs)"]
    D -- "No (Missed reps)" --> F["Compute proposed weight: Hold current load"]
    E --> G["Assemble ProposedPlan data object"]
    F --> G
    G --> H["Progression Planner receives ProposedPlan + Intake Injuries + Pain Flags"]
    H --> I{"Are there conflicts between proposed weights and pain/injury history?"}
    I -- "Yes (e.g. shoulder pain on bench)" --> J["Generate Safety Alert and recommendation for trainer"]
    I -- "No conflict" --> K["Mark plan as clean progression"]
    J --> L["Create WorkoutPlan record in DRAFT status"]
    K --> L
    L --> M["Draft plan pushed to Trainer Dashboard Triage Queue"]
    M --> N["Awaiting Trainer Human-in-the-Loop Review"]
```

---

## 4. Trainer Dashboard Review & Approval Flow

The trainer's rapid triage and 1-click approval workflow.

```mermaid
flowchart TD
    A["Trainer opens /trainer dashboard"] --> B["Dashboard fetches pending triage items from /api/v1/trainer/dashboard"]
    B --> C["Display scrollable Triage Queue sorted by urgency"]
    C --> D["Review Plan Card: shows previous load, proposed load, and deltas"]
    D --> E{"Are there Progression Planner Safety Warning Badges?"}
    E -- "Yes" --> F["Inspect highlighted injury conflict and pain note"]
    E -- "No" --> G["Standard progression review"]
    F --> H{"Trainer decision on flagged plan"}
    H -- "Accept AI Warning" --> I["Trainer edits weight inline (e.g. hold or deload)"]
    H -- "Dismiss False Positive" --> J["Trainer dismisses badge with 1 tap"]
    G --> K{"Trainer decision on standard plan"}
    I --> L["Tap 'Approve Plan'"]
    J --> L
    K -- "Approve" --> L
    K -- "Adjust" --> I
    L --> M["POST /api/v1/trainer/plans/:id/approve"]
    M --> N["Plan status updated from DRAFT to APPROVED"]
    N --> O["Approved plan becomes active on client's /s/:token view"]
```

---

## 5. End-to-End Agent Orchestration Pipeline

Sequence diagram showing data flow, component boundaries, and Human-in-the-Loop gates across all three agents.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Frontend as Mobile Browser (/s/:token)
    participant API as FastAPI Backend
    participant DB as Supabase PostgreSQL
    participant A1 as Workout Logger
    participant PE as Deterministic Engine
    participant A2 as Progression Planner
    actor Trainer
    participant A3 as Trainer Assistant

    %% Session Logging
    Client->>Frontend: Speaks/types "Squat 225 3x5, Bench 135 3x10 felt shoulder pinch"
    Frontend->>API: POST /s/:token/log (raw text)
    API->>A1: Parse with untrusted XML tags
    A1-->>API: Extracted sets + pain_flag: true (shoulder)
    API-->>Frontend: Render confirmation card
    Client->>Frontend: Taps "Confirm Log"
    Frontend->>API: Commit verified log
    API->>DB: INSERT into workout_logs

    %% Progression Generation
    Note over API,PE: End of training week triggered
    API->>DB: Query week's workout logs
    DB-->>API: Completed sets & reps
    API->>PE: compute_next_week(logged_sets, current_plan)
    PE-->>API: Proposed weights (+5 lbs squat, +5 lbs bench)
    API->>A2: Evaluate ProposedPlan + Injuries + Pain Flags
    A2-->>API: Safety Warning: Block bench +5 lbs due to shoulder pinch
    API->>DB: INSERT into workout_plans (status: DRAFT)

    %% Human in the Loop Review
    Trainer->>API: GET /trainer/dashboard
    API-->>Trainer: Staged plan with safety alert badge
    Trainer->>API: Override bench to hold 135 lbs; Tap "Approve"
    API->>DB: UPDATE workout_plans SET status='APPROVED'

    %% Adherence & Outreach
    API->>A3: Daily background adherence scan
    A3->>DB: Query client check-in timestamps
    A3-->>API: Flag Client B as 4 days inactive; draft check-in message
    Trainer->>API: Review triage queue; approves outreach message
```

---

## 6. In-Workout Pain Flag Escalation Flow

How a casual mention of discomfort is systematically tracked, prevented from causing immediate progression overloads, and surfaced to the coach.

```mermaid
flowchart TD
    A["Client enters chat: 'Knee was aching on lunges'"] --> B["Workout Logger detects pain keyword and anatomy context"]
    B --> C["Workout Logger sets pain_flag: true and summarizes note"]
    C --> D["Database stores pain record in workout_logs.pain_flags_json"]
    D --> E["Weekly planning evaluates client history"]
    E --> F["Progression Planner matches knee note with upcoming lower body program"]
    F --> G["Progression engine proposal marked with SAFETY_CONFLICT flag"]
    G --> H["Trainer dashboard displays warning badge with original quote"]
    H --> I["Trainer makes informed clinical adjustment before approving next week"]
```

---

## 7. Session Link Recovery & Regeneration Flow

How a trainer assists a client who has lost their phone, deleted bookmarks, or requires a session link reset.

```mermaid
flowchart TD
    A["Client contacts trainer: 'I lost my workout link'"] --> B["Trainer logs into /trainer dashboard"]
    B --> C["Trainer searches client roster for client name"]
    C --> D["Trainer opens Client Details panel"]
    D --> E["Trainer clicks 'Regenerate Session Link'"]
    E --> F["Backend creates new ClientSession UUID and deactivates old token"]
    F --> G["Trainer copies new URL: /s/:new_token"]
    G --> H["Trainer texts link to Client"]
    H --> I["Client opens link; all historical logs and active plan intact"]
```
