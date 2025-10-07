import { promises as fs } from 'fs';
import path from 'path';
import YAML from 'yaml';
import { BuilderSchema, BuilderConfig, WorkflowConfig } from './types.js';
import { z } from 'zod';

const DEFAULT_CONFIG_PATH = path.join(
  process.cwd(),
  'agentkit',
  'builder',
  'happy_hour_agents.yaml'
);

export async function loadBuilderConfig(configPath = DEFAULT_CONFIG_PATH): Promise<BuilderConfig> {
  const absolute = path.isAbsolute(configPath)
    ? configPath
    : path.join(process.cwd(), configPath);

  const file = await fs.readFile(absolute, 'utf-8');
  const parsed = YAML.parse(file, { merge: true });
  return BuilderSchema.parse(parsed);
}

const PipelineConfigSchema = z.object({
  workflowId: z.string(),
  restaurantSlug: z.string(),
});

export type PipelineConfigInput = z.infer<typeof PipelineConfigSchema>;

export function resolveWorkflow(config: BuilderConfig, workflowId?: string): WorkflowConfig {
  const targetId = workflowId ?? config.workflows[0]?.id;
  if (!targetId) {
    throw new Error('No workflows defined in builder configuration');
  }

  const workflow = config.workflows.find((wf) => wf.id === targetId);
  if (!workflow) {
    throw new Error(`Workflow ${targetId} not found in builder configuration`);
  }

  return workflow;
}
