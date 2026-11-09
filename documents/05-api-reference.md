# 05. REST API Reference

The **Trainer Progression App** backend exposes a modern, asynchronous RESTful API powered by **FastAPI**. 

- **Base URL**: `http://localhost:8000` (Local) / `https://api.yourdomain.com` (Production)
- **API Version Namespace**: `/api/v1`
- **Interactive OpenAPI Documentation**: `/docs` (Swagger UI) and `/redoc` (ReDoc)

---

## 1. Authentication & Security Architecture

The API uses two distinct authentication mechanisms depending on the caller's role:

```
+───────────────────────────────────+───────────────────────────────────+
│       TRAINER AUTHENTICATION      │       CLIENT AUTHENTICATION       │
+───────────────────────────────────+───────────────────────────────────+
│ Mechanism: Supabase JWT           │ Mechanism: Cryptographic UUID     │
│ Header: Authorization: Bearer <jwt>│ URL Path: /api/v1/s/:token/...   │
│ Scope: /api/v1/clients/*          │ Scope: /api/v1/s/:token           │
│        /api/v1/trainer/*          │        /api/v1/s/:token/log       │
│        /api/v1/workouts/*         │        /api/v1/s/:token/progress  │
│ Account required: YES             │ Account required: NO (Link only)  │
+───────────────────────────────────+───────────────────────────────────+
```

---

## 2. Health & System Status

### `GET /health`
Returns system health, database status, and uptime verification.

- **Authentication**: None (Public)
- **Response**: `200 OK`
```json
{
  "status": "ok",
  "service": "Trainer Progression API",
  "environment": "development"
}
```

---

## 3. Client Session Link Endpoints (Client Role)

Endpoints accessed by clients on mobile browsers using their secret session link token.

### 3.1. `GET /api/v1/s/{token}`
Validates the client's session token and retrieves their profile name and active prescribed workout program.

- **Authentication**: Valid `session_token` in path
- **Response**: `200 OK`
```json
{
  "client_name": "Sarah Miller",
  "token": "1be250aa-58a4-47d8-b117-29fdff768cd5",
  "active_plan": {
    "id": 42,
    "week_label": "2026-W45",
    "exercises": [
      {
        "exercise_id": "ex_bench",
        "name": "Barbell Bench Press",
        "sets": 3,
        "target_reps": 10,
        "target_weight_lbs": 135.0
      },
      {
        "exercise_id": "ex_squat",
        "name": "Back Squat",
        "sets": 3,
        "target_reps": 8,
        "target_weight_lbs": 185.0
      }
    ]
  }
}
```
- **Error States**:
  - `401 Unauthorized`: Token is inactive or invalid.

---

### 3.2. `POST /api/v1/s/{token}/log/preview`
Parses client voice or chat text using Agent 1 without committing to the database. Returns structured preview sets and flags for client inline review.

- **Authentication**: Valid `session_token` in path
- **Request Body** (`application/json`):
```json
{
  "plan_id": 42,
  "raw_input": "Did bench 135 for 3 sets of 10. Shoulder was pinching on set 3."
}
```
- **Response**: `200 OK`
```json
{
  "status": "complete",
  "extracted_sets": [
    {
      "exercise_id": "ex_bench",
      "set_num": 1,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 2,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 3,
      "reps": 8,
      "weight_lbs": 135.0,
      "pain_flag": true,
      "note": "Shoulder pinching on final reps"
    }
  ],
  "clarifying_question": null,
  "has_pain_flag": true,
  "pain_summary": "Shoulder discomfort noted on Bench Press",
  "model_name": "claude-sonnet-4-5-20250929",
  "execution_time_ms": 240.5
}
```

---

### 3.3. `POST /api/v1/s/{token}/log`
Commits the client-confirmed workout log to the database. Requires a client-generated UUID `client_request_id` for idempotency protection (returns HTTP 409 Conflict if already recorded).

