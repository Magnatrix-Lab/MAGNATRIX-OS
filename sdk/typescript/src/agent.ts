/**
 * agent.ts — MAGNATRIX TypeScript SDK Agent Builder
 */
export interface AgentConfig {
  name: string;
  role?: string;
  description?: string;
  personality?: string;
  skills?: string[];
  schedule?: string;
  canVeto?: boolean;
  maxParallelTasks?: number;
}

export class Agent {
  private config: AgentConfig;

  constructor(config: AgentConfig) {
    this.config = {
      role: "generic",
      skills: [],
      schedule: "*/15 * * * *",
      canVeto: false,
      maxParallelTasks: 3,
      ...config,
    };
  }

  withSkill(skill: string): this {
    if (!this.config.skills!.includes(skill)) this.config.skills!.push(skill);
    return this;
  }

  withVeto(enabled = true): this {
    this.config.canVeto = enabled;
    return this;
  }

  toJSON(): any {
    return {
      name: this.config.name,
      role: this.config.role,
      description: this.config.description,
      personality: this.config.personality,
      skills: this.config.skills,
      schedule: this.config.schedule,
      can_veto: this.config.canVeto,
      max_parallel_tasks: this.config.maxParallelTasks,
    };
  }

  static fromTemplate(template: string, name?: string): Agent {
    const templates: Record<string, Partial<AgentConfig>> = {
      scout: { role: "scout", skills: ["scan-tokens", "web-monitor"] },
      analyst: { role: "analyst", skills: ["analyze-signal", "forecast-model"] },
      executor: { role: "executor", skills: ["execute-trade", "deploy-node"] },
      guardian: { role: "guardian", skills: ["check-risk", "veto-trigger"], canVeto: true },
      researcher: { role: "researcher", skills: ["arxiv-scan", "protocol-deep-dive"] },
      writer: { role: "writer", skills: ["daily-digest", "report-generate"] },
      ops: { role: "ops", skills: ["repo-health", "gh-fix-ci"] },
      architect: { role: "architect", skills: ["code-mutate", "mcp-builder"] },
    };
    const t = templates[template] || {};
    return new Agent({ name: name || template, ...t });
  }
}
