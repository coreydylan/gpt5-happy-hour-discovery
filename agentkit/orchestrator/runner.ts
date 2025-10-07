import {
  AgentContext,
  AgentImplementation,
  AgentRegistry,
  AgentRunResult,
  AgentStep,
  BuilderConfig,
  DEFAULT_POLL_INTERVAL_MS,
  DEFAULT_TERMINAL_STATUSES,
  OrchestratorLogger,
  OrchestratorStateAdapter,
  ParallelStep,
  QueueItem,
  TerminalStep,
  WorkflowConfig,
  WorkflowStep,
} from './types.js';
import { sleep } from './utils/sleep.js';

interface RunnerOptions {
  workflow: WorkflowConfig;
  builder: BuilderConfig;
  state: OrchestratorStateAdapter;
  registry: AgentRegistry;
  logger: OrchestratorLogger;
  pollIntervalMs?: number;
  maxAgentRetries?: number;
}

export class OrchestratorRunner {
  private readonly workflow: WorkflowConfig;
  private readonly builder: BuilderConfig;
  private readonly state: OrchestratorStateAdapter;
  private readonly registry: AgentRegistry;
  private readonly logger: OrchestratorLogger;
  private readonly pollIntervalMs: number;
  private readonly maxAgentRetries: number;
  private readonly stepMap: Map<string, WorkflowStep>;
  private readonly agentConcurrency = new Map<string, number>();

  constructor(options: RunnerOptions) {
    this.workflow = options.workflow;
    this.builder = options.builder;
    this.state = options.state;
    this.registry = options.registry;
    this.logger = options.logger;
    this.pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
    this.maxAgentRetries = options.maxAgentRetries ?? 3;
    this.stepMap = new Map(options.workflow.steps.map((step) => [step.id, step]));

    for (const agent of options.builder.agents) {
      if (agent.concurrency) {
        this.agentConcurrency.set(agent.id, agent.concurrency);
      }
    }
  }

  async run(restaurantSlug: string): Promise<void> {
    let currentStepId = this.workflow.entry;
    const visited = new Set<string>();

    while (currentStepId) {
      if (visited.has(currentStepId)) {
        this.logger.warn({ event: 'loop-detected', step: currentStepId, restaurantSlug });
      }
      visited.add(currentStepId);

      const step = this.stepMap.get(currentStepId);
      if (!step) {
        throw new Error(`Workflow step ${currentStepId} not found`);
      }

      if (isTerminalStep(step)) {
        this.logger.info({ event: 'terminal-step-reached', step: currentStepId, restaurantSlug });
        break;
      }

      if (isAgentStep(step)) {
        const result = await this.runAgentStep(step, restaurantSlug);
        const next = await this.resolveNextStep(step.success, restaurantSlug, result);
        if (!next || next === 'finished') {
          break;
        }
        currentStepId = next;
        continue;
      }

      if (isParallelStep(step)) {
        await this.runParallelStep(step, restaurantSlug);
        const next = await this.resolveNextStep(step.success, restaurantSlug);
        if (!next || next === 'finished') {
          break;
        }
        currentStepId = next;
        continue;
      }

      throw new Error(`Unsupported step configuration for ${currentStepId}`);
    }
  }

  private async runAgentStep(step: AgentStep, restaurantSlug: string): Promise<AgentRunResult> {
    const agent = this.registry.get(step.agent);
    if (!agent) {
      throw new Error(`Agent ${step.agent} is not registered`);
    }

    const scopedLogger = this.logger.child({ step: step.id, agent: step.agent, restaurantSlug });

    await this.state.logAgentEvent({
      restaurantSlug,
      agentId: step.agent,
      status: 'started',
      payload: { stepId: step.id },
    });

    scopedLogger.info({ event: 'agent-start' });

    const result = await this.executeWithRetries(agent, {
      restaurantSlug,
      state: this.state,
      logger: scopedLogger,
      step,
    });

    scopedLogger.info({ event: 'agent-finished', status: result.status });

    await this.state.logAgentEvent({
      restaurantSlug,
      agentId: step.agent,
      status: result.status,
      payload: result.outputs ?? {},
    });

    const queueItems = this.prepareQueueItems(step, result.queueItems);
    for (const item of queueItems) {
      await this.state.enqueue(item.queue, {
        restaurant_slug: restaurantSlug,
        ...item.payload,
      });
    }

    if (result.status === 'failed') {
      throw result.error ?? new Error(`Agent ${step.agent} failed`);
    }

    return result;
  }

  private async runParallelStep(step: ParallelStep, restaurantSlug: string): Promise<void> {
    const queueName = step.parallel.source;
    const agentId = step.parallel.agent;
    const agent = this.registry.get(agentId);
    if (!agent) {
      throw new Error(`Agent ${agentId} is not registered`);
    }

    const concurrency = step.parallel.batch_size ?? this.agentConcurrency.get(agentId) ?? 4;
    const pollInterval = step.parallel.poll_interval_ms ?? this.pollIntervalMs;
    const scopedLogger = this.logger.child({ step: step.id, agent: agentId, restaurantSlug });

    scopedLogger.info({ event: 'parallel-start', queue: queueName, concurrency });

    while (true) {
      const items = await this.state.fetchPending(queueName, concurrency);

      if (items.length === 0) {
        const done = await this.isParallelComplete(queueName, step.parallel.complete_on ?? 'queue_empty');
        if (done) {
          scopedLogger.info({ event: 'parallel-complete' });
          break;
        }
        await sleep(pollInterval);
        continue;
      }

      await Promise.all(
        items.map(async (item) => {
          await this.state.markInProgress(queueName, item.id);
          await this.processParallelItem({
            queueName,
            agent,
            agentId,
            restaurantSlug,
            item,
            step,
            logger: scopedLogger.child({ queueItemId: item.id }),
          });
        })
      );
    }
  }

