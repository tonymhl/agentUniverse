import traceback
from typing import Any, List
import requests
import json
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompt_values import StringPromptValue
# from .object import ChatObject, ChatObjectProvider
# from .executor import ChatExecutor
# from .source import CHAT_SOURCE

from libro_ai.chat.utils import executor_by_ipython
from IPython.display import display, clear_output

# 调试时需要使用
from libro_ai.chat import chat_object_manager, ChatObjectProvider, ChatObject
from libro_ai.chat.executor import ChatExecutor
from libro_ai.chat.source import CHAT_SOURCE
from libro_ai.chat.utils import get_message_str

from nbformat import v4
from libro_flow import LibroNotebookClient

from IPython.display import display, clear_output, HTML

from tqdm.notebook import tqdm_notebook
import threading
import time
import os

DEPLOY_ENV = os.environ.get("env", "pre")

# 是否打印debug日志
# PRINT_DEBUG = os.environ.get("print_debug", "false")

# if DEPLOY_ENV == "pre":
#     ZXZBFF_ENDPOINT = "https://zxzcopilotbff-pre.alipay.com"
# else:
#     ZXZBFF_ENDPOINT = "https://zxzcopilotbff.alipay.com"

QE_ENDPOINT = "https://quantexpert-pre.antgroup-inc.cn/service_run"


def getMsgContent(msg):
    # print('msg = ' + str(msg))
    if isinstance(msg, HumanMessage):
        return {
            "type": "human",
            "content": getTextContent(msg)
        }
    if isinstance(msg, AIMessage):
        return {
            "type": "ai",
            "content": getTextContent(msg)
        }


import re
from IPython.display import display


def sanitize_input(query: str) -> str:
    """Sanitize input to the python REPL.
    Remove whitespace, backtick & python (if llm mistakes python console as terminal)
    Args:
        query: The query to sanitize
    Returns:
        str: The sanitized query
    """

    # # Removes `, whitespace & python from start
    # query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
    # # Removes whitespace & ` from end
    # query = re.sub(r"(\s|`)*$", "", query)
    # print('query =!!! = ' + query)
    # return query

    start = query.find('```')
    end = query.find('```', start + 1)
    source = getSource(query[start: end])
    prefix = source[0:9]
    if prefix == "```python":
        source = source[9:len(source)]
    prefix = source[0:3]
    if prefix == "```":
        source = source[3:len(source)]
    suffix = source[len(source) - 3:len(source)]
    if suffix == "```":
        source = source[0:len(source) - 3]
    # print('source = ' + source)
    return source


def executor_by_ipython(output: str, code: str) -> int:
    """A Python code executor. Use this to execute python commands. Input should be a valid python command.
    Args:
        code: pytho code
    """

    if code is None and output is None:
        pass

    if code is not None:
        # 默认取code的
        command = code
    else:
        # 从output中解析第一段python代码
        # 后续要根据环境变量，判断是否解析output中的代码自动执行，减少高危代码
        command = sanitize_input(output)

    try:
        data = {
            "application/vnd.libro.interpreter.code+text": command}
        display(data, raw=True)
        exec(command)
    except Exception as e:
        # print(traceback.format_exc())
        print('Error ocurred while run python code: %s, error = %s' % (command, str(traceback.format_exc())))


def getTextContent(msg):
    if isinstance(msg.content, str):
        return msg.content
    if isinstance(msg.content, List):
        text_content = msg.content[0]
        return text_content.get("text")


def getSource(str):
    source = str
    prefix = source[0:9]
    if prefix == "```python":
        source = source[9:len(source)]
    prefix = source[0:3]
    if prefix == "```":
        source = source[3:len(source)]
    suffix = source[len(source) - 3:len(source)]
    if suffix == "```":
        source = source[0:len(source) - 3]
    return source


