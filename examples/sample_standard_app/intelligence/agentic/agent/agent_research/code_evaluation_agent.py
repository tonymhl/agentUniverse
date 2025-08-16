#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/20 17:57
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : code_evaluation_agent.py
# @Software: PyCharm


from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
import pandas as pd
from datetime import datetime
import json
from agentuniverse.base.util.logging.logging_util import LOGGER
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager


class CodeEvaluationAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['code', 'indicator_data', 'result', 'task']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        agent_input['code'] = input_object.get_data('code')
        agent_input['indicator_data'] = input_object.get_data('indicator_data')
        agent_input['result'] = input_object.get_data('result')
        agent_input['task'] = input_object.get_data('task')
        return agent_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


if __name__ == '__main__':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    code_evaluation_agent = AgentManager().get_instance_obj('code_evaluation_agent')

    # test case
    code = 'import pandas as pd\n\ndef filter_products(indicator_data: dict) -> pd.DataFrame:\n    try:\n        # Extract data for each indicator\n        ind0_data = indicator_data.get(\'Ind0\')\n        ind1_data = indicator_data.get(\'Ind1\')\n\n        if ind0_data is None or ind1_data is None:\n            raise ValueError("Missing data for one or more indicators.")\n\n        # Convert \'the_datetime\' to datetime for filtering\n        ind0_data[\'the_datetime\'] = pd.to_datetime(ind0_data[\'the_datetime\'])\n        ind1_data[\'the_datetime\'] = pd.to_datetime(ind1_data[\'the_datetime\'])\n\n        # Filter data based on the start and end dates\n        start_date = pd.to_datetime(\'2024-01-01\')\n        end_date = pd.to_datetime(\'2024-12-20\')\n        ind0_filtered = ind0_data[(ind0_data[\'the_datetime\'] >= start_date) & (ind0_data[\'the_datetime\'] <= end_date)]\n        ind1_filtered = ind1_data[(ind1_data[\'the_datetime\'] >= start_date) & (ind1_data[\'the_datetime\'] <= end_date)]\n\n        # Merge the data on \'symbol\'\n        merged_data = pd.merge(ind0_filtered, ind1_filtered, on=\'symbol\', suffixes=(\'_Ind0\', \'_Ind1\'))\n\n        # Apply the filtering condition\n        condition = (merged_data[\'value_Ind0\'] > 0.8) & (merged_data[\'value_Ind1\'] <= 0.5)\n        filtered_df = merged_data[condition]\n\n        # Select relevant columns to return\n        filtered_df = filtered_df[[\'symbol\', \'value_Ind0\', \'value_Ind1\']]\n\n        return filtered_df\n\n    except Exception as e:\n        print(f"An error occurred: {e}")\n        return pd.DataFrame()'

    result = pd.DataFrame([
        {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '013239',
         'value': 0.296034},
        {'period': '1y', 'the_datetime': '2024-06-04', 'factor': 'max_drawdown', 'symbol': '013239',
         'value': 0.296034},
        {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '009420',
         'value': 0.055130}
    ])

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

    result = pd.DataFrame([
        {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '013239',
         'value': 0.296034},
        {'period': '1y', 'the_datetime': '2024-06-04', 'factor': 'max_drawdown', 'symbol': '013239',
         'value': 0.296034},
        {'period': '1y', 'the_datetime': '2024-06-03', 'factor': 'max_drawdown', 'symbol': '009420',
         'value': 0.055130}
    ])

    task = {'资产类型': '公募基金',
            '产品池': '固收+',
            '条件表达式': '$Ind0$ > 0.8 and $Ind1$ <= 0.5',
            '开始时间': '2024-01-01',
            '截止时间': '2024-12-20',
            '在指标库': False}

    result = code_evaluation_agent.run(code=code, indicator_data=indicator_data, result=result, task="filter")
    print(result.to_dict())
    print(result.to_dict()['output'])
    LOGGER.warn('code_evaluation_agent产出结果 \n ')
    LOGGER.info((result.to_dict()['output']))

