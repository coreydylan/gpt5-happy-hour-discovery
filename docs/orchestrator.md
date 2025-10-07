# Supabase Queue Runner

The orchestrator CLI executes the AgentKit workflow defined in `agentkit/builder/happy_hour_agents.yaml`. It reads Supabase state tables, advances queue-backed loops, and emits trace logs for every agent step.

## Prerequisites

- Node.js 18+
- Environment variables:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - (optional) `CONTRACT_MERGE_URL` for real extractor/merger integrations
- Supabase schema applied via `agentkit/db/create_state_tables.sql`

If the Supabase environment variables are missing, the CLI falls back to an in-memory adapter so you can exercise the workflow locally without persisting state.

## Commands

```bash
npm install
npm run build
npm run orchestrator -- --slug dukes-waikiki
```

Command options:

- `--slug` / `-s`: restaurant slug to drive the pipeline (required)
- `--workflow` / `-w`: override workflow ID from the builder file
- `--config` / `-c`: path to a different AgentKit builder YAML file

## Runtime Behavior

- Sequential agents (`normalize`, `discover`, `merge`) execute in order and may push tasks into queues.
- Spawn steps rely on the agent response to enqueue work (e.g., discovery supervisor populates `happy_hour_url_queue`).
- Parallel loops (`evaluate_loop`, `extract_loop`) poll Supabase queues, mark tasks in progress, and commit completion/failure with exponential backoff retries.
- Each agent run writes to `agent_run_logs` for observability.
- Logs are emitted via `pino` with JSON records that play nicely with structured log shippers.

## Testing

Run the integration test for the orchestrator engine with:

```bash
npm run test:orchestrator
```

The test exercises the full normalize → merge path using the in-memory state adapter and mock agents, ensuring queue transitions mirror the YAML definition.