def read_txt_files_to_dict(directory):
    """
    读取指定目录下的所有 txt 文件，并将文件名作为键，文件内容作为值存储到一个字典中。

    :param directory: 目录路径
    :return: 包含文件名和文件内容的字典
    """
    try:
        txt_files_dict = {}

        # 确保目录存在
        if not os.path.exists(directory):
            raise FileNotFoundError(f"目录 {directory} 不存在")

        # 遍历目录中的所有文件
        for filename in os.listdir(directory):
            # 构建文件路径
            filepath = os.path.join(directory, filename)

            # 检查文件是否是 txt 文件
            if os.path.isfile(filepath) and filename.endswith('.txt'):
                # 打开并读取文件内容
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    # 将文件名（不包括扩展名）作为键，文件内容作为值存储到字典中
                    key = os.path.splitext(filename)[0]
                    txt_files_dict[key] = content

        return txt_files_dict
    except Exception as e:
        # traceback.print_exc()
        raise e


def check(result, to_display=False):
    start = result.find('```')
    end = result.find('```', start + 1)
    source = getSource(result[start: end])
    if source == '':
        return None
    try:
        if to_display:
            display(HTML("""
            <div style="display: flex; align-items: center">
            <span style="color:rgb(22, 119, 255);padding:0 12px" role="img" aria-label="exclamation-circle" class="anticon anticon-exclamation-circle"><svg viewBox="64 64 896 896" focusable="false" data-icon="exclamation-circle" width="1em" height="1em" fill="currentColor" aria-hidden="true" style="
                width: 32px;
            "><path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm-32 232c0-4.4 3.6-8 8-8h48c4.4 0 8 3.6 8 8v272c0 4.4-3.6 8-8 8h-48c-4.4 0-8-3.6-8-8V296zm32 440a48.01 48.01 0 010-96 48.01 48.01 0 010 96z"></path></svg></span>
            自检中
            </div>"""))
        nb = v4.new_notebook(cells=[
            v4.new_code_cell(source=source),
        ])
        client = LibroNotebookClient(
            nb=nb,
        )
        client.execute()
        if to_display:
            clear_output()
            display(HTML("""
            <div style="display: flex; align-items: center">
            <span style="color:rgb(82, 196, 26);padding:0 12px" role="img" aria-label="exclamation-circle" class="anticon anticon-exclamation-circle"><svg viewBox="64 64 896 896" focusable="false" data-icon="exclamation-circle" width="1em" height="1em" fill="currentColor" aria-hidden="true" style="
                width: 32px;
            "><path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm193.5 301.7l-210.6 292a31.8 31.8 0 01-51.7 0L318.5 484.9c-3.8-5.3 0-12.7 6.5-12.7h46.9c10.2 0 19.9 4.9 25.9 13.3l71.2 98.8 157.2-218c6-8.3 15.6-13.3 25.9-13.3H699c6.5 0 10.3 7.4 6.5 12.7z"></path></svg></span>
            自检成功
            </div>"""))
        return True
    except Exception as e:
        if to_display:
            clear_output()
            display(HTML("""
            <div style="display: flex; align-items: center">
            <span style="color:rgb(255, 77, 79);padding:0 12px" role="img" aria-label="exclamation-circle" class="anticon anticon-exclamation-circle"><svg viewBox="64 64 896 896" focusable="false" data-icon="exclamation-circle" width="1em" height="1em" fill="currentColor" aria-hidden="true" style="
                width: 32px;
            "><path d="M512 64c247.4 0 448 200.6 448 448S759.4 960 512 960 64 759.4 64 512 264.6 64 512 64zm127.98 274.82h-.04l-.08.06L512 466.75 384.14 338.88c-.04-.05-.06-.06-.08-.06a.12.12 0 00-.07 0c-.03 0-.05.01-.09.05l-45.02 45.02a.2.2 0 00-.05.09.12.12 0 000 .07v.02a.27.27 0 00.06.06L466.75 512 338.88 639.86c-.05.04-.06.06-.06.08a.12.12 0 000 .07c0 .03.01.05.05.09l45.02 45.02a.2.2 0 00.09.05.12.12 0 00.07 0c.02 0 .04-.01.08-.05L512 557.25l127.86 127.87c.04.04.06.05.08.05a.12.12 0 00.07 0c.03 0 .05-.01.09-.05l45.02-45.02a.2.2 0 00.05-.09.12.12 0 000-.07v-.02a.27.27 0 00-.05-.06L557.25 512l127.87-127.86c.04-.04.05-.06.05-.08a.12.12 0 000-.07c0-.03-.01-.05-.05-.09l-45.02-45.02a.2.2 0 00-.09-.05.12.12 0 00-.07 0z"></path></svg></span>
            自检失败，请手动调试代码
            </div>"""))
            # display(e)
        return False


