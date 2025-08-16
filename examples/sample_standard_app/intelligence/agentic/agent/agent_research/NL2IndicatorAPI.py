#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2025/2/18 16:09
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : NL2IndicatorAPI.py
# @Software: PyCharm


import json
import logging
from typing import Optional, Dict, List, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 全局配置
DEFAULT_TIMEOUT = 10  # 默认超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数
RETRY_STATUS_CODES = (500, 502, 503, 504)  # 需要重试的状态码


class NL2IndicatorClient:
    """NL2INDICATOR服务端"""

    def __init__(
            self,
            endpoint: str = "https://dfdataagent-pre.antgroup-inc.cn/service_run",
            service_id: str = "nl2indicator_service",
            timeout: int = DEFAULT_TIMEOUT,
            max_retries: int = MAX_RETRIES
    ):
        """
        初始化客户端

        :param endpoint: 服务端点URL
        :param service_id: 服务标识
        :param timeout: 请求超时时间（秒）
        :param max_retries: 最大重试次数
        """
        self.endpoint = endpoint
        self.service_id = service_id
        self.timeout = timeout

        # 配置带重试机制的Session
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=['POST']
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

        # 公共请求头
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "NL2IndicatorClient/1.0"
        }

    def get_indicator_output(
            self,
            input_text: str,
            **kwargs
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取指标输出（线程安全）

        :param input_text: 自然语言查询文本
        :return: 指标列表（失败返回None）
        """
        payload = {
            "service_id": self.service_id,
            "params": {"input": input_text}
        }

        try:
            response = self.session.post(
                url=self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()

            result = response.json()
            if not isinstance(result, dict):
                logger.error("响应格式异常: 非字典类型")
                return None

            # 解析嵌套结构
            raw_result = result.get('result')
            if not raw_result:
                logger.warning("响应中缺少 result 字段")
                return None

            try:
                parsed_result = json.loads(raw_result)  # 更安全的解析方式
            except json.JSONDecodeError:
                logger.error("结果解析失败: 非标准JSON格式")
                return None

            return parsed_result.get('output')

        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {str(e)}")
        except json.JSONDecodeError:
            logger.error("响应解析失败: 非JSON格式")
        except KeyError as e:
            logger.error(f"响应字段缺失: {str(e)}")
        except Exception as e:
            logger.error(f"未知错误: {str(e)}", exc_info=True)

        return None


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = NL2IndicatorClient(
        timeout=15,
        max_retries=3
    )

    # 执行查询
    input_query = "高端近三年超额胜率"
    output = client.get_indicator_output(input_query)
    print(f"查询 '{input_query}' 返回结果 \n {output if output else None}")

    # 处理结果
    if output:
        logger.info(f"获取到 {len(output)} 条结果")
        for idx, item in enumerate(output[:3], 1):
            print(f"[{item.get('TopN', '未知')}] {item.get('indicator', '无指标名称')}")
            if idx == 1:  # 打印第一条完整信息
                print("示例完整记录:")
                print(json.dumps(item, indent=2, ensure_ascii=False))
    else:
        logger.warning("查询未返回有效结果")


# # 并发调用示例
# if __name__ == "__main__":
#     from concurrent.futures import ThreadPoolExecutor
#     def concurrent_demo():
#         client = NL2IndicatorClient()
#         queries = [
#             "高端近一年累计收益率",
#             "高端近两年最大回撤",
#             "高端近三年超额胜率"
#         ]
#
#         with ThreadPoolExecutor(max_workers=4) as executor:
#             futures = {
#                 executor.submit(client.get_indicator_output, q): q
#                 for q in queries
#             }
#
#             for future in futures:
#                 query = futures[future]
#                 try:
#                     result = future.result()
#                     print(f"查询 '{query}' 返回 {len(result) if result else 0} 条结果")
#                 except Exception as e:
#                     print(f"查询 '{query}' 失败: {str(e)}")



