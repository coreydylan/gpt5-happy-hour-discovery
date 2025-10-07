import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { OrchestratorLogger, OrchestratorStateAdapter, QueueItem } from './types.js';

interface SupabaseStateOptions {
  url: string;
  serviceRoleKey: string;
  tables: {
    contracts: string;
    urlQueue: string;
    extractionQueue: string;
    logs: string;
  };
  logger: OrchestratorLogger;
}

const DEFAULT_STATUS_FIELD = 'status';
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'skipped']);

export class SupabaseStateAdapter implements OrchestratorStateAdapter {
  private readonly client: SupabaseClient;
  private readonly tables: SupabaseStateOptions['tables'];
  private readonly logger: OrchestratorLogger;

  constructor(options: SupabaseStateOptions) {
    this.client = createClient(options.url, options.serviceRoleKey, {
      auth: { persistSession: false },
    });
    this.tables = options.tables;
    this.logger = options.logger.child({ scope: 'supabase' });
  }

  async getContract(slug: string): Promise<Record<string, unknown> | null> {
    const { data, error } = await this.client
      .from(this.tables.contracts)
      .select('contract')
      .eq('restaurant_slug', slug)
      .maybeSingle();

    if (error) {
      throw new Error(`Failed to fetch contract for ${slug}: ${error.message}`);
    }

    return data ? (data.contract as Record<string, unknown>) : null;
  }

  async upsertContract(slug: string, contract: Record<string, unknown>): Promise<void> {
    const { error } = await this.client
      .from(this.tables.contracts)
      .upsert({
        restaurant_slug: slug,
        contract,
        updated_at: new Date().toISOString(),
      });

    if (error) {
      throw new Error(`Failed to upsert contract for ${slug}: ${error.message}`);
    }
  }

  async enqueue(queue: string, payload: Record<string, unknown>): Promise<QueueItem> {
    if (queue === this.tables.urlQueue) {
      return this.enqueueUrlTask(payload);
    }

    if (queue === this.tables.extractionQueue) {
      return this.enqueueExtractionTask(payload);
    }

    throw new Error(`Unsupported queue ${queue} for Supabase state adapter`);
  }

  private async enqueueUrlTask(payload: Record<string, unknown>): Promise<QueueItem> {
    const { error, data } = await this.client
      .from(this.tables.urlQueue)
      .insert({
        restaurant_slug: payload.restaurant_slug,
        url: payload.url,
        why_interesting: payload.why_interesting ?? payload.reason,
        status: payload.status ?? 'pending',
        priority: payload.priority ?? 5,
        evidence: payload.evidence ?? null,
      })
      .select('*')
      .single();

    if (error) {
      throw new Error(`Failed to enqueue URL task: ${error.message}`);
    }

    return mapUrlRowToQueueItem(data);
  }

  private async enqueueExtractionTask(payload: Record<string, unknown>): Promise<QueueItem> {
    const { error, data } = await this.client
      .from(this.tables.extractionQueue)
      .insert({
        restaurant_slug: payload.restaurant_slug,
        source_url: payload.source_url,
        instructions: payload.instructions ?? payload.payload ?? {},
        status: payload.status ?? 'pending',
      })
      .select('*')
      .single();

    if (error) {
      throw new Error(`Failed to enqueue extraction task: ${error.message}`);
    }

    return mapExtractionRowToQueueItem(data);
  }

  async fetchPending(queue: string, limit: number): Promise<QueueItem[]> {
    if (queue === this.tables.urlQueue) {
      const { data, error } = await this.client
        .from(this.tables.urlQueue)
        .select('*')
        .eq(DEFAULT_STATUS_FIELD, 'pending')
        .order('priority', { ascending: true, nullsFirst: true })
        .order('discovered_at', { ascending: true, nullsFirst: true })
        .limit(limit);

      if (error) {
        throw new Error(`Failed to fetch pending from ${queue}: ${error.message}`);
      }

      return (data ?? []).map(mapUrlRowToQueueItem);
    }

    if (queue === this.tables.extractionQueue) {
      const { data, error } = await this.client
        .from(this.tables.extractionQueue)
        .select('*')
        .eq(DEFAULT_STATUS_FIELD, 'pending')
        .order('queued_at', { ascending: true, nullsFirst: true })
        .limit(limit);

      if (error) {
        throw new Error(`Failed to fetch pending from ${queue}: ${error.message}`);
      }

      return (data ?? []).map(mapExtractionRowToQueueItem);
    }

    throw new Error(`Unsupported queue ${queue}`);
  }

