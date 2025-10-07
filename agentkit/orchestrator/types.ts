import { z } from 'zod';

export const SpawnSchema = z.object({
  queue: z.string(),
  task: z.string(),
});

export type SpawnConfig = z.infer<typeof SpawnSchema>;

export const ParallelSchema = z.object({
  source: z.string(),
  agent: z.string(),
  status_field: z.string().default('status'),
  complete_on: z.enum(['all_terminal', 'queue_empty']).default('queue_empty'),
  batch_size: z.number().int().positive().optional(),
  poll_interval_ms: z.number().int().nonnegative().optional(),
});

export type ParallelConfig = z.infer<typeof ParallelSchema>;

export const StepSuccessSchema = z.object({
  next: z.string().optional(),
  condition: z.string().optional(),
  on_true: z.object({ next: z.string() }).optional(),
  on_false: z.object({ next: z.string() }).optional(),
});

export type StepSuccessConfig = z.infer<typeof StepSuccessSchema>;

export const AgentStepSchema = z.object({
  id: z.string(),
  agent: z.string(),
  spawn: SpawnSchema.optional(),
  success: StepSuccessSchema.optional(),
});

export type AgentStep = z.infer<typeof AgentStepSchema>;

export const ParallelStepSchema = z.object({
  id: z.string(),
  parallel: ParallelSchema,
  success: StepSuccessSchema.optional(),
});

export type ParallelStep = z.infer<typeof ParallelStepSchema>;

export const TerminalStepSchema = z.object({
  id: z.string(),
  terminal: z.boolean().default(true),
});

export type TerminalStep = z.infer<typeof TerminalStepSchema>;

export const WorkflowStepSchema = z.union([AgentStepSchema, ParallelStepSchema, TerminalStepSchema]);

export type WorkflowStep = z.infer<typeof WorkflowStepSchema>;

export const WorkflowSchema = z.object({
  id: z.string(),
  entry: z.string(),
  steps: z.array(WorkflowStepSchema),
});

export type WorkflowConfig = z.infer<typeof WorkflowSchema>;

export const AgentSchema = z.object({
  id: z.string(),
  name: z.string(),
  concurrency: z.number().int().positive().optional(),
  instructions_file: z.string().optional(),
  tools: z.array(z.string()).optional(),
});

export type AgentDescriptor = z.infer<typeof AgentSchema>;

export const BuilderSchema = z.object({
  project: z.string(),
  version: z.string(),
  metadata: z.record(z.any()).optional(),
  state: z.object({
    backend: z.string(),
    config: z.record(z.any()).optional(),
    tables: z.record(
      z.object({
        name: z.string(),
        key: z.string().optional(),
      })
    ),
  }),
  resources: z.record(z.any()).optional(),
  shared_tools: z.array(z.record(z.any())).optional(),
  agents: z.array(AgentSchema),
  workflows: z.array(WorkflowSchema),
});

export type BuilderConfig = z.infer<typeof BuilderSchema>;

export type AgentRunResult = {
  status: 'completed' | 'failed' | 'skipped';
  outputs?: Record<string, unknown>;
  queueItems?: Array<{
    queue: string;
    payload: Record<string, unknown>;
  }>;
  retriesRemaining?: number;
  error?: Error;
  queueUpdate?: Record<string, unknown>;
};

export interface AgentContext {
  restaurantSlug: string;
  state: OrchestratorStateAdapter;
  logger: OrchestratorLogger;
  step: WorkflowStep;
  queueItem?: QueueItem;
}

export type AgentImplementation = (
  ctx: AgentContext
) => Promise<AgentRunResult>;

export interface AgentRegistry {
  get(agentId: string): AgentImplementation | undefined;
}

export interface OrchestratorLogger {
  info(payload: Record<string, unknown> | string): void;
  warn(payload: Record<string, unknown> | string): void;
  error(payload: Record<string, unknown> | string, error?: unknown): void;
  child(bindings: Record<string, unknown>): OrchestratorLogger;
}

export type QueueItem = {
  id: string;
  payload: Record<string, unknown>;
  status: string;
  retries: number;
  lastError?: string;
  createdAt?: string;
  updatedAt?: string;
};

export interface OrchestratorStateAdapter {
  getContract(slug: string): Promise<Record<string, unknown> | null>;
  upsertContract(slug: string, contract: Record<string, unknown>): Promise<void>;
  enqueue(queue: string, payload: Record<string, unknown>): Promise<QueueItem>;
  fetchPending(queue: string, limit: number): Promise<QueueItem[]>;
  markInProgress(queue: string, itemId: string): Promise<void>;
  complete(queue: string, itemId: string, updates?: Record<string, unknown>): Promise<void>;
  fail(queue: string, itemId: string, error: string): Promise<void>;
  listQueue(queue: string): Promise<QueueItem[]>;
  logAgentEvent(event: {
    restaurantSlug: string;
    agentId: string;
    status: string;
    payload?: Record<string, unknown>;
  }): Promise<void>;
}

export const DEFAULT_TERMINAL_STATUSES = new Set(['completed', 'failed', 'skipped']);

export const DEFAULT_POLL_INTERVAL_MS = 1500;