  private async processParallelItem(params: {
    queueName: string;
    agent: AgentImplementation;
    agentId: string;
    restaurantSlug: string;
    item: QueueItem;
    step: ParallelStep;
    logger: OrchestratorLogger;
  }): Promise<void> {
    const { queueName, agent, agentId, restaurantSlug, item, step, logger } = params;

    let result: AgentRunResult;
    try {
      result = await this.executeWithRetries(agent, {
        restaurantSlug,
        state: this.state,
        logger,
        step,
        queueItem: item,
      });
    } catch (error) {
      await this.state.fail(queueName, item.id, (error as Error)?.message ?? 'Agent failed');
      await this.state.logAgentEvent({
        restaurantSlug,
        agentId,
        status: 'failed',
        payload: {
          queueItemId: item.id,
          error: error instanceof Error ? error.message : String(error),
        },
      });
      throw error;
    }

    logger.info({ event: 'queue-item-processed', status: result.status });

    if (result.queueItems?.length) {
      for (const nextItem of result.queueItems) {
        await this.state.enqueue(nextItem.queue, {
          restaurant_slug: restaurantSlug,
          ...nextItem.payload,
        });
      }
    }

    if (result.status === 'completed' || result.status === 'skipped') {
      await this.state.complete(queueName, item.id, result.queueUpdate);
      await this.state.logAgentEvent({
        restaurantSlug,
        agentId,
        status: result.status,
        payload: result.outputs ?? {},
      });
      return;
    }

    await this.state.fail(queueName, item.id, result.error?.message ?? 'Agent failed');
    await this.state.logAgentEvent({
      restaurantSlug,
      agentId,
      status: 'failed',
      payload: {
        queueItemId: item.id,
        error: result.error?.message ?? 'Unknown error',
      },
    });
  }

  private async executeWithRetries(agent: AgentImplementation, context: AgentContext): Promise<AgentRunResult> {
    let attempt = 0;
    let delay = 750;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      attempt += 1;
      try {
        const result = await agent(context);
        if (result.status === 'failed' && this.shouldRetry(attempt, result.retriesRemaining)) {
          await sleep(delay);
          delay = Math.min(delay * 2, 5000);
          continue;
        }
        return result;
      } catch (error) {
        if (!this.shouldRetry(attempt, undefined)) {
          throw error instanceof Error ? error : new Error(String(error));
        }
        await sleep(delay);
        delay = Math.min(delay * 2, 5000);
      }
    }
  }

  private shouldRetry(attempt: number, retriesRemaining?: number): boolean {
    if (retriesRemaining !== undefined) {
      return retriesRemaining > 0;
    }
    return attempt <= this.maxAgentRetries;
  }

  private async resolveNextStep(
    success: AgentStep['success'] | ParallelStep['success'] | undefined,
    restaurantSlug: string,
    result?: AgentRunResult
  ): Promise<string | undefined> {
    if (!success) {
      return undefined;
    }

    if (success.condition) {
      const satisfied = await this.evaluateCondition(success.condition, restaurantSlug, result);
      if (satisfied) {
        return success.on_true?.next ?? success.next;
      }
      return success.on_false?.next ?? success.next;
    }

    return success.next;
  }

  private async evaluateCondition(
    expression: string,
    restaurantSlug: string,
    result?: AgentRunResult
  ): Promise<boolean> {
    if (expression.trim() === "contract.happy_hour.status == 'confirmed'") {
      const contract = await this.state.getContract(restaurantSlug);
      const status = (contract as { happy_hour?: { status?: string } } | null)?.happy_hour?.status;
      return status === 'confirmed';
    }

    if (expression.trim() === 'result.status == "completed"') {
      return result?.status === 'completed';
    }

    this.logger.warn({ event: 'unsupported-condition', expression });
    return false;
  }

  private async isParallelComplete(queueName: string, mode: 'queue_empty' | 'all_terminal'): Promise<boolean> {
    const items = await this.state.listQueue(queueName);

    if (mode === 'queue_empty') {
      return items.every((item) => item.status !== 'pending' && item.status !== 'in_progress');
    }

    if (mode === 'all_terminal') {
      return items.every((item) => DEFAULT_TERMINAL_STATUSES.has(item.status));
    }

    return false;
  }

  private prepareQueueItems(step: AgentStep, queueItems?: QueueItemPayload[]): QueueItemPayload[] {
    const spawn = step.spawn;

    if (!queueItems || queueItems.length === 0) {
      if (spawn) {
        this.logger.warn({
          event: 'spawn-step-no-queue-items',
          step: step.id,
          agent: step.agent,
        });
      }
      return [];
    }

    if (!spawn) {
      return queueItems;
    }

    return queueItems.map((item) => {
      if (item.queue && item.queue !== spawn.queue) {
        return item;
      }
      return {
        queue: item.queue ?? spawn.queue,
        payload: {
          task: spawn.task,
          ...item.payload,
        },
      } satisfies QueueItemPayload;
    });
  }
}

type QueueItemPayload = {
  queue: string;
  payload: Record<string, unknown>;
};

function isAgentStep(step: WorkflowStep): step is AgentStep {
  return (step as AgentStep).agent !== undefined;
}

function isParallelStep(step: WorkflowStep): step is ParallelStep {
  return (step as ParallelStep).parallel !== undefined;
}

function isTerminalStep(step: WorkflowStep): step is TerminalStep {
  return (step as TerminalStep).terminal !== undefined;
}
