# 03. User Flows & System Journey Diagrams

This document illustrates the end-to-end user journeys, system state transitions, and multi-agent orchestration flows within the **Trainer Progression App**.

---

## 1. Dual Client Onboarding & Intake Flow (Option B)

How client profiles and intake information are populated with autonomy for both trainer and client, backed by trainer human-in-the-loop oversight.

```mermaid
flowchart TD
    subgraph TrainerPath ["Trainer Intake & Setup"]
        T1["Trainer logs into /trainer via Supabase Auth"] --> T2["Navigate to Client Roster"]
        T2 --> T3["Click 'Add New Client' (or use Trainer Assistant)"]
        T3 --> T4["Enter Client Name, Initial Goals & Injury Notes"]
        T4 --> T5["FastAPI creates ClientProfile row"]
        T5 --> T6["Backend generates cryptographic ClientSession token (/s/:token)"]
        T6 --> T7["Trainer shares session link with Client"]
    end

    subgraph ClientPath ["Client Mobile Intake & Updates"]
        C1["Client opens /s/:token on mobile browser"] --> C2["View Active Program & Intake Profile"]
        C2 --> C3["Client chats with Workout Logger to refine goals/injuries"]
        C3 --> C4["Workout Logger extracts updated goals or injury alerts"]
        C4 --> C5["Profile updated with client-reported injury notes"]
    end

    subgraph TrainerOversight ["Human-in-the-Loop Oversight"]
        T7 --> C1
        C5 --> O1["Trainer Dashboard surfaces client profile updates"]
        O1 --> O2["Trainer manually reviews, edits, or overrides goals/injuries"]
    end
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

How `EffortBasedProgression` drafts next week's weights and reps, and how the planner flags a held lift for the trainer to review. The planner does not change the numbers.

```mermaid
flowchart TD
    A["Weekly Planning Trigger (End of Week or Trainer Tap)"] --> B["Fetch all WorkoutLogs for current week"]
    B --> C["EffortBasedProgression drafts each exercise on its own"]
    C --> D{"Pain, missed reps, a missing set, challenging, or no effort?"}
    D -- "Yes" --> E["Hold the weight and the reps"]
    D -- "No, the effort was easy" --> F{"Target reps and load"}
    F -- "Under 12 reps" --> G["Keep the weight and add 2 reps, cap 12"]
    F -- "12 reps with a weight" --> H["Add 5 lb and reset reps to 8"]
    F -- "12 bodyweight reps" --> I["Hold. The trainer decides"]
    E --> J["Assemble the drafted plan"]
    G --> J
    H --> J
    I --> J
    J --> K["Planner reviews held, pain-free, same-weight lifts"]
    K --> L{"Is this a held, pain-free, same-weight lift?"}
    L -- "Yes" --> M["Add a trainer flag. Leave the drafted numbers alone"]
    L -- "No" --> N["No planner flag. An increase is not blocked"]
    M --> O["Create WorkoutPlan record in DRAFT status"]
    N --> O
    O --> P["Draft plan pushed to Trainer Dashboard Triage Queue"]
    P --> Q["Awaiting Trainer Human-in-the-Loop Review"]
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
    Client->>Frontend: Speaks/types "Squat was easy, hit every set. Bench felt challenging, no pain"
    Frontend->>API: POST /s/:token/log (raw text)
    API->>A1: Parse with untrusted XML tags
    A1-->>API: Extracted sets. Squat effort easy. Bench effort challenging. No pain
    API-->>Frontend: Render confirmation card
    Client->>Frontend: Taps "Confirm Log"
    Frontend->>API: Commit verified log
    API->>DB: INSERT into workout_logs

    %% Progression Generation
    Note over API,PE: End of training week triggered
    API->>DB: Query week's workout logs
    DB-->>API: Completed sets, reps, and effort
    API->>PE: compute_next_week(logged_sets, current_plan)
    PE-->>API: Reps-first draft. Easy squat under 12 gains 2 reps. Challenging bench holds weight and reps
    API->>A2: Review held, pain-free, same-weight lifts
    A2-->>API: Flag the held bench for the trainer. Drafted numbers stay unchanged
    API->>DB: INSERT into workout_plans (status: DRAFT)

    %% Human in the Loop Review
    Trainer->>API: GET /trainer/dashboard
    API-->>Trainer: Staged plan with a held-lift flag
    Trainer->>API: Reviews the held bench flag; Tap "Approve"
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