v = 0


def parse_file_knowledge_service(params, to_display=False):
    try:
        tqdm = None
        should_stop = None
        thread = None
        global v
        v = 0

        # def tqdm_run(stop_event):
        #     while not stop_event.is_set():
        #         global v
        #         if v < 15:
        #             v = v + 1
        #             tqdm.update(0.5)
        #         time.sleep(0.8)

        # if to_display:
        #     tqdm = tqdm_notebook(total=10)i
        #     should_stop = threading.Event()
        #     thread = threading.Thread(target=tqdm_run, args=[should_stop])
        #     thread.start()
        file_path = '/config/config.txt'  # 文件路径
        with open(file_path, 'r', encoding='utf-8') as file:
            userId = file.read()
        url = ZXZBFF_ENDPOINT + f'/api/libro/parseFileKnowledge?userId={userId}'
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json;charset=UTF-8",
            },
            data=json.dumps(params, ensure_ascii=False).encode("utf-8"),
            timeout=200,
        )
        resp = resp.json()
        result = ""
        if to_display:
            # should_stop.set()
            # thread.join()
            # tqdm.update(10)
            # tqdm.close()
            clear_output()
        if resp["success"] is True:
            res_str = resp.get('data').get('file_info')[0]
            if res_str is not None:
                return res_str
    except Exception as e:
        # print("模型当前忙，请稍后重试。")
        # traceback.print_exc()
        # print("生成失败:", e)
        raise e


def agent_service(service_id, params, to_display=False):
    try:
        # 获取本地的专家知识
        # default_extend_knowledge = read_txt_files_to_dict('/userdata/默认专家知识')
        # params["extend_knowledge"] = []
        # user_extend_knowledge = read_txt_files_to_dict('/userdata/自定义专家知识')
        # params["user_extend_knowledge"] = []

        tqdm = None
        should_stop = None
        thread = None
        global v
        v = 0

        # def tqdm_run(stop_event):
        #     while not stop_event.is_set():
        #         global v
        #         if v < 15:
        #             v = v + 1
        #             tqdm.update(0.5)
        #         time.sleep(0.8)

        # if to_display:
        #     tqdm = tqdm_notebook(total=10)
        #     should_stop = threading.Event()
        #     thread = threading.Thread(target=tqdm_run, args=[should_stop])
        #     thread.start()
        # file_path = '/config/config.txt'  # 文件路径
        # with open(file_path, 'r', encoding='utf-8') as file:
        #     userId = file.read()
        userId = '2088502728605001'
        # params["user_id"] = userId
        # url = ZXZBFF_ENDPOINT + f'/api/libro/queryAgent?userId={userId}'
        url = QE_ENDPOINT
        # print(url)
        # print(json.dumps(
        #     {
        #         "params": params,
        #         "service_id": "quant_expert_service",
        #         "user_id": userId
        #     }
        #     ,
        #     ensure_ascii=False,
        # ).encode("utf-8"))
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json;charset=UTF-8",
            },
            data=json.dumps(
                {
                    "params": params,
                    "service_id": service_id,
                    "user_id": userId
                }
                ,
                ensure_ascii=False,
            ).encode("utf-8"),

            #         data=json.dumps(
            #     {
            #         "params": {
            #             "input": "构建最大回撤因子的信息",
            #             "user_id": "2088422869948903",
            #             "chat_history": [
            #             ]
            #         },
            #         "service_id": "quant_expert_service",
            #         "user_id": "2088502728605001"
            #     },
            #     ensure_ascii=False,
            # ).encode("utf-8"),

            timeout=200,
        )

        # resp = requests.post(
        #     url,
        #     headers={
        #         "Content-Type": "application/json;charset=UTF-8",
        #     },
        #     data=json.dumps(
        #         {
        #             "user_id": "2088502728605001"
        #         },
        #         ensure_ascii=False,
        #     ).encode("utf-8"),
        #     timeout=10,
        # )

        resp = resp.json()
        result = ""
        # if to_display:
        #     # should_stop.set()
        #     # thread.join()
        #     # tqdm.update(10)
        #     # tqdm.close()
        #     clear_output()
        # print(resp)
        if resp["success"] is True:
            res_str = resp.get("result")
            if res_str is not None:
                return json.loads(res_str)
    except Exception as e:
        # traceback.print_exc()
        # print("生成失败:", e)
        raise e


