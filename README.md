# Job Scraper MCP Server

A self-hosted Model Context Protocol (MCP) server that aggregates job postings across India from **LinkedIn, Indeed, Google Jobs, Adzuna, and Remotive** for Google Gemini Spark.

Designed for automated morning job discovery, targeting SDE-1, junior, intern (2027 grad), fullstack, backend, frontend, creative frontend, and DevOps positions.

---

## 1. Architecture: High-Volume Scraping with Zero Token Bloat

Returning 400+ complete job postings with long descriptions in a single MCP chat response can produce over 1.5 MB of text, risking context window saturation and token limits.

This server solves that by splitting storage and presentation:
1. **Full Dataset to Disk (atomic)**: Complete scraped records with full descriptions are written to a temp file and atomically renamed into dedicated JSON files:
   - `data/mode1.json` (Pan-India sweep)
   - `data/mode2.json` (Location-focused sweep)
   - `data/mode3.json` (Remote sweep)
2. **Google Drive Handoff**: The full dataset is uploaded to your Drive folder `gemini spark data` via a Google Apps Script Web App (`drive_webhook.gs`), where Gemini Spark can read it natively with its Google Drive tool.
3. **Fresh Overwrite per Run**: Each time a mode tool runs, it overwrites its respective JSON file with the fresh batch, so previous days' listings never accumulate into stale bloat.
4. **Curated MCP Response**: Gemini Spark receives a clean, lightweight payload containing total counts, Drive upload status, and a curated preview of the top 15 matching jobs (with direct apply links, salary, and company details — no full descriptions).
5. **Paginated Retrieval Tool**: Gemini Spark can inspect full job descriptions in safe chunks (e.g. 20 to 50 items) using the `get_saved_jobs` tool whenever deeper detail is needed.

---

## 2. Quick Start (Virtual Environment Setup & Run)

Never install dependencies globally. Always use a dedicated `.venv`.

### Windows (PowerShell)

```powershell
# 1. Navigate to the project directory
cd "D:\coding\project\ADVANCED\Job Scraper MCP Server"

# 2. Create the virtual environment
python -m venv .venv

# 3. Activate the environment
.venv\Scripts\Activate.ps1

# (If PowerShell blocks script execution, run this once:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment variables
Copy-Item .env.example .env
# Edit .env and paste your Adzuna credentials

# 6. Start the MCP server
python main.py
```

### Windows (Command Prompt - cmd.exe)

```cmd
cd /d "D:\coding\project\ADVANCED\Job Scraper MCP Server"
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
python main.py
python .\test_run.py
```

### macOS / Linux (Bash / Zsh)

```bash
cd "Job Scraper MCP Server"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
python .\test_run.py
```

The server listens on `http://localhost:8000/mcp` by default.

---

## 3. API Credentials & Setup

| Source | Authentication | Cost / Quota | Purpose |
|---|---|---|---|
| **JobSpy** | None (public guest endpoints) | Free, unlimited | Scrapes LinkedIn, Indeed, and Google Jobs (JobSpy only). |
| **Adzuna** | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | Free, 250 calls/day | Official structured job feed for India. |
| **Jooble** | `Jooble_API` / `JOOBLE_API_KEY` | Free (500 calls/day) | Large-scale aggregator across thousands of Indian boards. |
| **Remotive** | None | Free public API | Remote jobs open to international / Indian candidates. |
| **Himalayas** | None | Free public API | Modern remote developer jobs with salary ranges. |
| **Arbeitnow** | None | Free public API | Tech & remote developer jobs from global ATS. |

### Environment Setup (`.env`)

```env
ADZUNA_APP_ID=your_id_here
ADZUNA_APP_KEY=your_key_here
Jooble_API=your_jooble_key_here
HMAC_SECRET_KEY=your_secret_key_here
GOOGLE_DRIVE_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
DRIVE_FOLDER_NAME=gemini spark data
MCP_PORT=8000
```

### Google Drive Webhook Setup (2 minutes, no GCP project)

