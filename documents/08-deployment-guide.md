# 08. Deployment & Operations Guide

This guide provides step-by-step instructions for deploying the **Trainer Progression App** to production using **Render** (Backend Docker Container), **Vercel** (Frontend Next.js), and **Supabase** (PostgreSQL & Auth).

---

## 1. Master Environment Variable Catalog

| Variable | Scope | Required | Example / Format | Source & Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `SUPABASE_URL` | Root, Backend | Yes | `https://xyz.supabase.co` | Supabase Dashboard $\to$ Settings $\to$ API. Project API URL. |
| `SUPABASE_ANON_KEY` | Root, Frontend | Yes | `eyJhbGciOi...` | Supabase Dashboard $\to$ Settings $\to$ API. Public client API key. |
| `SUPABASE_JWT_SECRET` | Root, Backend | Yes | `your-secret-hex-string` | Supabase Dashboard $\to$ Settings $\to$ API $\to$ JWT Secret. Used by backend to verify trainer auth tokens. |
| `DATABASE_URL` | Backend | Yes | `postgresql+psycopg://postgres.xyz:[PASS]@aws-0-us-east-2.pooler.supabase.com:6543/postgres` | Supabase Dashboard $\to$ Connect button $\to$ Connection Pooling (port 6543). Direct connection to PostgreSQL. |
| `ANTHROPIC_API_KEY` | Backend | Yes | `sk-ant-api03-...` | Anthropic Console $\to$ API Keys. Powers Agents 1, 2, and 3. |
| `BACKEND_URL` | Root, Backend | Yes | `https://api.yourdomain.com` | Public URL where FastAPI backend is hosted. |
| `FRONTEND_URL` | Root, Backend | Yes | `https://app.yourdomain.com` | Public URL where Next.js frontend is hosted. |
| `CORS_ORIGINS` | Backend | Yes | `https://app.yourdomain.com` | Comma-separated list of allowed frontend origins for CORS headers. |
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Yes | `https://xyz.supabase.co` | Injected into Next.js client bundle for Supabase Auth. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Yes | `eyJhbGciOi...` | Injected into Next.js client bundle for Supabase Auth. |
| `NEXT_PUBLIC_API_URL` | Frontend | Yes | `https://api.yourdomain.com/api/v1` | Base REST API URL used by the frontend HTTP client. |

> [!IMPORTANT]
> **Supabase Connection Pooling Hostname**:
> Always use the Supavisor pooler hostname (`aws-0-us-east-2.pooler.supabase.com:6543`) with `postgresql+psycopg://` as the URI driver scheme. Do **NOT** use the project hostname (`xyz.supabase.co:5432`), as it only accepts HTTPS traffic, not raw PostgreSQL wire protocol.

---

## 2. Supabase Infrastructure Setup

1. **Create Project**: Log into [supabase.com](https://supabase.com) and create a new project (select AWS region closest to your users, e.g., `us-east-2`).
2. **Retrieve API Keys**: Navigate to **Project Settings $\to$ API** to obtain `URL`, `anon public key`, and `JWT Secret`.
3. **Retrieve Database Connection String**: Click the green **"Connect"** button in the header bar. Select **Transaction Pooler (Port 6543)** and copy the connection string. Replace `[YOUR-PASSWORD]` with your database password.
4. **Configure Authentication**: Navigate to **Authentication $\to$ Providers $\to$ Email**. Ensure email sign-in is enabled. Disable email confirmations if you want trainers to test immediately without verifying inboxes.

---

## 3. Backend Deployment: Render (Docker Web Service)

1. **Create Web Service**:
   - Log into [render.com](https://render.com) and click **New + $\to$ Web Service**.
   - Connect your GitHub repository (`trainer-agent-app`).
2. **Configure Service Settings**:
   - **Name**: `trainer-progression-api`
   - **Region**: Same as Supabase (e.g., Ohio / US East).
   - **Branch**: `main` (Production) or `develop` (Staging).
   - **Root Directory**: `backend`
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Instance Type**: Starter or Standard.
3. **Configure Environment Variables**:
   Add the following secrets under the **Environment** tab:
   - `DATABASE_URL` (Supabase connection string with `postgresql+psycopg://`)
   - `SUPABASE_JWT_SECRET`
   - `ANTHROPIC_API_KEY`
   - `CORS_ORIGINS` (e.g., `https://your-frontend.vercel.app`)
   - `DEBUG`: `false`
4. **Configure Health Check**:
   - Set **Health Check Path** to `/health`.
5. **Pre-Deploy Migration Command**:
   - Under **Build & Deploy**, set **Pre-Deploy Command** to:
     ```bash
     alembic upgrade head
     ```
6. **Deploy**: Click **Create Web Service**. Verify logs show:
   ```
   INFO: Uvicorn running on http://0.0.0.0:8000
   ```

---

## 4. Frontend Deployment: Vercel (Next.js)

1. **Import Project**:
   - Log into [vercel.com](https://vercel.com) and click **Add New... $\to$ Project**.
   - Select your GitHub repository (`trainer-agent-app`).
2. **Configure Project Settings**:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click "Edit" and select `frontend`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
3. **Configure Environment Variables**:
   Add the following variables:
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://your-project.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `eyJhbGciOi...`
   - `NEXT_PUBLIC_API_URL`: `https://trainer-progression-api.onrender.com/api/v1`
4. **Deploy**: Click **Deploy**. Vercel will build the Next.js app and assign a production URL (e.g., `https://trainer-progression-app.vercel.app`).
5. **Update Backend CORS**: Return to Render and update `CORS_ORIGINS` with the newly assigned Vercel URL.

---

## 5. Local Development Quickstart

To run the full stack locally for development:

### Step 1: Environment Files
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Fill in real keys in backend/.env and frontend/.env
```

### Step 2: Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Verify: Open `http://localhost:8000/health` $\to$ `{"status": "healthy"}`.

### Step 3: Frontend Setup (Separate Terminal)
```bash
cd frontend
npm install
npm run dev
```
Verify: Open `http://localhost:3000` on your mobile browser or DevTools mobile emulator.

---

## 6. Observability & Production Monitoring

1. **API Health Endpoint**: Automated uptime monitors (Better Uptime, Pingdom, Render Monitor) should ping `GET /health` every 60 seconds.
2. **Agent Trace Audit Table**: Query `agent_traces` to evaluate model latencies and failure rates:
   ```sql
   SELECT agent_name, status, COUNT(*), AVG(execution_time_ms)
   FROM agent_traces
   WHERE created_at > NOW() - INTERVAL '24 hours'
   GROUP BY agent_name, status;
   ```
3. **Structured Server Logs**: Inspect Docker logs in Render dashboard for HTTP exceptions, unhandled schema errors, or Claude API rate limits.
