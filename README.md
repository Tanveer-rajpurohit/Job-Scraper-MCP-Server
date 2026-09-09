# Job Scraper MCP Server

A self-hosted Model Context Protocol (MCP) server that aggregates job postings across India from **LinkedIn, Indeed, Google Jobs, Adzuna, and Remotive** for Google Gemini Spark.

Designed for automated morning job discovery, targeting SDE-1, junior, intern (2027 grad), fullstack, backend, frontend, creative frontend, and DevOps positions.

---

## 1. Architecture: High-Volume Scraping with Zero Token Bloat

Returning 400+ complete job postings with long descriptions in a single MCP chat response can produce over 1.5 MB of text, risking context window saturation and token limits.

This server solves that by splitting storage and presentation:
1. **Full Dataset to Disk**: Complete scraped records with full descriptions are written directly to dedicated JSON files:
   - `data/mode1.json` (Pan-India sweep)
   - `data/mode2.json` (Location-focused sweep)
   - `data/mode3.json` (Remote sweep)
2. **Fresh Overwrite per Run**: Each time a mode tool runs, it overwrites its respective JSON file with the fresh batch, so previous days' listings never accumulate into stale bloat.
3. **Curated MCP Response**: Gemini Spark receives a clean, lightweight payload containing total counts, file metadata, and a curated preview of the top 20 matching jobs (with direct apply links, salary, and company details).
4. **Paginated Retrieval Tool**: Gemini Spark can inspect full job descriptions in safe chunks (e.g. 20 to 50 items) using the `get_saved_jobs` tool whenever deeper detail is needed.

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
```

### macOS / Linux (Bash / Zsh)

```bash
cd "Job Scraper MCP Server"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
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
MCP_PORT=8000
```

---

## 4. MCP Tools Available to Gemini Spark

### Tool 1: `scrape_jobs_india_all`
- **Scope**: Pan-India sweep across 12 tech search terms matching Tanveer's stack (Go, gRPC, Node.js, TypeScript, React, Next.js, WebRTC, Docker, Kubernetes, AWS, PostgreSQL, Redis, Kafka, RAG).
- **Target Audience**: SDE-1, junior engineer, and 2027 graduate internship roles.
- **Freshness**: Only listings from the last **3 to 4 days** (max 96 hours).
- **Output**: Overwrites `data/mode1.json` with all jobs and returns the top 20 curated previews.

### Tool 2: `scrape_jobs_india_location`
- **Scope**: Location-specific queries for candidates prioritizing local hubs and tier-1 tech cities.
- **Clusters**:
  - **Gujarat Cluster (Primary)**: Ahmedabad, Gandhinagar, Vadodara.
  - **Metro Cluster**: Gurugram, Delhi, Mumbai, Pune.
- **Freshness**: Last **3 to 4 days** (max 96 hours).
- **Candidate Level Filter**: Automatically filters out senior, lead, principal, and 3+ to 10+ years positions, returning only internships, freshers, and 0-2 years SDE-1 roles.
- **Output**: Overwrites `data/mode2.json` with all jobs and returns the complete jobs list in the MCP response.

### Tool 3: `scrape_jobs_remote`
- **Scope**: Remote-first jobs accepting applicants from India, plus global remote roles.
- **Freshness**: Last **3 to 4 days** (max 96 hours).
- **Candidate Level Filter**: Automatically filters out senior, lead, principal, and 3+ to 10+ years positions.
- **Output**: Overwrites `data/mode3.json` with all jobs and returns the complete jobs list in the MCP response.

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

- **`id`**: Deterministic 16-character HMAC-SHA256 signature generated across `title + company + location + date_posted + job_link` using `HMAC_SECRET_KEY`. Deduplication runs internally prior to sending the response.
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
3. The tool directly returns the full list of jobs in JSON and writes/overwrites `data/mode1.json`, `data/mode2.json`, or `data/mode3.json` on disk.

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
   2. Review the top matches and total counts returned in each response.
   3. If more details on specific postings are needed, call get_saved_jobs with mode and offset.
   4. Deduplicate against my Google Sheet 'Seen Jobs' tab using the 'id' field.
   5. Append new jobs to today's date tab and send my morning summary.
   ```
