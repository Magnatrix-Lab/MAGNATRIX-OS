/**
 * pipeline.ts — MAGNATRIX TypeScript SDK Pipeline Builder
 */
interface PipelineStep {
  id: string;
  agent: string;
  skill: string;
  depends_on: string[];
  config?: Record<string, any>;
}

export class Pipeline {
  private name: string;
  private description: string;
  private steps: PipelineStep[] = [];

  constructor(name: string, description = "") {
    this.name = name;
    this.description = description;
  }

  step(id: string, agent: string, skill: string, dependsOn: string[] = [], config?: Record<string, any>): this {
    this.steps.push({ id, agent, skill, depends_on: dependsOn, config });
    return this;
  }

  toJSON(): any {
    return {
      name: this.name,
      description: this.description,
      steps: this.steps,
    };
  }

  static fromTemplate(template: string): Pipeline {
    const templates: Record<string, { description: string; steps: [string, string, string, string[]][] }> = {
      "trading-signal": {
        description: "End-to-end trading pipeline",
        steps: [
          ["scan", "scout", "scan-tokens", []],
          ["analyze", "analyst", "analyze-signal", ["scan"]],
          ["risk_check", "guardian", "check-risk", ["analyze"]],
          ["execute", "executor", "execute-trade", ["risk_check"]],
        ],
      },
      "security-audit": {
        description: "Full whitebox security audit",
        steps: [
          ["recon", "researcher", "security-audit", []],
          ["triage", "guardian", "check-risk", ["recon"]],
          ["report", "writer", "daily-digest", ["triage"]],
        ],
      },
    };
    const t = templates[template] || { description: "", steps: [] };
    const p = new Pipeline(template, t.description);
    for (const [id, agent, skill, deps] of t.steps) {
      p.step(id, agent, skill, deps);
    }
    return p;
  }
}
