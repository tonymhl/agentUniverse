# MCP Server
agentUniverse allows users to expose their tools/toolkits as MCP Servers for external services. To achieve this, you need to complete the following steps.

## 1. Mark Tools for Publication
You can designate tools (Tool) or toolkits (Toolkit) in their YAML definition files to be accessible via an MCP Server.

Configure as follows:
```yaml
name: 'tool_name'
description: 'tool description'
as_mcp_tool: true
```

This tool will be added to the default MCP Server in agentUniverse, named `default_mcp_server` by default.

If you need to specify a custom MCP service name or publish tools to multiple MCP services, use the server_name field:
```yaml
name: 'tool_name'
description: 'tool description'
as_mcp_tool:
  server_name: mcp_search_server
```
Here, `as_mcp_tool` indicates the tool/toolkit can be called via an MCP Server, while server_name specifies the target MCP service. Different MCP services operate independently and do not conflict with each other.

## 2.Start the MCP Server
Refer to the example code for starting the MCP Server:
```python
from agentuniverse.agent_serve.web.mcp.mcp_server_manager import MCPServerManager
from agentuniverse.base.agentuniverse import AgentUniverse


class ServerApplication:
    """
    Server application.
    """

    @classmethod
    def start(cls):
        AgentUniverse().start(core_mode=True)
        MCPServerManager().start_server()
        
if __name__ == "__main__":
    ServerApplication.start()
```

Parameters for MCPServerManager.start_server:
- host: The host address for the MCP Server (default: 0.0.0.0).
- port: The port number for the Uvicorn server (default: 8890).
- transport: The MCP server type, with options:
  - "sse" (Server-Sent Events): Access path: http://${host}:${port}/${server_name}/sse
  - "streamable_http": Access path: http://${host}:${port}/${server_name}/mcp

Example: For the mcp_search_server with default configurations, the endpoints are:
- http://0.0.0.0:8890/mcp_search_server/sse (for SSE)
- http://0.0.0.0:8890/mcp_search_server/mcp (for Streamable HTTP)
