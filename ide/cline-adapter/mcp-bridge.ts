import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({ name: "magnatrix-cline", version: "0.1.0" }, {
  capabilities: { tools: {} }
});

server.setRequestHandler("tools/list", async () => ({
  tools: [
    { name: "cline_code", description: "Generate code", inputSchema: { type: "object", properties: { file: { type: "string" }, instruction: { type: "string" } } } },
    { name: "cline_debug", description: "Debug code", inputSchema: { type: "object", properties: { file: { type: "string" }, error: { type: "string" } } } },
  ]
}));

server.setRequestHandler("tools/call", async (req) => {
  const { name, arguments: args } = req.params;
  if (name === "cline_code") {
    return { content: [{ type: "text", text: `// Generated: ${args.file}
// ${args.instruction}
// TODO: implement` }] };
  }
  return { content: [{ type: "text", text: "OK" }] };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log("Cline MCP Bridge active");
}
main().catch(console.error);