  async markInProgress(queue: string, itemId: string): Promise<void> {
    await this.updateStatus(queue, itemId, 'in_progress', {});
  }

  async complete(queue: string, itemId: string, updates?: Record<string, unknown>): Promise<void> {
    await this.updateStatus(queue, itemId, 'completed', updates ?? {});
  }

  async fail(queue: string, itemId: string, errorMessage: string): Promise<void> {
    this.logger.warn({ message: 'queue task failed', queue, itemId, error: errorMessage });
    await this.updateStatus(queue, itemId, 'failed', {});
  }

  private async updateStatus(
    table: string,
    itemId: string,
    status: string,
    updates: Record<string, unknown>
  ): Promise<void> {
    const patch: Record<string, unknown> = { ...updates, status };

    if (table === this.tables.urlQueue) {
      patch.last_checked = new Date().toISOString();
    }

    if (table === this.tables.extractionQueue) {
      const now = new Date().toISOString();
      if (status === 'in_progress') {
        patch.started_at = now;
      }
      if (status === 'completed' || status === 'failed') {
        patch.completed_at = now;
      }
    }

    const { error } = await this.client.from(table).update(patch).eq('task_id', itemId);

    if (error) {
      throw new Error(`Failed to update status for ${itemId} in ${table}: ${error.message}`);
    }
  }

  async listQueue(queue: string): Promise<QueueItem[]> {
    if (queue === this.tables.urlQueue) {
      return this.listQueueFromTable(queue, mapUrlRowToQueueItem);
    }

    if (queue === this.tables.extractionQueue) {
      return this.listQueueFromTable(queue, mapExtractionRowToQueueItem);
    }

    throw new Error(`Unsupported queue ${queue}`);
  }

  private async listQueueFromTable(table: string, mapper: (row: any) => QueueItem): Promise<QueueItem[]> {
    const { data, error } = await this.client
      .from(table)
      .select('*')
      .order('discovered_at', { ascending: true, nullsFirst: true });

    if (error) {
      throw new Error(`Failed to list queue ${table}: ${error.message}`);
    }

    return (data ?? []).map(mapper);
  }

  async logAgentEvent(event: {
    restaurantSlug: string;
    agentId: string;
    status: string;
    payload?: Record<string, unknown>;
  }): Promise<void> {
    const { error } = await this.client.from(this.tables.logs).insert({
      restaurant_slug: event.restaurantSlug,
      agent_id: event.agentId,
      status: event.status,
      payload: event.payload ?? {},
    });

    if (error) {
      this.logger.error({ message: 'Failed to insert agent log', error: error.message });
    }
  }
}

function mapUrlRowToQueueItem(row: any): QueueItem {
  return {
    id: row.task_id,
    payload: {
      restaurant_slug: row.restaurant_slug,
      url: row.url,
      why_interesting: row.why_interesting,
      verdict: row.verdict,
      priority: row.priority,
      evidence: row.evidence,
    },
    status: row.status,
    retries: row.retries ?? 0,
    lastError: row.error_message ?? undefined,
    createdAt: row.discovered_at,
    updatedAt: row.last_checked,
  };
}

function mapExtractionRowToQueueItem(row: any): QueueItem {
  return {
    id: row.task_id,
    payload: {
      restaurant_slug: row.restaurant_slug,
      source_url: row.source_url,
      instructions: row.instructions,
      result: row.result,
    },
    status: row.status,
    retries: row.retries ?? 0,
    lastError: row.error_message ?? undefined,
    createdAt: row.queued_at,
    updatedAt: row.completed_at ?? row.started_at,
  };
}

export const InMemoryTerminalStatuses = TERMINAL_STATUSES;
