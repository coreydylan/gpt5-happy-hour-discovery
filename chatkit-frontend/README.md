# HHMap ChatKit Frontend

This Next.js application wraps the HHMap AgentKit workflow with OpenAI's ChatKit interface. It provides three core capabilities:

1. **Restaurant Intake** – seed or refresh the canonical happy hour contract stored in Supabase.
2. **Contract Visibility** – view prompt templates and the raw contract JSON in real time.
3. **ChatKit Console** – embed the `openai-chatkit` web component so operators can orchestrate normalization, discovery, and extraction runs.

## Getting Started

```bash
cd chatkit-frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to access the console.

### Required Environment Variables

Create a `.env.local` file in the `chatkit-frontend` directory:

```
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=service-role-key
NEXT_PUBLIC_CHATKIT_API_BASE=/api/chatkit
NEXT_PUBLIC_CHATKIT_SCRIPT_URL=https://cdn.platform.openai.com/deployments/chatkit/chatkit.js
OPENAI_API_KEY=sk-...
CHATKIT_WORKFLOW_ID=wflow_...
CHATKIT_WORKFLOW_VERSION=latest
```

- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` – enable writes to the AgentKit state tables defined in `agentkit/db/create_state_tables.sql`. Grab these from **Supabase → Project Settings → API** (`Project URL`) and **Service key** (service_role).
- `NEXT_PUBLIC_CHATKIT_SCRIPT_URL` – points to the hosted ChatKit web component bundle on OpenAI's CDN.
- `OPENAI_API_KEY` – grants the API route access to `client.beta.chatkit.sessions.create` so the widget can mint client secrets.
- `CHATKIT_WORKFLOW_ID` – workflow identifier deployed in the OpenAI dashboard that powers the hosted ChatKit experience.
- `CHATKIT_WORKFLOW_VERSION` – optional workflow version override (defaults to the latest deployed version when left blank).
- `NEXT_PUBLIC_CHATKIT_API_BASE` – base URL the widget uses for custom API calls (defaults to `/api/chatkit`).

### Supabase Setup & Verification

1. **Apply the state tables.** Use the SQL editor in Supabase or `psql` with the connection string found under **Project Settings → Database → Connection string → URI**:
   ```bash
   cd chatkit-frontend
   psql "$SUPABASE_DB_URL" -f ../agentkit/db/create_state_tables.sql
   ```
   The script creates `restaurant_contracts`, `happy_hour_url_queue`, `happy_hour_extraction_queue`, and `agent_run_logs` with the required indexes.
2. **Document where secrets live.** Store the Supabase URL and service role key in your team's secret manager (e.g., 1Password vault) and paste redacted references in your runbook or wiki.
3. **Verify read/write access.** With `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set, run:
   ```bash
   npm run verify:supabase
   ```
   The script performs a contract upsert, queue inserts, and an agent log write/read cycle, then cleans up the test rows.
4. **Capture proof for the task.** Grab the CLI output (or a Supabase dashboard screenshot) showing the verification rows before cleanup. Re-run with `npm run verify:supabase -- --keep` if you need the rows to persist for screenshots.
5. **Smoke test the API.**
   ```bash
   curl -X POST http://localhost:3000/api/contracts \
     -H "Content-Type: application/json" \
     -d '{"name":"Verification Bistro","location":"Test City","restaurant_slug":"verification-bistro"}'

   curl http://localhost:3000/api/contracts/verification-bistro
   ```
   Confirm the response echoes the stored contract and metadata timestamps.

## API Surface

### `POST /api/contracts`
Seeds or refreshes a happy hour contract using the template in `agentkit/contracts/happy_hour_contract_template.json`. When Supabase is configured the contract is upserted into the `restaurant_contracts` table.

### `GET /api/contracts/[slug]`
Returns the persisted contract for a restaurant. Falls back to the template when Supabase is unavailable.

### `POST /api/chatkit/session`
Creates a ChatKit session via the OpenAI API and returns the short-lived `client_secret` used by the widget.

### `POST /api/chatkit/client-tools`
Handles ChatKit client tool invocations (Normalize, Discover, Extract). Logs the invocation to `agent_run_logs` and pushes URL candidates into `happy_hour_url_queue` when supplied.

### `GET /api/chatkit`
Health endpoint and placeholder for the full ChatKit API. Replace with an AgentKit bridge service once available.

## Wiring to AgentKit

1. Deploy the AgentKit project defined in `agentkit/builder/happy_hour_agents.yaml`.
2. Point the Supabase credentials to the instance used by the AgentKit workflow.
3. Implement a merge service at `CONTRACT_MERGE_URL` so extractor patches reconcile cleanly.
4. Replace the placeholder `/api/chatkit` implementation with a service that conforms to the ChatKit API spec and proxies events into AgentKit runs.

## Roadmap

- Swap the placeholder ChatKit API with a production-ready bridge once OpenAI releases the official SDK helpers.
- Extend `client-tools` to trigger AgentKit workflow runs via REST or queue-based orchestration.
- Display live agent run telemetry by streaming `agent_run_logs` updates into the UI.
- Add authentication and role-based access before exposing the console to operators.