- **Authentication**: Valid `session_token` in path
- **Request Body** (`application/json`):
```json
{
  "plan_id": 42,
  "client_request_id": "550e8400-e29b-41d4-a716-446655440000",
  "raw_input": "Did bench 135 for 3 sets of 10. Shoulder was pinching on set 3.",
  "confirmed_sets": [
    {
      "exercise_id": "ex_bench",
      "set_num": 1,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 2,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 3,
      "reps": 8,
      "weight_lbs": 135.0,
      "pain_flag": true,
      "note": "Shoulder pinching on final reps"
    }
  ],
  "has_pain_flag": true,
  "pain_summary": "Shoulder discomfort noted on Bench Press"
}
```
- **Response**: `201 Created`
```json
{
  "id": 108,
  "client_id": 12,
  "plan_id": 42,
  "client_request_id": "550e8400-e29b-41d4-a716-446655440000",
  "raw_input": "Did bench 135 for 3 sets of 10. Shoulder was pinching on set 3.",
  "extracted_sets": [
    {
      "exercise_id": "ex_bench",
      "set_num": 1,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 2,
      "reps": 10,
      "weight_lbs": 135.0,
      "pain_flag": false,
      "note": "Completed clean"
    },
    {
      "exercise_id": "ex_bench",
      "set_num": 3,
      "reps": 8,
      "weight_lbs": 135.0,
      "pain_flag": true,
      "note": "Shoulder pinching on final reps"
    }
  ],
  "has_pain_flag": true,
  "pain_summary": "Shoulder discomfort noted on Bench Press",
  "logged_at": "2026-11-08T03:30:00Z"
}
```
- **Error States**:
  - `409 Conflict`: A workout log with this `client_request_id` has already been recorded.

---

### 3.4. `GET /api/v1/s/{token}/progress`
Retrieves past workout log history for client self-monitoring on mobile.

- **Authentication**: Valid `session_token` in path
- **Response**: `200 OK`
```json
{
  "client_id": 12,
  "recent_logs": [
    {
      "id": 108,
      "logged_at": "2026-11-08T03:30:00Z",
      "sets": [...],
      "has_pain_flag": true
    }
  ]
}
```

---

## 4. Client Management Endpoints (Trainer Role)

Endpoints for managing client profiles and generating session links. Requires Supabase JWT.

### 4.1. `POST /api/v1/clients`
Creates a new client profile under the trainer's roster.

- **Authentication**: `Bearer <supabase_jwt>`
- **Request Body**:
```json
{
  "full_name": "Marcus Vance",
  "email": "marcus@example.com",
  "phone": "+15551234567",
  "primary_goal": "Strength & Hypertrophy",
  "experience_level": "Intermediate",
  "injuries": [
    "Right ACL reconstruction (2022)",
    "Mild lower back stiffness"
  ],
  "intake_notes": "Client wants to improve squat strength while protecting knees."
}
```
- **Response**: `201 Created`
```json
{
  "id": 15,
  "trainer_id": 1,
  "full_name": "Marcus Vance",
  "email": "marcus@example.com",
  "phone": "+15551234567",
  "primary_goal": "Strength & Hypertrophy",
  "experience_level": "Intermediate",
  "injuries": ["Right ACL reconstruction (2022)", "Mild lower back stiffness"],
  "intake_notes": "Client wants to improve squat strength while protecting knees.",
  "created_at": "2026-11-08T03:30:00Z",
  "updated_at": "2026-11-08T03:30:00Z"
}
```

---

### 4.2. `GET /api/v1/clients`
Retrieves all clients belonging to the authenticated trainer.

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `200 OK` (Array of `ClientProfileResponse` objects)

---

### 4.3. `GET /api/v1/clients/{client_id}`
Retrieves a single client profile by ID.

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `200 OK` (`ClientProfileResponse`)
- **Error States**: `404 Not Found`

---

