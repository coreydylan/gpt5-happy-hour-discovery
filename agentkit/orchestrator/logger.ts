import pino, { Logger } from 'pino';
import { OrchestratorLogger } from './types.js';

const defaultLogger = pino({
  name: 'hhmap-orchestrator',
  level: process.env.LOG_LEVEL ?? 'info',
  base: undefined,
});

class PinoLogger implements OrchestratorLogger {
  constructor(private readonly logger: Logger) {}

  info(payload: Record<string, unknown> | string): void {
    this.logger.info(payload);
  }

  warn(payload: Record<string, unknown> | string): void {
    this.logger.warn(payload);
  }

  error(payload: Record<string, unknown> | string, error?: unknown): void {
    if (error instanceof Error) {
      this.logger.error({ ...toRecord(payload), err: error }, error.message);
    } else {
      this.logger.error({ ...toRecord(payload), err: error });
    }
  }

  child(bindings: Record<string, unknown>): OrchestratorLogger {
    return new PinoLogger(this.logger.child(bindings));
  }
}

function toRecord(value: Record<string, unknown> | string): Record<string, unknown> {
  return typeof value === 'string' ? { message: value } : value;
}

export function getLogger(): OrchestratorLogger {
  return new PinoLogger(defaultLogger);
}
