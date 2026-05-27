import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

// CCL + MCP Bridge — MAGNATRIX Layer 1.5
// Routes requests between brains and models

const server = new Server({ name: "magnatrix-ccl-bridge", version: "0.1.0" }, {
  capabilities: { tools: {} }
});

server.setRequestHandler("tools/list", async () => ({
  tools: [
    { name: "route_chat", description: "Route chat to local/cloud model", inputSchema: { type: "object", properties: { model: { type: "string" }, prompt: { type: "string" } } } },
    { name: "route_code", description: "Route code task to codellama", inputSchema: { type: "object", properties: { code: { type: "string" } } } },
    { name: "switch_model", description: "Switch active model", inputSchema: { type: "object", properties: { target: { type: "string" } } } },
  ]
}));

server.setRequestHandler("tools/call", async (req) => {
  const { name, arguments: args } = req.params;
  if (name === "route_chat") {
    return { content: [{ type: "text", text: `[CCL] Routed to ${args.model}: ${args.prompt.substring(0, 50)}...` }] };
  }
  if (name === "switch_model") {
    return { content: [{ type: "text", text: `[CCL] Switched to ${args.target}` }] };
  }
  return { content: [{ type: "text", text: "Unknown tool" }] };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log("CCL MCP Bridge active");
}
main().catch(console.error);
