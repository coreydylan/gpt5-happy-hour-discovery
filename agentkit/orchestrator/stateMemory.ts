import { nanoid } from './utils/nanoid.js';
import { OrchestratorStateAdapter, QueueItem } from './types.js';

interface QueueRecord {
  id: string;
  queue: string;
  payload: Record<string, unknown>;
  status: string;
  retries: number;
  createdAt: string;
  updatedAt: string;
  lastError?: string;
}

export class InMemoryStateAdapter implements OrchestratorStateAdapter {
  private readonly contracts = new Map<string, Record<string, unknown>>();
  private readonly queues = new Map<string, QueueRecord[]>();
  private readonly logs: Array<Record<string, unknown>> = [];

  constructor(initial?: { contracts?: Record<string, Record<string, unknown>> }) {
    if (initial?.contracts) {
      for (const [slug, contract] of Object.entries(initial.contracts)) {
        this.contracts.set(slug, clone(contract));
      }
    }
  }

  async getContract(slug: string): Promise<Record<string, unknown> | null> {
    const value = this.contracts.get(slug);
    return value ? clone(value) : null;
  }

  async upsertContract(slug: string, contract: Record<string, unknown>): Promise<void> {
    this.contracts.set(slug, clone(contract));
  }

  async enqueue(queue: string, payload: Record<string, unknown>): Promise<QueueItem> {
    const record: QueueRecord = {
      id: nanoid(),
      queue,
      payload: clone(payload),
      status: 'pending',
      retries: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    const list = this.queues.get(queue) ?? [];
    list.push(record);
    this.queues.set(queue, list);
    return this.toQueueItem(record);
  }

  async fetchPending(queue: string, limit: number): Promise<QueueItem[]> {
    return (this.queues.get(queue) ?? [])
      .filter((record) => record.status === 'pending')
      .slice(0, limit)
      .map((record) => this.toQueueItem(record));
  }

  async markInProgress(queue: string, itemId: string): Promise<void> {
    this.updateRecord(queue, itemId, { status: 'in_progress' });
  }

  async complete(queue: string, itemId: string, updates?: Record<string, unknown>): Promise<void> {
    const patch: Partial<QueueRecord> = { status: 'completed' };
    if (updates) {
      patch.payload = { ...this.getRecord(queue, itemId).payload, ...updates };
    }
    this.updateRecord(queue, itemId, patch);
  }

  async fail(queue: string, itemId: string, errorMessage: string): Promise<void> {
    this.updateRecord(queue, itemId, {
      status: 'failed',
      lastError: errorMessage,
    });
  }

  async listQueue(queue: string): Promise<QueueItem[]> {
    return (this.queues.get(queue) ?? []).map((record) => this.toQueueItem(record));
  }

  async logAgentEvent(event: {
    restaurantSlug: string;
    agentId: string;
    status: string;
    payload?: Record<string, unknown> | undefined;
  }): Promise<void> {
    this.logs.push({
      ...event,
      createdAt: new Date().toISOString(),
    });
  }

  private getRecord(queue: string, id: string): QueueRecord {
    const record = (this.queues.get(queue) ?? []).find((item) => item.id === id);
    if (!record) {
      throw new Error(`Queue item ${id} not found in ${queue}`);
    }
    return record;
  }

  private updateRecord(queue: string, id: string, updates: Partial<QueueRecord>): void {
    const record = this.getRecord(queue, id);
    if (updates.status !== undefined) {
      record.status = updates.status;
    }
    if (updates.payload !== undefined) {
      record.payload = clone(updates.payload);
    }
    if (updates.retries !== undefined) {
      record.retries = updates.retries;
    }
    if (updates.lastError !== undefined) {
      record.lastError = updates.lastError;
    }
    if (updates.createdAt !== undefined) {
      record.createdAt = updates.createdAt;
    }
    record.updatedAt = updates.updatedAt ?? new Date().toISOString();
  }

  private toQueueItem(record: QueueRecord): QueueItem {
    return {
      id: record.id,
      payload: clone(record.payload),
      status: record.status,
      retries: record.retries,
      lastError: record.lastError,
      createdAt: record.createdAt,
      updatedAt: record.updatedAt,
    };
  }
}

function clone<T>(value: T): T {
  const structured = (globalThis as typeof globalThis & { structuredClone?: <V>(v: V) => V }).structuredClone;
  if (typeof structured === 'function') {
    return structured(value);
  }
  return JSON.parse(JSON.stringify(value));
}
