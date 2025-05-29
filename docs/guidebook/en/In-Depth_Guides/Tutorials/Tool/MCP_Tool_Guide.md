# MCP Tools

An MCP tool is a specialized type of Tool that performs tasks by invoking an MCPServer.

The current version of MCPServer supports three communication modes:
* Standard input/output streams (stdio)
* Server-Sent Events(SSE)
* Streamable HTTP

Below are YAML configuration examples for each MCP mode.

1) Standard Input/Output Streams
```yaml
name: 'calculator'
description: |
  使用该工具可以执行搜索操作。工具的输入是你想搜索的内容。
server_name: 'demo_stdio_mcp_tool'
transport: 'stdio'
command: 'python'
args:
  - 'stdio_server.py'
env:
  TIMEOUT: 100

metadata:
  type: 'TOOL'
  module: 'agentuniverse.agent.action.tool.mcp_tool'
  class: 'MCPTool'
```

2) SSE
```yaml
name: 'weather'
origin_tool_name: 'get_weather'
server_name: 'demo_http_mcp_tool'
transport: 'sse'
url: 'http://localhost:8000/sse'
metadata:
  type: 'TOOL'
  module: 'agentuniverse.agent.action.tool.mcp_tool'
  class: 'MCPTool'
```

3) Streamable HTTP
```yaml
name: 'weather'
origin_tool_name: 'get_weather'
server_name: 'demo_http_mcp_tool'
transport: 'streamable_http'
url: 'http://localhost:8000/mcp'
metadata:
  type: 'TOOL'
  module: 'agentuniverse.agent.action.tool.mcp_tool'
  class: 'MCPTool'
```

### Key Parameter Notes  
* name: Represents both the tool name in agentUniverse and the corresponding tool name in MCPServer. If you want to use a different name, specify the actual tool name in MCPServer using the `origin_tool_name` parameter.
* description: Unlike a standard tool, this field may be left empty. If not explicitly provided, the description from MCPServer will be used as the default.
* server_name: Identifies a unique MCPServer. Sessions are shared among MCPServers with the same server_name.
* transport: Accepts three values:
  * `stdio`: Requires command and args to launch a local MCPServer via command line. The optional env parameter (a dict) defines runtime environment variables.
  * `sse` or `streamable_http`: Requires the url parameter to connect to a remote MCPServer.

### References  
* Tool Definition Example: [duckduckgo_search_mcp_tool](../../../../../../examples/sample_apps/toolkit_demo_app/intelligence/agentic/tool/duckduckgo_search_mcp_tool.yaml)
* Tool Invocation Example: [demo_agent_with_mcp_tool](../../../../../../examples/sample_apps/toolkit_demo_app/intelligence/agentic/agent/agent_instance/demo_agent_with_mcp_tool.yaml)