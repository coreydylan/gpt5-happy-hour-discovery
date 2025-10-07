#!/usr/bin/env node
import { loadBuilderConfig, resolveWorkflow } from './config.js';
import { getLogger } from './logger.js';
import { SupabaseStateAdapter } from './stateSupabase.js';
import { InMemoryStateAdapter } from './stateMemory.js';
import { OrchestratorRunner } from './runner.js';
import { createMockAgentRegistry } from './agents/mockAgents.js';

interface CliOptions {
  slug: string;
  workflow?: string;
  configPath?: string;
}

function parseArgs(argv: string[]): CliOptions {
  const options: Partial<CliOptions> = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--slug' || arg === '-s') {
      options.slug = argv[++i];
    } else if (arg === '--workflow' || arg === '-w') {
      options.workflow = argv[++i];
    } else if (arg === '--config' || arg === '-c') {
      options.configPath = argv[++i];
    }
  }

  if (!options.slug) {
    throw new Error('Restaurant slug is required. Pass via --slug');
  }

  return options as CliOptions;
}

async function main(): Promise<void> {
  const logger = getLogger();

  try {
    const options = parseArgs(process.argv.slice(2));
    const config = await loadBuilderConfig(options.configPath);
    const workflow = resolveWorkflow(config, options.workflow);

    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    const tables = config.state.tables as Record<string, { name: string }>;
    const contractsTable = tables.contracts?.name;
    const urlQueueTable = tables.url_queue?.name;
    const extractionQueueTable = tables.extraction_queue?.name;
    const logsTable = tables.logs?.name;

    if (!contractsTable || !urlQueueTable || !extractionQueueTable || !logsTable) {
      throw new Error('Builder configuration missing required table mappings');
    }

    const stateAdapter =
      supabaseUrl && supabaseKey
        ? new SupabaseStateAdapter({
            url: supabaseUrl,
            serviceRoleKey: supabaseKey,
            tables: {
              contracts: contractsTable,
              urlQueue: urlQueueTable,
              extractionQueue: extractionQueueTable,
              logs: logsTable,
            },
            logger,
          })
        : new InMemoryStateAdapter();

    if (!(supabaseUrl && supabaseKey)) {
      logger.warn({
        event: 'no-supabase-credentials',
        message: 'Using in-memory state adapter. Queue results will not persist.',
      });
    }

    const registry = createMockAgentRegistry();
    const runner = new OrchestratorRunner({
      workflow,
      builder: config,
      state: stateAdapter,
      registry,
      logger,
    });

    await runner.run(options.slug);

    logger.info({ event: 'pipeline-complete', slug: options.slug });
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    getLogger().error({ event: 'orchestrator-failed', error: err.message });
    process.exitCode = 1;
  }
}

main();
