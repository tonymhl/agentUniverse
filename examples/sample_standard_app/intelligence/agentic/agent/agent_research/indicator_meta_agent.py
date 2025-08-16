#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/4 11:56
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : indicator_meta_agent.py
# @Software: PyCharm


import json
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.util.logging.logging_util import LOGGER
from agentuniverse.agent.action.tool.tool_manager import ToolManager  # 假设存在 ToolManager
from typing import Any

class IndicatorMetaAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        input_text = input_object.get_data('input')
        # 直接将用户输入传递给工具
        planner_input['input'] = input_text
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result

if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    # 启动 AgentUniverse
    AgentUniverse().start(config_path='../../../../config/config.toml')

    # 获取智能体实例
    agent = AgentManager().get_instance_obj('indicator_meta_agent')

    # 测试输入
    indicator_dict = str({'在指标库': True, '指标名称': '最大回撤', '时间频率': '日频', '回溯区间': '近1年', '开始时间': "2024-10-21", '截止时间': "2024-10-21", '指标代码': 'Ind0'})


    # 运行智能体
    res = agent.run(input=indicator_dict)
    print(res)

    # 打印输出
    LOGGER.info(f"用户输入: {indicator_dict}")
    LOGGER.info(f"模型输出: {res.to_dict()['output']}")
    print(f"input={indicator_dict}, output=" + res.to_dict()['output'])
