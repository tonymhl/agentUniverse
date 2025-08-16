#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/14 00:44
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : indicator_nscode_extraction_agent.py
# @Software: PyCharm


import json
import logging
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
# from agentuniverse.base.util.logging.logging_util import LOGGER
from sample_standard_app.platform.base_lib.logger.logger_conf import Logger
from sample_standard_app.platform.base_lib.logger.logger_type import LoggerType
from dfdatapsdk import dfd_client
from dfdatapsdk.configs.sys_config import SysConfig
from sample_standard_app.app.core.agent.asset_research.utils import *
SysConfig.set_app_name("finassetpreference")
SysConfig.set_db_mode("dev")
SysConfig.set_token("fap.antalpha.2A")

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
LOGGER = logging.getLogger(__name__)

class IndicatorNSCodeExtractionAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'error_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        input_text = input_object.get_data('input')
        planner_input['input'] = input_text
        planner_input['error_info'] = input_object.get_data('error_info')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()

        factor_meta_params_str = planner_result['output']
        # 1. 解析 JSON 字符串为字典
        try:
            # 去除字符串中的JSON格式标记
            cleaned_str = factor_meta_params_str.strip('```json\n').strip('\n```')
            # 使用json.loads()函数解析字符串为字典
            factor_meta_params = json.loads(cleaned_str)
            # 输出解析后的字典
            LOGGER.info(f"解析输出: \n"
                        f"{factor_meta_params}")
        except json.JSONDecodeError as e:
            LOGGER.info("JSON 解析错误:", e)
            factor_meta_params = {}

        # 检查必要的键是否存在
        required_keys = ["ns_code", "frequency_desc", "period_desc", "start_date", "end_date"]
        if not all(key in factor_meta_params for key in required_keys):
            raise KeyError(f"缺少必要的入参。需要的参数为: {required_keys}")

        # 2. 提取参数
        ns_code = factor_meta_params["ns_code"]
        frequency_desc = factor_meta_params["frequency_desc"]
        period_desc = factor_meta_params["period_desc"]

        # 检查并处理 None 值
        if factor_meta_params['start_date'] is None:
            start_date = ''
        else:
            # 检查并添加 00:00:00 到日期末尾
            if not factor_meta_params['start_date'].endswith('00:00:00'):
                start_date = f"{factor_meta_params['start_date']} 00:00:00"
            else:
                start_date = factor_meta_params['start_date']

        if factor_meta_params['end_date'] is None:
            end_date = ''
        else:
            # 检查并添加 00:00:00 到日期末尾
            if not factor_meta_params['end_date'].endswith('00:00:00'):
                end_date = f"{factor_meta_params['end_date']} 00:00:00"
            else:
                end_date = factor_meta_params['end_date']

        # 3. 调用 quote_alpha_simple_factor_ns 查询 ns_code 指标数据
        try:
            LOGGER.info(f"调用 query_fact 接口，参数为: \n"
                        f"nscode={ns_code}, \n"
                        f"period=[{period_desc}], \n"
                        f"frequency=[{frequency_desc}], \n"
                        f"d0={start_date}, \n"
                        f"d1={end_date}, \n"
                        f"brief=True")
            dfd_data = quote_alpha_simple_factor_ns(
                nscode=ns_code,
                filter=None,
                period=[period_desc],
                frequency=[frequency_desc],
                d0=start_date,
                d1=end_date,
                brief=True)
        except Exception as e:
            LOGGER.info("调用 query_fact 接口时出错:", e)
            dfd_data = None

        # 4. 检查是否成功获取数据
        if dfd_data is not None:
            try:
                result_data = {
                    "指标代码": planner_result['input']['指标代码'],
                    "数据": dfd_data.copy()
                }
                LOGGER.info(f"查询结果: \n")
                LOGGER.info(result_data)
            except AttributeError:
                result_data = {
                    "指标代码": planner_result['input']['指标代码'],
                    "数据": dfd_data.copy()
                }
                LOGGER.info("查询结果: \n")
                LOGGER.info(result_data)
        else:
            LOGGER.info("未能获取查询数据。")
            result_data = None

        result["data"] = result_data

        return result

if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    # 启动 AgentUniverse
    AgentUniverse().start(config_path='../../../../config/config.toml')

    # 获取智能体实例
    agent = AgentManager().get_instance_obj('indicator_nscode_extraction_agent')

    # 测试输入
    indicator_dict = {'库编码': 'fund.indicator.max_drawdown',
                      '指标名称': '最大回撤',
                      '资产类型': '公募基金',
                      '时间频率': '日',
                      '回溯区间': '近1年',
                      '开始时间': '2024-01-01',
                      '截止时间': '2024-12-26',
                      '指标代码': 'Ind1'}

    # 运行智能体
    res = agent.run(input=indicator_dict, error_info='')
    LOGGER.info(res)

    # 打印输出
    LOGGER.info(f"用户输入: {indicator_dict}")
    LOGGER.info(f"模型识别入参: {res.to_dict()['output']}")
    LOGGER.info(f"模型输出: {res.to_dict()['data']}")
    LOGGER.info(f"input={indicator_dict}, output={res.to_dict()['data']}")


