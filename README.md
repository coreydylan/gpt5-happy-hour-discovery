# HHMap AgentKit (2025 Reboot)

This repository has been reset around the AgentKit + ChatKit stack. All legacy Lambda/orchestrator implementations now live under `archive/` for reference.

## Active Workspace
- `agentkit/` – canonical JSON schema, prompts, Supabase tables, and the `happy_hour_agents.yaml` workflow.
- `agentkit/connectors/` – concrete implementations for workflow tool IDs (see `docs/connectors.md` for setup and smoke tests).
- `chatkit-frontend/` – Next.js console embedding the ChatKit web component and session bridge.
- `AGENTKIT_PROGRESS.md` – historical summary & current status.
- `HHMAP_ROADMAP.md` – forward-looking plan of record.

## Legacy Artifacts
- `archive/legacy/` – previous Lambda, Supabase, and discovery code paths (kept locally; Git ignores the contents so stash your snapshot here as needed).
- `archive/tooling/` – third-party repos (e.g., ChatKit JS, Agents SDK) preserved for reference.

## Getting Started
1. Review `HHMAP_ROADMAP.md` for objectives and immediate tasks.
2. Follow `chatkit-frontend/README.md` to bring up the operator console.
3. Update `.env.local` with Supabase credentials and OpenAI keys (see `chatkit-frontend/README.md` for the exact values and secret locations).
4. Apply `agentkit/db/create_state_tables.sql` to your Supabase project and run `npm run verify:supabase` from `chatkit-frontend/` to confirm the state tables are writable.

## Notes
- Historical assets stay accessible via `archive/` and Git history; the full legacy snapshot can also live in `archive/legacy/` locally without affecting commits.
- Hosted AgentKit deployment is optional until OpenAI exposes the public CLI/API.
- Keep `AGENTKIT_PROGRESS.md` updated as milestones land.
