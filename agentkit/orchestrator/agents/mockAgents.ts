import { AgentImplementation, AgentRegistry, AgentRunResult } from '../types.js';

const URL_QUEUE = 'happy_hour_url_queue';
const EXTRACTION_QUEUE = 'happy_hour_extraction_queue';

const DEFAULT_AGENTS: Record<string, AgentImplementation> = {
  normalizer: async (ctx) => {
    const existing = await ctx.state.getContract(ctx.restaurantSlug);
    if (!existing) {
      const contract = {
        restaurant: {
          slug: ctx.restaurantSlug,
          name: ctx.restaurantSlug.replace(/-/g, ' '),
          status: 'needs_review',
        },
        happy_hour: {
          status: 'unknown',
          evidence: [],
          offers: [],
        },
        metadata: {
          lastUpdatedAt: new Date().toISOString(),
        },
      } satisfies Record<string, unknown>;
      await ctx.state.upsertContract(ctx.restaurantSlug, contract);
      ctx.logger.info({ event: 'contract_initialized', slug: ctx.restaurantSlug });
      return { status: 'completed', outputs: { initialized: true } } satisfies AgentRunResult;
    }

    return { status: 'completed', outputs: { initialized: false } } satisfies AgentRunResult;
  },

  discovery_supervisor: async (ctx) => {
    const slug = ctx.restaurantSlug;
    const baseUrl = slug.replace(/[^a-z0-9]+/gi, '-');

    const queueItems = [
      {
        queue: URL_QUEUE,
        payload: {
          restaurant_slug: slug,
          url: `https://example.com/${baseUrl}/happy-hour`,
          why_interesting: 'Mock discovery result',
          priority: 3,
        },
      },
      {
        queue: URL_QUEUE,
        payload: {
          restaurant_slug: slug,
          url: `https://example.com/${baseUrl}/menu`,
          why_interesting: 'Menu page for extraction consideration',
          priority: 5,
        },
      },
    ];

    ctx.logger.info({ event: 'discovery_spawned', count: queueItems.length });

    return { status: 'completed', queueItems } satisfies AgentRunResult;
  },

  url_evaluator: async (ctx) => {
    const item = ctx.queueItem;
    if (!item) {
      return { status: 'failed', error: new Error('url_evaluator requires queue item') };
    }

    const url = String(item.payload.url);
    const isPromising = /happy-hour|specials|drinks/.test(url);

    const queueItems = isPromising
      ? [
          {
            queue: EXTRACTION_QUEUE,
            payload: {
              restaurant_slug: ctx.restaurantSlug,
              source_url: url,
              instructions: {
                reason: 'Evaluator identified promising URL',
              },
            },
          },
        ]
      : [];

    return {
      status: 'completed',
      outputs: {
        verdict: isPromising ? 'ready_for_extraction' : 'not_relevant',
      },
      queueItems,
      queueUpdate: {
        verdict: isPromising ? 'ready_for_extraction' : 'not_relevant',
      },
    } satisfies AgentRunResult;
  },

  extractor: async (ctx) => {
    const item = ctx.queueItem;
    if (!item) {
      return { status: 'failed', error: new Error('extractor requires queue item') };
    }

    const contract = (await ctx.state.getContract(ctx.restaurantSlug)) ?? {};
    const happyHourPatch = {
      status: 'confirmed',
      schedule: [
        { day: 'monday', opens_at: '16:00', closes_at: '18:00' },
        { day: 'tuesday', opens_at: '16:00', closes_at: '18:00' },
      ],
      offers: [
        {
          type: 'drinks',
          description: 'Half-price cocktails',
        },
        {
          type: 'food',
          description: 'Discounted appetizers',
        },
      ],
      evidence: [
        {
          source_url: item.payload.source_url,
          captured_at: new Date().toISOString(),
        },
      ],
    } satisfies Record<string, unknown>;

    const nextContract = {
      ...contract,
      happy_hour: happyHourPatch,
      metadata: {
        ...(contract as { metadata?: Record<string, unknown> }).metadata,
        lastUpdatedAt: new Date().toISOString(),
      },
    } as Record<string, unknown>;

    await ctx.state.upsertContract(ctx.restaurantSlug, nextContract);

    return {
      status: 'completed',
      outputs: {
        result: happyHourPatch,
      },
      queueUpdate: {
        result: happyHourPatch,
      },
    } satisfies AgentRunResult;
  },

  merger: async (ctx) => {
    const contract = await ctx.state.getContract(ctx.restaurantSlug);
    if (!contract) {
      return {
        status: 'failed',
        error: new Error('No contract available for merge step'),
      } satisfies AgentRunResult;
    }

    const happyHour = (contract as { happy_hour?: Record<string, unknown> }).happy_hour ?? {};
    return {
      status: 'completed',
      outputs: {
        merged: true,
        happyHourStatus: happyHour.status ?? 'unknown',
      },
    } satisfies AgentRunResult;
  },
};

export class MockAgentRegistry implements AgentRegistry {
  private readonly agents = new Map<string, AgentImplementation>();

  constructor(overrides?: Record<string, AgentImplementation>) {
    for (const [id, impl] of Object.entries(DEFAULT_AGENTS)) {
      this.agents.set(id, impl);
    }

    if (overrides) {
      for (const [id, impl] of Object.entries(overrides)) {
        this.agents.set(id, impl);
      }
    }
  }

  get(agentId: string): AgentImplementation | undefined {
    return this.agents.get(agentId);
  }
}

export function createMockAgentRegistry(
  overrides?: Record<string, AgentImplementation>
): MockAgentRegistry {
  return new MockAgentRegistry(overrides);
}
