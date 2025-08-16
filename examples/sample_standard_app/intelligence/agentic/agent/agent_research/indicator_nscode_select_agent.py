#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/26 00:44
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : indicator_nscode_select_agent.py
# @Software: PyCharm


import json
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.util.logging.logging_util import LOGGER
# from dfdatapsdk import dfd_client
# from dfdatapsdk.configs.sys_config import SysConfig
from sample_standard_app.app.core.agent.asset_research.utils import *
# SysConfig.set_app_name("finassetpreference")
# # SysConfig.set_db_mode("dev")
# SysConfig.set_db_mode("dev")
# SysConfig.set_token("fap.antalpha.2A")


AssetMapping = {
    "公募基金": "FUND",
    "A股": "STOCK",
    "专户": "SPECIAL_ACCOUNT",
    "私募基金": "SIMU",
}

FreqMapping = {
    "日": "day",
    "周": "week",
    "月": "month",
    "季": "quarter",
    "半年": "halfyear",
    "年": "year"
}

PeriodMapping = {
    "成立以来": "daystart",
    "今年以来": "yearsince",
    "近n日": "nd",
    "近n月": "nm",
    "近n年": "ny"
}

IndicatorQueryPrompt = {
    "库编码": "当前值: {current}",
    "指标名称": "当前值: {current}",
    "资产类型": f"可选值: {', '.join(AssetMapping.keys())}, 当前值: {{current}}",
    "时间频率": f"可选值: {', '.join(FreqMapping.keys())}, 当前值: {{current}}",
    "回溯区间": f"可选值: {', '.join(PeriodMapping.keys())}, 当前值: {{current}}",
    "开始时间": "建议格式: 'yyyy-mm-dd', 当前值: {current}",
    "截止时间": "建议格式: 'yyyy-mm-dd', 当前值: {current}"
}

def validate_indicator_query(indicator_query, keys=None):
    indicator_query = indicator_query.copy()
    if keys is None: keys = list(indicator_query.keys())
    Errors = {}
    for iKey in keys:
        iVal = indicator_query[iKey]
        if iKey in ("开始时间", "截止时间"):
            try:
                pd.to_datetime(iVal)
            except:
                Errors[iKey] = f"'{iKey}' 格式有误: {iVal} 无法转化成日期!"
        elif iKey == "资产类型":
            if iVal not in AssetMapping:
                Errors[iKey] = f"'{iKey}' 格式有误: 尚不支持的资产类型 '{iVal}'"
        elif iKey == "时间频率":
            if iVal not in FreqMapping:
                Errors[iKey] = f"'{iKey}' 格式有误: 尚不支持的时间频率 '{iVal}'"
        elif iKey == "回溯区间":
            iNewVal = re.sub("\d+", "n", iVal)
            if iNewVal not in PeriodMapping:
                Errors[iKey] = f"'{iKey}' 格式有误: 尚不支持的回溯区间 '{iVal}'"
        elif iKey == "库编码":
            indicator_query[iKey] = iVal
    return Errors, indicator_query

def set_indicator_default(indicator_query, indicator_list=[]):
    Defaults = {}
    if indicator_list:
        indicator_list = pd.DataFrame(indicator_list)
        for iKey in ["资产类型", "截止时间", "开始时间", "时间频率", "回溯区间"]:
            if indicator_list[iKey].notnull().any():
                Defaults[iKey] = indicator_list.groupby([iKey])[iKey].count().idxmax()
    adjusted_query = {}
    for iKey in list(indicator_query.keys()):
        iVal = indicator_query[iKey]
        if pd.notnull(iVal):
            adjusted_query[iKey] = iVal
            continue
        if iKey == "截止时间":
            adjusted_query[iKey] = Defaults.get("截止时间", dt.datetime.today().date().strftime("%Y-%m-%d"))
        elif iKey == "开始时间":
            iEndDT = (pd.to_datetime(indicator_query["截止时间"]) if pd.notnull(indicator_query["截止时间"]) else dt.datetime.today())
            adjusted_query[iKey] = Defaults.get("开始时间", iEndDT.date().strftime("%Y-%m-%d"))
        elif iKey == "资产类型":
            adjusted_query[iKey] = Defaults.get("资产类型", "公募基金")
        elif iKey == "时间频率":
            adjusted_query[iKey] = Defaults.get("时间频率", "日")
        elif iKey == "回溯区间":
            adjusted_query[iKey] = Defaults.get("回溯区间", None)
        elif iKey == "库编码":
            adjusted_query[iKey] = Defaults.get("库编码", None)
        else:
            adjusted_query[iKey] = None
    return adjusted_query

