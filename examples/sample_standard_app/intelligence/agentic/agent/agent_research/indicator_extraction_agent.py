#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/02 00:44
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : indicator_extraction_agent.py
# @Software: PyCharm

# @FileName: indicator_extraction_agent.py

import json
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.util.logging.logging_util import LOGGER
from dfdatapsdk import dfd_client
from dfdatapsdk.configs.sys_config import SysConfig
from sample_standard_app.app.core.agent.asset_research.utils import *
SysConfig.set_app_name("finassetpreference")
SysConfig.set_db_mode("dev")
SysConfig.set_token("fap.antalpha.2A")

class IndicatorExtractionAgent(Agent):
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
        required_keys = ["factor_name", "frequency_desc", "period_desc", "start_date", "end_date"]
        if not all(key in factor_meta_params for key in required_keys):
            raise KeyError(f"缺少必要的入参。需要的参数为: {required_keys}")

        # 2. 提取参数
        factor_name = factor_meta_params["factor_name"]
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

        # 3. 调用 META 接口
        try:
            dfd_data = dfd_client.query_fact(
                data_id="antmeta_fund_factor_model",
                tags={
                    'frequency': [frequency_desc],
                    'factor': [factor_name],
                    'period': [period_desc]
                },
                fields=['the_datetime', 'symbol', 'factor', 'value'],
                # slot_direction = 'DESC',
                # slot_num = 1,
                start=start_date,
                end=end_date,
                db_mode="sim",
                token="fap.antalpha.2A"
            )
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
                LOGGER.warn(f"查询结果: \n")
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
    agent = AgentManager().get_instance_obj('indicator_extraction_agent')

    # 测试输入
    indicator_dict = {'在指标库': True, '指标名称': '最大回撤', '时间频率': '日频', '回溯区间': '近1年', '开始时间': "2024-10-20", '截止时间': "2024-10-21", '指标代码': 'Ind0'}

    # 运行智能体
    res = agent.run(input=indicator_dict)
    LOGGER.info(res)

    # 打印输出
    LOGGER.info(f"用户输入: {indicator_dict}")
    LOGGER.info(f"模型识别入参: {res.to_dict()['output']}")
    LOGGER.info(f"模型输出: {res.to_dict()['data']}")
    LOGGER.info(f"input={indicator_dict}, output={res.to_dict()['data']}")

    # factor_meta_params_str = res.to_dict()['output']
    #
    # # 1. 解析 JSON 字符串为字典
    # try:
    #     # 去除字符串中的JSON格式标记
    #     cleaned_str = factor_meta_params_str.strip('```json\n').strip('\n```')
    #     # 使用json.loads()函数解析字符串为字典
    #     factor_meta_params = json.loads(cleaned_str)
    #     # 输出解析后的字典
    #     LOGGER.info(factor_meta_params)
    # except json.JSONDecodeError as e:
    #     LOGGER.info("JSON 解析错误:", e)
    #     factor_meta_params = {}
    #
    # # 检查必要的键是否存在
    # required_keys = ["factor_name", "frequency_desc", "period_desc", "start_date", "end_date"]
    # if not all(key in factor_meta_params for key in required_keys):
    #     raise KeyError(f"缺少必要的键。需要的键: {required_keys}")
    #
    # # 2. 提取参数
    # factor_name = factor_meta_params["factor_name"]
    # frequency_desc = factor_meta_params["frequency_desc"]
    # period_desc = factor_meta_params["period_desc"]
    # # 检查并添加 00:00:00 到日期末尾
    # if not factor_meta_params['start_date'].endswith('00:00:00'):
    #     start_date = f"{factor_meta_params['start_date']} 00:00:00"
    # else:
    #     start_date = factor_meta_params['start_date']
    # if not factor_meta_params['end_date'].endswith('00:00:00'):
    #     end_date = f"{factor_meta_params['end_date']} 00:00:00"
    # else:
    #     end_date = factor_meta_params['end_date']
    #
    #
    # # 3. 调用 query_fact 接口
    # try:
    #     dfd_data = dfd_client.query_fact(
    #         data_id="antmeta_fund_factor_model",
    #         tags={
    #             'frequency': [frequency_desc],
    #             'factor': [factor_name],
    #             'period': [period_desc]
    #         },
    #         fields=['the_datetime', 'symbol', 'factor', 'value'],
    #         # slot_direction = 'DESC',
    #         # slot_num = 1,
    #         start=start_date,
    #         end=end_date,
    #         db_mode="sim",
    #         token="fap.antalpha.2A"
    #     )
    # except Exception as e:
    #     LOGGER.info("调用 query_fact 接口时出错:", e)
    #     dfd_data = None
    #
    # # 4. 检查是否成功获取数据
    # if dfd_data is not None:
    #     try:
    #         result = {
    #             "指标代码": indicator_dict['指标代码'],
    #             "数据": dfd_data.copy()
    #         }
    #         LOGGER.info("查询结果:")
    #         LOGGER.info(result)
    #     except AttributeError:
    #         result = {
    #             "指标代码": indicator_dict['指标代码'],
    #             "数据": dfd_data.copy()
    #         }
    #         LOGGER.info("查询结果:")
    #         LOGGER.info(result)
    # else:
    #     LOGGER.info("未能获取查询数据。")



    # dfd_data = dfd_client.query_fact(
    #     data_id="antmeta_fund_factor_model",
    #     tags={
    #         # 'symbol': ['002301'],
    #         'frequency': ['day'],
    #         'factor': ['max_drawdown'],
    #         'period': ['3m']
    #     },
    #     fields=['the_datetime', 'symbol', 'factor', 'value'],
    #     # slot_direction = 'DESC',
    #     # slot_num = 1,
    #     # start='2024-11-21 00:00:00',
    #     # start_excluded=False,
    #     # end='2024-11-21 00:00:00',
    #     # end_excluded=False,
    #     db_mode="sim",
    #     # db_mode="sim",
    #     # token="dfdata.quality"
    #     token="fap.antalpha.2A"
    #     # token = "fap.antalpha.2A.write"
    # )
    # LOGGER.info(dfd_data)






