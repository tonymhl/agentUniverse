#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2025/2/17 19:06
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : get_NL2INDICATOR.py
# @Software: PyCharm


import requests
from prettyprinter import pformat


def get_indicator_output(input_text):
    """
    通过输入文本获取指标信息

    Args:
        input_text (str): 查询文本，如"高端近三年超额胜率"

    Returns:
        str(Dict): 包含指标数据的列表
        None: 请求失败时返回
    """
    url = "https://dfdataagent-pre.antgroup-inc.cn/service_run"
    headers = {"Content-Type": "application/json"}
    payload = {
        "service_id": "nl2indicator_service",
        "params": {
            "input": input_text
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # 检查 HTTP 错误
        result = response.json()

        # 返回指标信息
        return result.get('result')

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return None
    except ValueError:
        print("响应解析失败")
        return None


# 使用示例
if __name__ == "__main__":
    input_query = "高端近三年超额胜率"
    result = get_indicator_output(input_query)

    if result:
        try:
            # 将 output 转换为字典
            output = eval(result)
        except Exception as e:
            print(f"无法解析输出: {e}")
        output = output.get('output')
        print(f"获取到 {len(output)} 条结果：")
        print(pformat(output))
        for item in output[:3]:  # 打印前3条结果
            print(f"{item['TopN']}: {item['indicator']}")
    else:
        print("查询失败")





