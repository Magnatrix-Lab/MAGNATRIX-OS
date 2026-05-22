/**
 * client.ts — MAGNATRIX TypeScript SDK Client
 */
export interface MAGNATRIXConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export class MAGNATRIXClient {
  private baseUrl: string;
  private apiKey: string;
  private timeout: number;

  constructor(config: MAGNATRIXConfig = {}) {
    this.baseUrl = (config.baseUrl || process.env.MAGNATRIX_API_URL || "http://localhost:8080").replace(/\/$/, "");
    this.apiKey = config.apiKey || process.env.MAGNATRIX_API_KEY || "";
    this.timeout = config.timeout || 30000;
  }

  private async request(method: string, endpoint: string, payload?: any): Promise<any> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json",
    };
    if (this.apiKey) headers["Authorization"] = `Bearer ${this.apiKey}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: payload ? JSON.stringify(payload) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!response.ok) {
        return { error: `HTTP ${response.status}`, detail: await response.text() };
      }
      return await response.json();
    } catch (err: any) {
      clearTimeout(timer);
      return { error: err.message || String(err) };
    }
  }

  async status(): Promise<any> { return this.request("GET", "/api/v2/status"); }
  async health(): Promise<any> { return this.request("GET", "/health"); }
  async llmChat(messages: any[], model?: string, extra?: any): Promise<any> {
    return this.request("POST", "/api/v2/llm/chat", { messages, model, ...extra });
  }
  async llmModels(): Promise<any[]> {
    const r = await this.request("GET", "/api/v2/llm/models");
    return r.data || [];
  }
  async swarmNodes(): Promise<any[]> {
    const r = await this.request("GET", "/api/v2/swarm/nodes");
    return r.nodes || [];
  }
  async knowledgeQuery(query: string, limit = 10): Promise<any> {
    return this.request("POST", "/api/v2/knowledge/query", { query, limit });
  }
  async tradingStatus(): Promise<any> { return this.request("GET", "/api/v2/trading/status"); }
  async constitution(): Promise<any> { return this.request("GET", "/api/v2/governance/constitution"); }
  async evolveTrigger(): Promise<any> { return this.request("POST", "/api/v2/evolve/trigger"); }
}
