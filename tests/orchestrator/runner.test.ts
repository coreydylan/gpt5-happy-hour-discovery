import { describe, expect, it } from 'vitest';
import { loadBuilderConfig, resolveWorkflow } from '../../agentkit/orchestrator/config.js';
import { InMemoryStateAdapter } from '../../agentkit/orchestrator/stateMemory.js';
import { createMockAgentRegistry } from '../../agentkit/orchestrator/agents/mockAgents.js';
import { OrchestratorRunner } from '../../agentkit/orchestrator/runner.js';
import { OrchestratorLogger } from '../../agentkit/orchestrator/types.js';

class TestLogger implements OrchestratorLogger {
  constructor(private readonly bindings: Record<string, unknown> = {}) {}

  info(_payload: Record<string, unknown> | string): void {}
  warn(_payload: Record<string, unknown> | string): void {}
  error(_payload: Record<string, unknown> | string, _error?: unknown): void {}
  child(bindings: Record<string, unknown>): OrchestratorLogger {
    return new TestLogger({ ...this.bindings, ...bindings });
  }
}

describe('OrchestratorRunner integration', () => {
  it('runs the happy hour pipeline and updates contract', async () => {
    const config = await loadBuilderConfig();
    const workflow = resolveWorkflow(config, 'happy_hour_pipeline');

    const state = new InMemoryStateAdapter();
    const registry = createMockAgentRegistry();
    const runner = new OrchestratorRunner({
      workflow,
      builder: config,
      state,
      registry,
      logger: new TestLogger(),
    });

    const restaurantSlug = 'dukes-waikiki';
    await runner.run(restaurantSlug);

    const contract = await state.getContract(restaurantSlug);
    expect(contract).not.toBeNull();
    const happyHour = (contract as { happy_hour?: { status?: string } } | null)?.happy_hour;
    expect(happyHour?.status).toBe('confirmed');

    const urlQueue = await state.listQueue('happy_hour_url_queue');
    expect(urlQueue.every((item) => item.status === 'completed')).toBe(true);

    const extractionQueue = await state.listQueue('happy_hour_extraction_queue');
    expect(extractionQueue.every((item) => item.status === 'completed')).toBe(true);
  });
});