def set_filter_default(filter, indicator_list):
    if indicator_list:
        indicator_list = pd.DataFrame(indicator_list)
        Defaults = {
            "资产类型": indicator_list.groupby(["资产类型"])["资产类型"].count().idxmax(),
            "截止时间": indicator_list.groupby(["截止时间"])["截止时间"].count().idxmax(),
            "开始时间": indicator_list.groupby(["开始时间"])["开始时间"].count().idxmax(),
        }
    else:
        Defaults = {}
    adjusted_filter = {}
    for iKey in list(filter.keys()):
        iVal = filter[iKey]
        if pd.notnull(iVal):
            adjusted_filter[iKey] = iVal
            continue
        if iKey == "截止时间":
            adjusted_filter[iKey] = Defaults.get("截止时间", dt.datetime.today().date().strftime("%Y-%m-%d"))
        elif iKey == "开始时间":
            adjusted_filter[iKey] = Defaults.get("开始时间", dt.datetime.today().date().strftime("%Y-%m-%d"))
        elif iKey == "资产类型":
            adjusted_filter[iKey] = Defaults.get("资产类型", "公募基金")
        else:
            adjusted_filter[iKey] = None
    return adjusted_filter

def adjust_indicator_query(indicator_query):
    indicator_query = indicator_query.copy()
    for iKey, iVal in list(indicator_query.items()):
        if iKey in ("开始时间", "截止时间"):
            try:
                pd.to_datetime(iVal)
            except:
                indicator_query[iKey] = None
        elif iKey == "资产类型":
            if iVal not in AssetMapping:
                indicator_query[iKey] = None
        elif iKey == "时间频率":
            if iVal not in FreqMapping:
                indicator_query[iKey] = None
        elif iKey == "回溯区间":
            if isinstance(iVal, str):
                iNewVal = re.sub("\d+", "n", iVal)
                if iNewVal not in PeriodMapping:
                    iNewVal = iNewVal.replace("个", "")
                    if iNewVal not in PeriodMapping:
                        indicator_query[iKey] = None
                    else:
                        indicator_query[iKey] = iVal.replace("个", "")
            else:
                indicator_query[iKey] = None
        elif iKey == "库编码":
            if not isinstance(iVal, str):
                indicator_query[iKey] = None
        elif iKey == "指标代码":
            indicator_query[iKey] = iVal
        elif iKey not in IndicatorQueryPrompt:
            indicator_query.pop(iKey)
    NewQuery = {iKey: None for iKey in IndicatorQueryPrompt.keys()}
    NewQuery.update(indicator_query)
    return NewQuery

def extract_json(s):
    p = re.compile("(\{(.|\n)*?\})")
    groups = re .findall(p, s)
    json_list = []
    for ijson_str, _ in groups:
        try:
            ijson = json.loads(ijson_str)
        except:
            print(f"无法解析的 json: {ijson_str}")
        else:
            json_list.append(ijson)
    return json_list

class IndicatorNSCodeSelectAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['indicator_list', 'alternative_indicators', 'error_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        indicator_list = input_object.get_data('indicator_list')
        alternative_indicators = input_object.get_data("alternative_indicators")
        if indicator_list:
            adjusted_indicator_list = ["当前给定的指标列表是: "]
            for iIndicator in indicator_list:
                adjusted_indicator_list.append(json.dumps(iIndicator, ensure_ascii=False))
                if iIndicator["指标代码"] in alternative_indicators:
                    adjusted_indicator_list.append(f"{iIndicator['指标名称']} 指标库里的候选指标有: ")
                    iAlternatives = [json.dumps({
                        "库编码": iIndicator["库编码"],
                        "指标名称": iIndicator["指标名称"],
                        "指标描述": iIndicator["元信息"]["onecode_factor_description"],
                    }, ensure_ascii=False) for iIndicator in alternative_indicators[iIndicator["指标代码"]]]
                    adjusted_indicator_list.append(f"{iAlternatives}")
            planner_input['indicator_list'] = indicator_list
            planner_input['alternative_indicators'] = "\n".join(adjusted_indicator_list)
        else:
            raise Exception("indicator_nscode_select_agent: 指标列表不能为空!")
        planner_input['error_info'] = input_object.get_data('error_info')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        indicator_list = extract_json(result["output"])
        for i, iQuery in enumerate(indicator_list):
            indicator_list[i] = adjust_indicator_query(iQuery)
        result["indicator_list"] = indicator_list
        return result

if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    # 启动 AgentUniverse
    AgentUniverse().start(config_path='../../../../config/config.toml')

    # 获取智能体实例
    agent = AgentManager().get_instance_obj('indicator_nscode_select_agent')

    # 测试输入
    indicator_list = [
     {'库编码': None,
      '指标名称': '年化超额收益',
      '资产类型': '专户',
      '时间频率': '日',
      '回溯区间': '近1年',
      '开始时间': '2024-01-01',
      '截止时间': '2024-12-26',
      '指标代码': 'Ind0'},
     {'库编码': 'special_account.indicator.alpha_simple_factor_simu_mf_max_drawdown',
      '指标名称': '最大回撤',
      '资产类型': '专户',
      '时间频率': '日',
      '回溯区间': '近3月',
      '开始时间': '2024-01-01',
      '截止时间': '2024-12-26',
      '指标代码': 'Ind1'}]


    alternative_indicators ={'Ind0': [{'库编码': 'special_account.indicator.alpha_simple_factor_ex_annual_returns_yeb_simu_series',
               '指标名称': '高端-相对余额宝年化收益率超额值',
               '元信息': {'日频': None,
                          '周频': None,
                          '半年频': None,
                          '月频': None,
                          'level1_nscode': 'special_account.indicator.alpha_simple_factor_ex_annual_returns_yeb_simu_series',
                          '季频': None,
                          'onecode_factor_owner': '麦冬',
                          'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                          'level0_operator': 'ex_annual_returns_yeb_simu_series',
                          'uni_id': 'special_account.indicator.alpha_simple_factor_ex_annual_returns_yeb_simu_series',
                          'chi_name': '高端-相对余额宝年化收益率超额值',
                          '年频': None,
                          '二级维度': '收益指标',
                          '三级维度': '区间超额',
                          'grouped_chi_name': '超额:收益:相对基准',
                          'onecode_factor_description': '相对余额宝年化收益率超额值',
                          '业务域': '私募基金',
                          '一级维度': '绩效指标',
                          'onecode(C端、有流量)': "['SAI000686', 'SAI000708']",
                          'fap_asset_type': '专户'}},
              {'库编码': 'fund.private_fund.indicator.alpha_simple_factor_ex_annual_returns_000300_simu_series',
               '指标名称': '年化超额（相对沪深300）',
               '元信息': {'日频': None,
                          '周频': None,
                          '半年频': None,
                          '月频': None,
                          'level1_nscode': 'fund.private_fund.indicator.alpha_simple_factor_ex_annual_returns_000300_simu_series',
                          '季频': None,
                          'onecode_factor_owner': '岩见',
                          'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                          'level0_operator': 'ex_annual_returns_simu_series',
                          'uni_id': 'fund.private_fund.indicator.alpha_simple_factor_ex_annual_returns_000300_simu_series',
                          'chi_name': '年化超额（相对沪深300）',
                          '年频': None,
                          '二级维度': '收益指标',
                          '三级维度': '区间超额',
                          'grouped_chi_name': '超额:年化超额:相对基准',
                          'onecode_factor_description': '相对沪深300的年化超额',
                          '业务域': '私募基金',
                          '一级维度': '绩效指标',
                          'onecode(C端、有流量)': "['FPF000027', 'FPF000029', 'FPF000028']",
                          'fap_asset_type': '私募基金'}},
              {'库编码': 'special_account.indicator.alpha_simple_factor_ex_return_000905_simu_series',
               '指标名称': 'X度超额收益（相对中证500）',
               '元信息': {'日频': None,
                          '周频': None,
                          '半年频': None,
                          '月频': None,
                          'level1_nscode': 'special_account.indicator.alpha_simple_factor_ex_return_000905_simu_series',
                          '季频': None,
                          'onecode_factor_owner': '岩见',
                          'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                          'level0_operator': 'period_ex_return_simu_series',
                          'uni_id': 'special_account.indicator.alpha_simple_factor_ex_return_000905_simu_series',
                          'chi_name': 'X度超额收益（相对中证500）',
                          '年频': None,
                          '二级维度': '收益指标',
                          '三级维度': '区间超额',
                          'grouped_chi_name': '超额:收益:相对基准',
                          'onecode_factor_description': '相对中证500的年化超额收益',
                          '业务域': '私募基金',
                          '一级维度': '绩效指标',
                          'onecode(C端、有流量)': "['SAI000012', 'SAI000095', 'SAI000094', 'SAI000093', 'SAI000033', 'SAI000011', 'SAI000034', 'SAI000050', 'SAI000049']",
                          'fap_asset_type': '专户'}}],
     'Ind1': [{'库编码': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_risk',
               '指标名称': '高端-最大回撤',
               '元信息': {'日频': None,
                          '周频': None,
                          '半年频': None,
                          '月频': None,
                          'level1_nscode': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_risk',
                          '季频': None,
                          'onecode_factor_owner': '承溯',
                          'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                          'level0_operator': 'max_drawdown_simu_risk',
                          'uni_id': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_risk',
                          'chi_name': '高端-最大回撤',
                          '年频': None,
                          '二级维度': '风险指标',
                          '三级维度': '回撤',
                          'grouped_chi_name': '净值:最大回撤',
                          'onecode_factor_description': '高端-最大回撤',
                          '业务域': '私募基金',
                          '一级维度': '绩效指标',
                          'onecode(C端、有流量)': "['SAI000111', 'SAI000112']",
                          'fap_asset_type': '专户'}},
              {'库编码': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_series',
               '指标名称': '高端-高端周净值最大回撤',
               '元信息': {'日频': None,
                          '周频': None,
                          '半年频': None,
                          '月频': None,
                          'level1_nscode': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_series',
                          '季频': None,
                          'onecode_factor_owner': '启夏',
                          'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                          'level0_operator': 'max_drawdown_simu_series',
                          'uni_id': 'special_account.indicator.alpha_simple_factor_max_drawdown_simu_series',
                          'chi_name': '高端-高端周净值最大回撤',
                          '年频': None,
                          '二级维度': '风险指标',
                          '三级维度': '回撤',
                          'grouped_chi_name': '净值:最大回撤',
                          'onecode_factor_description': '高端-高端周净值最大回撤',
                          '业务域': '私募基金',
                          '一级维度': '绩效指标',
                          'onecode(C端、有流量)': "['SAI000682', 'SAI000101', 'SAI000102', 'SAI000103', 'SAI000110', 'SAI000714', 'SAI000559', 'SAI000464', 'SAI000683']",
                          'fap_asset_type': '专户'}},
              {
                  '库编码': 'fund.private_fund.indicator.alpha_simple_factor_ex_max_drawdown_repair_days_000300_simu_series',
                  '指标名称': '滚动超额最大回撤回补天数（相对沪深300）',
                  '元信息': {'日频': None,
                             '周频': None,
                             '半年频': None,
                             '月频': None,
                             'level1_nscode': 'fund.private_fund.indicator.alpha_simple_factor_ex_max_drawdown_repair_days_000300_simu_series',
                             '季频': None,
                             'onecode_factor_owner': '一宣',
                             'onecode_meta_domain_type': 'ALPHA_SIMPLE_FACTOR',
                             'level0_operator': 'ex_max_drawdown_repair_days_simu_series',
                             'uni_id': 'fund.private_fund.indicator.alpha_simple_factor_ex_max_drawdown_repair_days_000300_simu_series',
                             'chi_name': '滚动超额最大回撤回补天数（相对沪深300）',
                             '年频': None,
                             '二级维度': '风险指标',
                             '三级维度': '回撤修复',
                             'grouped_chi_name': '超额:最大回撤修复天数:相对基准',
                             'onecode_factor_description': '滚动超额最大回撤回补天数（相对沪深300）',
                             '业务域': '私募基金',
                             '一级维度': '绩效指标',
                             'onecode(C端、有流量)': "['FPF000007', 'FPF000011', 'FPF000008']",
                             'fap_asset_type': '私募基金'}}]}

    # 运行智能体
    res = agent.run(indicator_list=indicator_list, alternative_indicators=alternative_indicators, error_info='')
    LOGGER.info(res)

    # 打印输出
    LOGGER.info(f"原始指标列表: {indicator_list}")
    LOGGER.info(f"模型识别入参: {res.to_dict()['output']}")
    LOGGER.info(f"模型识别indicator_list: {res.to_dict()['indicator_list']}")


