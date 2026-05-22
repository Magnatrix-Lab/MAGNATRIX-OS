/**
 * mesh.ts — MAGNATRIX TypeScript SDK Mesh Client
 */
export class MeshClient {
  private baseUrl: string;

  constructor(baseUrl = "http://localhost:8080") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async send(sender: string, type: string, payload: any, target?: string, priority = 5): Promise<any> {
    // Placeholder — in production calls mesh API
    return { status: "sent", sender, type, target, payload, timestamp: Date.now() };
  }

  async broadcast(sender: string, type: string, payload: any): Promise<any> {
    return this.send(sender, type, payload);
  }
}