r = None
finished = 0


class QuantExpert_smart_selector(ChatExecutor):
    def run(
            self,
            value,
            **kwargs,
    ) -> Any:
        """
        agent
        """
        try:
            global r, finished
            r = None
            finished = 0
            params = {}
            if isinstance(value, List):
                # print(f'value-len1 = {len(value)}')
                msg = value.pop()
                params = {
                    "input": getTextContent(msg),
                }
                # print(f'value-len1 = {len(value)}')
                if msg is not None:
                    if isinstance(msg.content, List):
                        if len(msg.content) == 2:
                            file_content = msg.content[1]
                            file_type = file_content.get("type")
                            if file_type == "image_url":
                                params["files"] = [
                                    {"type": "image", "url": file_content.get("image_url")}]
                            if file_type == "pdf_url":
                                display(HTML("""
                                <div style="display: flex; align-items: center">
                                <span style="color:rgb(22, 119, 255);padding:0 12px" role="img" aria-label="exclamation-circle" class="anticon anticon-exclamation-circle"><svg viewBox="64 64 896 896" focusable="false" data-icon="exclamation-circle" width="1em" height="1em" fill="currentColor" aria-hidden="true" style="
                                    width: 32px;
                                "><path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm-32 232c0-4.4 3.6-8 8-8h48c4.4 0 8 3.6 8 8v272c0 4.4-3.6 8-8 8h-48c-4.4 0-8-3.6-8-8V296zm32 440a48.01 48.01 0 010-96 48.01 48.01 0 010 96z"></path></svg></span>
                                解析 PDF 文件
                                </div>"""))
                                file_load_result_dict = parse_file_knowledge_service({
                                    "files": [{"type": "pdf", "url": file_content.get("pdf_url")}]})
                                tag = file_load_result_dict.get("tag")
                                params["files"] = [{"type": "pdf", "tag": tag}]
                # print(f'value = {str(value)}')
                if len(value) > 0:
                    params["chat_history"] = list(map(getMsgContent, value))
            elif isinstance(value, StringPromptValue):
                params = {
                    "input": value.to_string(),
                    # 先写死,后面分扩展channel
                    "define_intention": "smart_selector_agent",
                }

            # print(f'params={str(json.dumps(params))}')
            result_dic = agent_service("quant_expert_service_internal", params, True)
            output = result_dic.get("output")
            run_code = None
            if 'run_code' in result_dic:
                run_code = result_dic.get("run_code")

            # should_check = result_dic.get("self_check")
            # if not should_check:
            #     return result
            if output is not None or run_code is not None:

                clear_output()
                if isinstance(output, str):
                    data = {"application/vnd.libro.prompt+json": output}
                    display(data, raw=True)
                # if isinstance(result, AIMessage):
                #     data = {"application/vnd.libro.prompt+json": result.content}
                #     display(data, raw=True)
                # from libro_ai.chat.utils import executor_by_ipython
                # print('executor_by_ipython?????')
                executor_by_ipython(output, run_code)
                return output

                # return result
            else:
                return "模型当前忙，请稍后重试。"

        except Exception as e:
            print(traceback.format_exc())
            return "模型当前忙，请稍后重试。"


class ExpertProvider(ChatObjectProvider):
    name: str = "ant-quantV2"
    quant_smart_selector: QuantExpert_smart_selector = QuantExpert_smart_selector(name="QuantExpert_smart_selectorV2")

    def list(self):
        return [
            ChatObject(
                name="smart_selectorV2",
                to_executor=lambda: self.quant_smart_selector,
                type=CHAT_SOURCE["CUSTOM"],
            ),
        ]


expert_provider = ExpertProvider()
chat_object_manager.register_provider(expert_provider)
