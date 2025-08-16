#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/9 16:17
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : indicator_calculation_agent.py
# @Software: PyCharm


from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
import pandas as pd
from datetime import datetime
import json
from agentuniverse.base.util.logging.logging_util import LOGGER


class IndicatorCalculationAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['indicator_list', 'indicator_algorithm', 'NV_data', 'error_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        agent_input['requirement'] = input_object.get_data('requirement')
        agent_input['indicator_list'] = input_object.get_data('indicator_list')
        agent_input['indicator_algorithm'] = input_object.get_data('indicator_algorithm')
        agent_input['NV_data'] = input_object.get_data('NV_data')
        agent_input['error_info'] = input_object.get_data('error_info')
        return agent_input

    def parse_result(self, planner_result: dict) -> dict:
        # 假设planner_result包含执行的代码和执行结果
        return planner_result


if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_calculation_agent')

    # Test case 1: Calculate Sharpe Ratio
    indicator_list = {'在指标库': False, '指标名称': '年化收益率', '资产类型': '公募基金', '时间频率': '日', '回溯区间': '近1年', '开始时间': '2024-01-01', '截止时间': '2024-12-31', '指标代码': 'Ind0'}
    indicator_algorithm = {'指标代码': 'Ind0', '指标名称': '年化收益率', '用户描述': '按照一年365天口径，计算年化收益率', '指标算法': '为了计算年化收益率，根据用户提供的指标信息和公式，我们需要遵循以下步骤：\n\n### 所需数据\n1. **初始净值**：在回溯区间的开始时间（2024-01-01）时的基金净值。\n2. **结束净值**：在回溯区间的截止时间（2024-12-31）时的基金净值。\n3. **投资天数**：从开始时间到截止时间的天数。\n\n### 计算步骤\n1. **获取初始净值和结束净值**：\n   - 从基金的净值数据中提取2024-01-01的净值作为初始净值。\n   - 从基金的净值数据中提取2024-12-31的净值作为结束净值。\n\n2. **计算投资内收益**：\n   - 投资内收益 = 结束净值 - 初始净值\n\n3. **计算投资天数**：\n   - 计算从2024-01-01到2024-12-31的天数。由于2024年是闰年，这段时间包含366天。\n\n4. **计算年化收益率**：\n   - 使用公式：年化收益率 = (投资内收益 / 初始净值) / 投资天数 × 365 × 100%\n   - 具体步骤：\n     - 计算收益率 = 投资内收益 / 初始净值\n     - 计算日均收益率 = 收益率 / 投资天数\n     - 计算年化收益率 = 日均收益率 × 365 × 100%\n\n5. **输出年化收益率**：\n   - 将计算得到的年化收益率作为最终结果输出。\n\n### 注意事项\n- 确保净值数据的准确性和完整性。\n- 确保日期计算的准确性，特别是在处理闰年时。\n- 结果应以百分比形式表示。\n\n通过以上步骤，可以准确计算出公募基金在指定时间段内的年化收益率。'}
    NV_data = pd.DataFrame(
        {
            'restored_net_value': [1.0000, 1.0000, 1.0000, 1.0000, 1.3960, 1.3968, 1.0000, 0.9993],
            'symbol': ['000003.OF', '000003.OF', '000003.OF', '000003.OF', '022851.OF', '022851.OF', '159320.OF', '159320.OF'],
            'net_value_date': [
                datetime(2013, 3, 20), datetime(2013, 3, 22), datetime(2013, 3, 25), datetime(2013, 3, 26),
                datetime(2024, 12, 12), datetime(2024, 12, 13), datetime(2024, 12, 12), datetime(2024, 12, 13)
            ]
        }
    )

    res = agent.run(
        indicator_list=indicator_list,
        indicator_algorithm=indicator_algorithm,
        NV_data=NV_data,
        error_info=''
    )

    print(res.to_dict())
    LOGGER.info(f"Generated calculation code:\n{res.to_dict()['output']}")


