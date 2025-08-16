#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/6 17:55
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : filter_indicator_agent.py
# @Software: PyCharm


from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
import json
from agentuniverse.base.util.logging.logging_util import LOGGER

class FilterIndicatorAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['requirement', 'indicator_list', 'indicator_data', 'filter_condition', 'error_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        agent_input['requirement'] = input_object.get_data('requirement')
        agent_input['indicator_list'] = input_object.get_data('indicator_list')
        agent_input['indicator_data'] = input_object.get_data('indicator_data')
        agent_input['filter_condition'] = input_object.get_data('filter_condition')
        agent_input['error_info'] = input_object.get_data('error_info')
        return agent_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('filter_indicator_agent')

    requirement = '我想提取固收+近1年年化收益率超过0.8，且近一年最大回撤不超过50%的产品'

    indicator_list = [
        {'在指标库': True, '指标名称': '年化超额收益', '资产类型': '公募基金', '时间频率': '日', '回溯区间': '近1年', '开始时间': '无', '截止时间': '无', '指标代码': 'Ind0'},
        {'在指标库': True, '指标名称': '正收益概率', '资产类型': '公募基金', '时间频率': '日', '回溯区间': '近3个月', '开始时间': '无', '截止时间': '无', '指标代码': 'Ind1'}
    ]
    filter_condition = {'资产类型': '公募基金', '产品池': '固收+', '筛选条件': '$Ind0$ > 0.8 and $Ind1$ < 0.5', '开始时间': '无', '截止时间': '无'}
    # 测试输入
    indicator_data = [
        {
            '指标代码': 'Ind0',
            '数据': [
                {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'annual_returns', 'symbol': '013239',
                 'value': -0.080433},
                {'period': '1y', 'the_datetime': '2024-06-04', 'factor': 'annual_returns', 'symbol': '013239',
                 'value': -0.071420},
                {'period': '1y', 'the_datetime': '2024-07-26', 'factor': 'annual_returns', 'symbol': '013239',
                 'value': -0.095427}
            ]
        },
        {
            '指标代码': 'Ind1',
            '数据': [
                {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '013239',
                 'value': 0.296034},
                {'period': '1y', 'the_datetime': '2024-06-04', 'factor': 'max_drawdown', 'symbol': '013239',
                 'value': 0.296034},
                {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '009420',
                 'value': 0.055130}
            ]
        }
    ]


    res = agent.run(requirement=requirement,
                    indicator_list=indicator_list,
                    indicator_data=indicator_data,
                    filter_condition=filter_condition,
                    error_info='')
    print(res.to_dict())
    print(res.to_dict()['output'])
    LOGGER.warn('filter_indicator_agent产出代码 \n ')
    LOGGER.info((res.to_dict()['output']))
