# 如何在agentUniverse中使用MCP服务
在agentUniverse中，您只需通过以下2个步骤，即可将任意MCP服务接入，并将其作为工具供智能体使用。

## step1. 通过MCPToolkit将您指定MCP服务作为工具包接入
MCPServer当前版本可分为三类通信模式,1)通过标准输入输出流(stdio)连接，2)通过SSE方式连接，3）通过Streamable HTTP连接，下列是各类不同MCP模式的配置yaml样例。

1)标准输入输出流(stdio)模式连接示例如下：
```yaml
name: 'docx_toolkit'
description: |
  这是一个docx相关的工具集
transport: 'stdio'
command: 'uvx'
args:
  - 'mcp-server-office'

metadata:
  type: 'TOOLKIT'
  module: 'agentuniverse.agent.action.toolkit.mcp_toolkit'
  class: 'MCPToolkit'
```

2）SSE模式连接示例如下：
```yaml
name: 'search_toolkit'
description: |
  这是一个搜索相关的工具包
transport: 'sse'
url: 'http://localhost:8000/sse'

metadata:
  type: 'TOOLKIT'
  module: 'agentuniverse.agent.action.toolkit.mcp_toolkit'
  class: 'MCPToolkit'
```

3）Streamable HTTP连接示例如下：
```yaml
name: 'weather'
transport: 'streamable_http'
url: 'http://localhost:8000/mcp'
metadata:
  type: 'TOOLKIT'
  module: 'agentuniverse.agent.action.toolkit.mcp_toolkit'
  class: 'MCPToolkit'
```

- `transport`、`url`、`command`、`args`、`env`等参数均与mcp官方定义一致。

## step2. 将MCPToolkit配置给agent，供agent使用MCP服务
通过步骤一我们已经将mcp服务接入了，进一步您可以MCPToolkit配置给agent，供agent使用MCP服务。

配置方式：将您想使用的MCPToolkit列表挂载在agent配置文件的 [`action`->`toolkit`] 属性中。

下面是一个完整的示例配置，在该agent中使用了步骤一中配置的stdio模式下的docx mcp服务。

```yaml
info:
  name: 'demo_agent_with_mcp_toolkit'
  description: 'A simple demonstration react agent designed to showcase 
  the integration and usage of mcp toolkits.'
profile:
  prompt_version: qwen_react_agent.cn
  llm_model:
    name: 'qwen3-32b'
    stop: 'Observation'
    temperature: 0.1
action:
  toolkit:
    - 'docx_toolkit'
memory:
  name: 'demo_memory'
metadata:
  type: 'AGENT'
  module: 'agentuniverse.agent.template.react_agent_template'
  class: 'ReActAgentTemplate'
```

详细的案例app代码地址可以参考[MCP使用样例app](/examples/sample_apps/toolkit_demo_app)，MCPToolkit接入您可参考[配置文件](/examples/sample_apps/toolkit_demo_app/intelligence/agentic/toolkit/docx_toolkit.yaml), Agent配置MCPToolkit可参考[配置文件](/examples/sample_apps/toolkit_demo_app/intelligence/agentic/agent/agent_instance/demo_agent_with_mcp_toolkit.yaml)，测试启动入口见[文件](/examples/sample_apps/toolkit_demo_app/intelligence/test/run_demo_agent_with_mcp_toolkit.py)。

更多详细内容您可阅读文档[MCP工具包](../../In-Depth_Guides/原理介绍/工具包/MCP工具包.md)、[MCP工具](../../In-Depth_Guides/原理介绍/工具/MCP工具.md)。
