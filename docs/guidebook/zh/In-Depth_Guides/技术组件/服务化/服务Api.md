# Web API

agentUniverse的Web Server提供了数个调用Agent服务的API接口，允许开发者按自己的需求从外部调用Agent服务。

为了方便说明，我们假设Web Server启动在本地的8888端口上，并注册了一个名为`demo_service`的Agent服务：

```yaml
name: 'demo_service'
description: 'A demo service used for explaining.'
agent: 'demo_agent'
metadata:
  type: 'SERVICE'
```

其中的`demo_agent`接受一个str类型的input参数,  
并返回一个字符串:`"Your input is {input}."`

## /service_run

该POST接口以同步的方式调用Agent服务，调用会阻塞直到目标Agent服务返回结果。  
调用示例如下:

```shell
curl -X POST -H "Content-Type: application/json" -d '{"service_id":"demo_service","params":{"input":"Hello!"}}' http://127.0.0.1:8888/service_run
```

### 请求参数：

| 参数名        | 类型     | 是否必须 | 描述                |
|------------|--------|------|-------------------|
| service_id | string | 是    | 本次请求想要访问的Agent服务。 |
| params     | Object | 否    | 想要访问的Agent服务的参数。  |  

params中参数的结构：

| 参数名          | 类型           | 是否必须 | 描述                                                        |
|--------------|--------------|------|-----------------------------------------------------------|
| session_id   | string       | 否    | 会话id, 唯一标识一个会话                                            |
| query        | string       | 否    | 用户的query， 这里只是示例，具体的参数需要根据具体智能体定义。                        |
| chat_history | List[Object] | 否    | 历史会话记录，支持从外部传入的历史会话记录。若没有传入，则根据session_id和agent_id从记忆中获取。 |

说明：除session_id之外，其他参数需要根据具体智能体自行定义。

### 返回结果：
预期收到的返回值示例如下：

```shell
{
        "success": true,
        "result": "Your input is Hello!.",
        "message": null,
        "request_id": "7dd7d737b6b64c3c92addf541e73e97c"
}
```

返回结果说明：

| 参数名        | 类型      | 是否必须 | 描述                                            |
|------------|---------|------|-----------------------------------------------|
| success    | boolean | 是    | 表示Agent调用的成功与否，取值为`true`和`false`。             |
| message    | string  | 否    | 当`success`为`false`时返回错误信息，成功时为`null`。         |
| result     | object  | 是    | Agent调用成功时返回的执行结果。 不同智能体的返回结果格式可能不同，由用户自己定义。  |
| request_id | string  | 是    | 唯一请求标识符，用于通过`/service_run_result`接口查询对应请求的结果。 |

## /service_run_stream

该POST接口类似`/service_run`，调用方式与其一致:

```shell
curl -X POST -H "Content-Type: application/json" -d '{"service_id":"demo_service","params":{"input":"Hello!"}}' http://127.0.0.1:8888/service_run_stream
```

### 请求方法:

    POST

### 请求参数：

| 参数名        | 类型     | 是否必须 | 描述                |
|------------|--------|------|-------------------|
| service_id | string | 是    | 本次请求想要访问的Agent服务。 |
| params     | Object | 否    | 想要访问的Agent服务的参数。  |  

params中参数的结构：

| 参数名          | 类型           | 是否必须 | 描述                                                        |
|--------------|--------------|------|-----------------------------------------------------------|
| session_id   | string       | 否    | 会话id, 唯一标识一个会话                                            |
| query        | string       | 否    | 用户的query， 这里只是示例，具体的参数需要根据具体智能体定义。                        |
| chat_history | List[Object] | 否    | 历史会话记录，支持从外部传入的历史会话记录。若没有传入，则根据session_id和agent_id从记忆中获取。 |

说明：除session_id之外，其他参数需要根据具体智能体自行定义。

### 返回结果：

Agent的返回结果会以流式的形式返回,其中响应头中包含：

| 参数名          | 类型     | 是否必须 | 描述                   |
|--------------|--------|------|----------------------|
| X-Request-ID | string | 是    | 请求的id                |
| Content-Type | string | 是    | 值为：text/event-stream | 

流式返回结果数据结构：

| 参数名     | 类型          | 是否必须 | 描述                            |
|---------|-------------|------|-------------------------------|
| process | json string | 否    | 模型的流式回答输出/中间执行过程信息/用户自定义的输出信息 |
| result  | json string | 是    | 智能体的最终执行结果，最后一个流式输出信息，用户自行定义  |                                           
| error   | string      | 否    | 报错信息                          |

process的数据结构：

| 参数名  | 类型     | 是否必须 | 描述                                                                          |
|------|--------|------|-----------------------------------------------------------------------------|
| type | string | 是    | 数据的类型，当为模型的输出时为：token，用户可以根据需要自定义流式输出的 type与data                            |
| data | Object | 是    | 当type为token时的输出示例：```{"token": "Hello!", "agent_info": {"name":"agent"}}``` |

## /service_run_async

该POST接口以异步的形式调用Agent服务。调用方式如下:

```shell
curl -X POST -H "Content-Type: application/json" -d '{"service_id":"demo_service","params":{"input":"Hello!"}}' http://127.0.0.1:8888/service_run_async
```

该接口调用后会立刻返回:

```shell
{
        "success": true,
        "result": null,
        "message": null,
        "request_id": "7dd7d737b6b64c3c92addf541e73e97c"
}
```

返回结果中仅会包含表示调用成功与否的`success`与表示本次调用的`request_id`。
对于调用的结果，您需要使用`request_id`在[/service_run_result]()接口中进行查询。

## /service_run_result

该GET接口允许用户用request_id的状态，调用样例如下：

```shell
 curl 'http://127.0.0.1:8888/service_run_result?request_id=8e6f17dbe7ff4730a62b4a2914d73c74'
```

预期收到的返回值示例如下：

```shell
{
  "message":null,
  "request_id":"8e6f17dbe7ff4730a62b4a2914d73c74",
  "result":{
    "result":"Your input is Hello!.",
    "state":"finish",
    "steps":[]
    },
  "success":true}

```

其中`result`包含三个部分：`result`表示Agent服务的执行结果，`state`表示Agent服务的执行状态，`steps`表示Agent服务执行的中间过程。

`state`表示的任务状态包含以下几种情况：

```text
# agentuniverse.agent_serve.web.request_task.TaskStateEnum

class TaskStateEnum(Enum):
    """All possible state of a web request task."""
    INIT = "init"
    RUNNING = "running"
    FINISHED = "finished"
    FAIL = "fail"
    CANCELED = "canceled"
```