### 4.4. `POST /api/v1/clients/{client_id}/sessions`
Generates a new, non-guessable cryptographic session link URL for a client. Deactivates previous tokens if regenerated.

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `201 Created`
```json
{
  "session_token": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "session_url": "http://localhost:3000/s/f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "created_at": "2026-11-08T03:30:00Z",
  "is_active": true
}
```

---

## 5. Trainer Dashboard & Approval Endpoints

Endpoints powering the trainer's weekly review feed, triage alerts, and Human-in-the-Loop plan approvals.

### 5.1. `GET /api/v1/trainer/dashboard`
Fetches all pending workout plan drafts awaiting review, accompanied by Agent 3 triage cards.

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `200 OK`
```json
{
  "pending_approval_count": 3,
  "pending_plans": [
    {
      "id": 43,
      "client_id": 12,
      "week_label": "2026-W46",
      "status": "draft",
      "exercises_json": [
        {
          "exercise_id": "bench_press",
          "name": "Barbell Bench Press",
          "target_sets": 3,
          "target_reps": 10,
          "target_weight_lbs": 135.0
        }
      ],
      "safety_flags_json": [
        {
          "severity": "warning",
          "message": "Shoulder pinching reported last week. Weight held at 135 lbs."
        }
      ]
    }
  ],
  "triage_cards": [
    {
      "client_id": 12,
      "client_name": "Sarah Miller",
      "urgency": "high",
      "reason": "Shoulder pinching reported on Bench Press set 3. Progression held for safety.",
      "recommended_action": "Review shoulder notes and approve or modify Bench Press load.",
      "draft_message": "Hey Sarah, noticed your shoulder felt tight on Bench Press. How is it feeling today?"
    }
  ]
}
```

---

### 5.2. `POST /api/v1/trainer/plans/{plan_id}/approve`
**The Human-in-the-Loop Checkpoint Gate**. Signs off on a staged draft plan, changing its status to `approved` and releasing it to the client's mobile session.

- **Authentication**: `Bearer <supabase_jwt>`
- **Request Body** (Optional overrides):
```json
{
  "trainer_notes": "Great work this week. Keeping bench at 135 to let that shoulder recover."
}
```
- **Response**: `200 OK`
```json
{
  "id": 43,
  "client_id": 12,
  "week_label": "2026-W46",
  "status": "approved",
  "approved_at": "2026-11-08T03:35:00Z"
}
```

---

### 5.3. `GET /api/v1/trainer/alerts`
Retrieves Agent 3 compliance and adherence alerts (e.g., missed sessions, inactive clients).

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `200 OK` (Array of alerts with urgency levels)

---

## 6. Workout Management Endpoints

### 6.1. `GET /api/v1/workouts/{client_id}/current`
Fetches the active approved workout plan for a given client.

- **Authentication**: `Bearer <supabase_jwt>`
- **Response**: `200 OK` (`WorkoutPlanResponse`)

---

### 6.2. `POST /api/v1/workouts/{client_id}/plans`
Manually drafts or updates a workout plan for a client.

- **Authentication**: `Bearer <supabase_jwt>`
- **Request Body**:
```json
{
  "week_label": "2026-W46",
  "exercises": [
    {
      "exercise_id": "back_squat",
      "name": "Back Squat",
      "target_sets": 3,
      "target_reps": 8,
      "target_weight_lbs": 190.0
    }
  ]
}
```
- **Response**: `201 Created`

---

## 7. Standard Error Responses

All endpoints adhere to RFC 7807 structured HTTP error representations:

```json
{
  "detail": "Descriptive human-readable error explanation."
}
```

| HTTP Status | Reason |
| :--- | :--- |
| `400 Bad Request` | Missing required payload attributes or malformed data. |
| `401 Unauthorized` | Invalid or expired Supabase JWT token, or missing session token. |
| `403 Forbidden` | Authenticated trainer does not own the requested client record. |
| `404 Not Found` | Requested client, session link, or workout plan does not exist. |
| `422 Unprocessable` | Pydantic validation failure on schema types or fields. |
| `500 Server Error` | Uncaught server exception or database connectivity issue. |