1. Open [script.google.com](https://script.google.com) → **New project**.
2. Replace the default `Code.gs` content with the contents of [`drive_webhook.gs`](drive_webhook.gs).
3. **Deploy → New deployment → Web app**: Execute as **Me**, access **Anyone**.
4. Copy the deployment URL (`https://script.google.com/macros/s/.../exec`) into `.env` as `GOOGLE_DRIVE_WEBHOOK_URL`.

Leave it empty to skip Drive upload entirely — datasets are still saved locally and reachable via `get_saved_jobs`.

---

## 4. MCP Tools Available to Gemini Spark

### Tool 1: `scrape_jobs_india_all`
- **Scope**: Pan-India sweep across 13 tech search terms matching Tanveer's stack (Go, gRPC, Node.js, TypeScript, React, Next.js, WebRTC, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka, RAG).
- **Target Audience**: SDE-1, junior engineer, and 2027 graduate internship roles.
- **Freshness**: Only listings from the last **3 to 4 days** (max 96 hours).
- **Output**: Atomically overwrites `data/mode1.json`, uploads the full dataset to Google Drive, and returns a lightweight summary with the **top 15 preview jobs** (apply links included, no full descriptions).

### Tool 2: `scrape_jobs_india_location`
- **Scope**: Location-specific queries for candidates prioritizing local hubs and tier-1 tech cities.
- **Quota-aware strategy**: JobSpy (free, unlimited) queries all 7 cities individually — Ahmedabad, Gandhinagar, Vadodara, Delhi, Gurugram, Mumbai, Pune — while quota-limited Adzuna (250 calls/day) and Jooble (500 calls/day) query 4 regional hubs only: **Gujarat, Delhi NCR, Mumbai, Pune**. This cuts their combined API calls by ~50%.
- **Freshness**: Last **3 to 4 days** (max 96 hours).
- **Candidate Level Filter**: Automatically filters out senior, lead, principal, and 3+ to 10+ years positions, returning only internships, freshers, and 0-2 years SDE-1 roles.
- **Output**: Atomically overwrites `data/mode2.json`, uploads to Drive, and returns a lightweight summary with the top 15 preview jobs.

### Tool 3: `scrape_jobs_remote`
- **Scope**: Remote-first jobs accepting applicants from India, plus global remote roles.
- **Freshness**: Last **3 to 4 days** (max 96 hours).
- **Candidate Level Filter**: Automatically filters out senior, lead, principal, and 3+ to 10+ years positions.
- **Output**: Atomically overwrites `data/mode3.json`, uploads to Drive, and returns a lightweight summary with the top 15 preview jobs.

### Lightweight Response Contract

Every mode tool returns the same envelope, keeping the MCP response under a few KB:

```json
{
  "status": "success",
  "mode": "mode1",
  "total_jobs": 142,
  "file_saved": "mode1.json",
  "drive": { "status": "success", "file_name": "mode1_jobs_2026-09-09.json", "drive_link": "https://drive.google.com/file/d/.../view" },
  "preview_count": 15,
  "preview_jobs": [ { "id": "...", "title": "...", "company": "...", "apply_link": "...", "salary": "..." } ],
  "has_more": true,
  "errors": [],
  "note": "Preview shows top 15 of 142 jobs. Full dataset saved to mode1.json and uploaded to Google Drive. Retrieve full records via get_saved_jobs(mode='mode1', offset=N, limit=20)."
}
```

### Tool 4: `get_saved_jobs`
- **Scope**: Allows Gemini Spark to inspect full job descriptions in small, token-safe windows.
- **Arguments**:
  - `mode`: `"mode1"`, `"mode2"`, or `"mode3"`.
  - `offset`: Starting index (e.g. `0`, `50`, `100`).
  - `limit`: Batch size (e.g. `20` or `50`).
- **Output**: Full job objects with complete 2,800-character descriptions.

---

## 5. Normalized Job Structure & HMAC Signature

Each record stored inside `data/mode1.json`, `data/mode2.json`, and `data/mode3.json` has this format:

```json
{
  "id": "ac6545574fb15a07",
  "source": "adzuna",
  "title": "Backend Engineer (Go / Node.js)",
  "company": "Company Name",
  "job_link": "https://www.adzuna.in/land/ad/...",
  "apply_link": "https://company.hire.com/apply/...",
  "company_link": "",
  "description": "Detailed job description text cleanly sanitized and capped at 2,800 characters...",
  "location": "Ahmedabad, Gujarat",
  "date_posted": "2026-09-07",
  "job_type": "fulltime",
  "is_remote": false,
  "salary": "INR 800000-1400000"
}
```

- **`id`**: Deterministic 16-character HMAC-SHA256 signature generated across **normalized title + company** using `HMAC_SECRET_KEY`. Link and date are intentionally excluded because they are aggregator-specific — this way the same job cross-posted on LinkedIn, Indeed, and Adzuna collapses into one record. Deduplication runs internally prior to sending the response.
- **`apply_link`**: Direct applicant link where exposed by JobSpy; defaults to canonical `job_link`.
- **`description`**: HTML markup stripped, whitespace normalized, capped at 2,800 characters to provide rich details for resume/cover letter generation.

---

## 6. Standalone Verification (No MCP or Spark Required)

You can verify scrapers, deduplication, and JSON output with a single terminal command:

```powershell
.venv\Scripts\Activate.ps1
python test_run.py
```

This runs a live query across Adzuna, Remotive, and JobSpy, writes `data/mode1.json` to disk, and prints a verified sample job showing direct apply links and stripped HTML descriptions.

---

## 7. Testing with MCP Inspector

```powershell
.venv\Scripts\Activate.ps1
mcp dev main.py
```

In the Inspector web interface:
1. The server loads with 4 tools: `scrape_jobs_india_all`, `scrape_jobs_india_location`, `scrape_jobs_remote`, and `get_saved_jobs`.
2. Click **Run Tool** on any scraper.
3. The tool returns a lightweight summary (counts, Drive status, top 15 preview) and writes/overwrites `data/mode1.json`, `data/mode2.json`, or `data/mode3.json` on disk.

---

## 7. Connecting to Gemini Spark

1. **Deploy to a host with a public HTTPS endpoint**:
   - **Render.com**: Create a free Web Service. Build command: `pip install -r requirements.txt`, start command: `python main.py`. Add `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in environment variables.
   - **Railway.app** or **Fly.io**: Set start command to `python main.py` and bind `$PORT`.
2. **Add to Gemini**:
   - Open Gemini → **Settings** → **Connected Apps** → **Add custom app**.
   - Enter your public URL: `https://your-deployment.onrender.com/mcp`.
3. **Daily Schedule Prompt in Gemini Spark**:
   ```text
   Every morning at 08:00 AM IST:
   1. Call scrape_jobs_india_all, scrape_jobs_india_location, and scrape_jobs_remote.
   2. Review the preview_jobs and total counts returned in each response.
   3. If more details on specific postings are needed, call get_saved_jobs with mode and offset,
      or read the full dataset from the Google Drive link in the response.
   4. Deduplicate against my Google Sheet 'Seen Jobs' tab using the 'id' field.
   5. Append new jobs to today's date tab and send my morning summary.
   ```
