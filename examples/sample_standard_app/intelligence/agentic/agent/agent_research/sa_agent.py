# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/11/30 16:20
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: sa_agent.py
import re
import json
import datetime as dt

import pandas as pd
from prettyprinter import pformat

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.plan.planner.planner import Planner
from agentuniverse.agent.plan.planner.planner_manager import PlannerManager
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from agentuniverse.agent.action.tool.tool_manager import ToolManager
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.action.knowledge.store.store_manager import StoreManager

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
            iEndDT = (pd.to_datetime(indicator_query["截止时间"]) if pd.notnull(
                indicator_query["截止时间"]) else dt.datetime.today())
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
        elif iKey == "产品池":
            adjusted_filter[iKey] = Defaults.get("产品池", "所有")
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
    groups = re.findall(p, s)
    json_list = []
    for ijson_str, _ in groups:
        try:
            ijson = json.loads(ijson_str)
        except:
            print(f"无法解析的 json: {ijson_str}")
        else:
            json_list.append(ijson)
    return json_list


class UserIntentParseAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_list', 'filter', 'indicator_algorithm', 'indicator_modification',
                'indicator_adding', 'filter_modification', 'indicator_algorithm_modification']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['indicator_list'] = input_object.get_data('indicator_list')
        if planner_input['indicator_list']:
            planner_input['indicator_list'] = f"当前的指标列表是: \n{planner_input['indicator_list']}"
            planner_input["indicator_adding"] = "* 新增指标: 增加当前给定的指标列表中没有的指标"
            planner_input[
                "indicator_modification"] = "* 指标口径修改: 对当前给定的指标列表中的指标口径分项进行修改，这些是常见的用户输入：将所有指标的开始时间修改为 2024-10-31, 将年化收益的资产范围限制在私募基金里, 某个指标使用库里的指标"
            planner_input[
                "filter_modification"] = "* 筛选条件修改：对当前给定的筛选条件进行修改，这些是常见的用户输入：将产品筛选的范围限定在偏股池里，筛选条件修改为年化收益大于 30% 并且最大回撤不高于 10%"
            planner_input[
                "indicator_algorithm_modification"] = "* 指标算法修改: 对当前给定的衍生指标计算算法进行修改，这些是常见的用户输入：夏普比率计算中的无风险利率假设为 2%"
        else:
            planner_input["indicator_list"] = ""
            planner_input["indicator_modification"] = ""
            planner_input["indicator_adding"] = ""
            planner_input["filter_modification"] = ""
            planner_input["indicator_algorithm_modification"] = ""
        planner_input['filter'] = input_object.get_data('filter')
        if planner_input['filter']:
            planner_input['filter'] = f"当前的筛选条件是: \n{planner_input['filter']}"
        else:
            planner_input["filter"] = ""
        indicator_algorithm = input_object.get_data('indicator_algorithm')
        if indicator_algorithm:
            planner_input[
                'indicator_algorithm'] = f"当前的衍生指标列表是: \n{[iIndicator['指标名称'] for iIndicator in indicator_algorithm.values()]}"
        else:
            planner_input["indicator_algorithm"] = ""
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


class QuantConsultingAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'quant_external_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        if not input_object.get_data('quant_external_info'):
            search_tool = ToolManager().get_instance_obj("google_search_tool")
            retrieved_docs = search_tool.run(input=planner_input['input'])
            planner_input["quant_external_info"] = retrieved_docs
        else:
            planner_input["quant_external_info"] = input_object.get_data('quant_external_info')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


class IndicatorExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


class IndicatorQuerySAAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['requirement', 'indicator_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        if not input_object.get_data('indicator_list'):
            knowledge = KnowledgeManager().get_instance_obj("NL2Indicator_knowledge")
            retrieved_docs = knowledge.query_knowledge(query_str=input_object.get_data('requirement'),
                                                       similarity_top_k=5)
            retrieved_texts = [json.dumps({
                "库编码": doc.id,
                "指标名称": doc.metadata["name"],
                "指标描述": doc.metadata["onecode_factor_description"],
            }, ensure_ascii=False) for doc in retrieved_docs]
            planner_input["indicator_list"] = ', '.join(retrieved_texts)
        else:
            planner_input['indicator_list'] = input_object.get_data('indicator_list')
        planner_input['requirement'] = input_object.get_data('requirement')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        indicator_list = extract_json(result["output"])
        for i, iQuery in enumerate(indicator_list):
            indicator_list[i] = adjust_indicator_query(iQuery)
        result["indicator_list"] = indicator_list
        return result


class IndicatorModificationAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_list', "alternative_indicators"]

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
            planner_input['indicator_list'] = "\n".join(adjusted_indicator_list)
            planner_input['alternative_indicators'] = ""
        else:
            raise Exception("IndicatorModificationAgent: 指标列表不能为空!")
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        indicator_list = extract_json(result["output"])
        for i, iQuery in enumerate(indicator_list):
            indicator_list[i] = adjust_indicator_query(iQuery)
        result["indicator_list"] = indicator_list
        return result


class IndicatorAddingAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_list', 'lib_indicator_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['indicator_list'] = input_object.get_data('indicator_list')
        if planner_input['indicator_list']:
            indicator_list = [json.dumps(iIndicator, ensure_ascii=False) for iIndicator in
                              planner_input['indicator_list']]
            planner_input['indicator_list'] = f"当前给定的指标列表是: \n{indicator_list}"
        planner_input['input'] = input_object.get_data('input')
        if not input_object.get_data('lib_indicator_list'):
            knowledge = KnowledgeManager().get_instance_obj("NL2Indicator_knowledge")
            retrieved_docs = knowledge.query_knowledge(query_str=input_object.get_data('requirement'),
                                                       similarity_top_k=5)
            retrieved_texts = [json.dumps({
                "库编码": doc.id,
                "指标名称": doc.metadata["name"],
                "指标描述": doc.metadata["onecode_factor_description"],
            }, ensure_ascii=False) for doc in retrieved_docs]
            planner_input["lib_indicator_list"] = ', '.join(retrieved_texts)
        else:
            planner_input['lib_indicator_list'] = input_object.get_data('indicator_list')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        if result["output"] == "无新增指标":
            result["indicator_list"] = []
        else:
            indicator_list = extract_json(result["output"])
            for i, iQuery in enumerate(indicator_list):
                indicator_list[i] = adjust_indicator_query(iQuery)
            result["indicator_list"] = indicator_list
        return result


class IndicatorConsultingAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_external_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        if not input_object.get_data('indicator_external_info'):
            search_tool = ToolManager().get_instance_obj("google_search_tool")
            retrieved_docs = search_tool.run(input=planner_input['input'])
            planner_input["indicator_external_info"] = retrieved_docs
        else:
            planner_input["indicator_external_info"] = input_object.get_data('indicator_external_info')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        indicator_knowledge = KnowledgeManager().get_instance_obj("NL2Indicator_knowledge")
        Docs = indicator_knowledge.query_knowledge(query_str=planner_result["output"], similarity_top_k=5)
        planner_result["lib_indicator_list"] = [
            {"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in Docs]
        return planner_result


class IndicatorCalculatorSAAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['indicator_name', 'indicator_info', 'indicator_args', 'indicator_external_info']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        if not input_object.get_data('indicator_external_info'):
            search_tool = ToolManager().get_instance_obj("google_search_tool")
            retrieved_docs = search_tool.run(input=input_object.get_data('indicator_name') + "的算法")
            planner_input["indicator_external_info"] = retrieved_docs
        else:
            planner_input["indicator_external_info"] = input_object.get_data('indicator_external_info')
        planner_input['indicator_name'] = input_object.get_data('indicator_name')
        planner_input['indicator_info'] = input_object.get_data('indicator_info')
        planner_input['indicator_args'] = json.dumps(input_object.get_data('indicator_args'), ensure_ascii=False)
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


class IndicatorAlgorithmModificationAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_name', 'indicator_args', 'indicator_algorithm']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['indicator_algorithm'] = input_object.get_data('indicator_algorithm')
        planner_input['indicator_name'] = input_object.get_data('indicator_name')
        planner_input['indicator_args'] = json.dumps(input_object.get_data('indicator_args'), ensure_ascii=False)
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


class FilterSAAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['requirement', 'indicator_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['requirement'] = input_object.get_data('requirement')
        planner_input['indicator_list'] = str(input_object.get_data('indicator_list'))
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["filter"] = extract_json(result["output"])
        return result


class FilterModificationAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'indicator_list', 'filter']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        indicator_list = [json.dumps(iIndicator, ensure_ascii=False) for iIndicator in
                          input_object.get_data('indicator_list')]
        planner_input['indicator_list'] = f"\n{indicator_list}"
        filter = json.dumps(input_object.get_data('filter'), ensure_ascii=False)
        planner_input['filter'] = f"当前的筛选条件是: \n{filter}"
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["filter"] = extract_json(result["output"])
        return result


# 指标查询
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
    store = StoreManager().get_instance_obj('indicator_zsearch_store')
    knowledge = KnowledgeManager().get_instance_obj("NL2Indicator_knowledge")

    ## 知识注入
    # knowledge.insert_knowledge(source_path="../../knowledge/raw_knowledge_file/indicator_info.xlsx")

    # 指标查询
    # requirement = "我想提取专户近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    requirement = input("你好，我是一个指标查询智能助手, 请告诉我你的指标查询需求:")
    rsp = agent.run(requirement=requirement, indicator_list="")
    rsp = rsp.to_dict()
    indicator_list = rsp["indicator_list"]

    alternative_indicators = {}
    for i, iIndicator in enumerate(indicator_list):
        iIndicator["指标代码"] = f"Ind{i}"
        iAlternativeIndicators = knowledge.query_knowledge(query_str=iIndicator["指标名称"], similarity_top_k=3)
        alternative_indicators[iIndicator["指标代码"]] = [
            {"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in
            iAlternativeIndicators]
    print(f"requirement={requirement}, indicator_list={pformat(indicator_list)}")
    print(f"alternative_indicators={pformat(alternative_indicators)}")
    print("===")

# 指标抽取
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_extract_agent')

    # 指标抽取
    # requirement = "我想提取专户近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    requirement = input("你好，我是一个指标查询智能助手, 请告诉我你的指标查询需求:")
    rsp = agent.run(input=requirement)
    rsp = rsp.to_dict()
    indicator_list = rsp["output"]

    print(f"requirement={requirement}, indicator_list={pformat(indicator_list)}")
    print("===")

# 指标修改
if __name__ == "__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_modification_agent')

    indicator_list = [
        {'指标代码': 'Ind0', '库编码': None, '资产类型': '公募基金', '指标名称': '年化超额收益', '时间频率': '日',
         '回溯区间': '近1年', '开始时间': None, '截止时间': None},
        {'指标代码': 'Ind1', '库编码': None, '资产类型': '公募基金', '指标名称': '正收益概率', '时间频率': '日',
         '回溯区间': '近3月', '开始时间': None, '截止时间': None}
    ]
    print(f"当前的指标列表: {pformat(indicator_list)}")
    user_input = input(f"请告诉我你指标口径修改的说明:")
    rsp = agent.run(input=user_input, indicator_list=indicator_list)
    rsp = rsp.to_dict()
    adjusted_indicator_list = rsp["indicator_list"]
    print(
        f"user_input={user_input}",
        f"adjusted_indicator_list={pformat(adjusted_indicator_list)}",
        sep="\n"
    )

    print("===")

# 新增指标
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_adding_agent')

    indicator_list = [
        {'指标代码': 'Ind0', '资产类型': '公募基金', '库编码': None, '指标名称': '年化超额收益', '时间频率': '日',
         '回溯区间': '近1年', '开始时间': None, '截止时间': None},
        {'指标代码': 'Ind1', '资产类型': '公募基金', '库编码': None, '指标名称': '正收益概率', '时间频率': '日',
         '回溯区间': '近3月', '开始时间': None, '截止时间': None}
    ]
    lib_indicator_list = ["年化超额收益", "最大回撤"]
    print(f"当前的指标列表: {pformat(indicator_list)}")
    user_input = input(f"请告诉我你指标修改的说明:")
    rsp = agent.run(input=user_input, indicator_list=indicator_list, lib_indicator_list=lib_indicator_list)
    rsp = rsp.to_dict()
    added_indicator_list = rsp["indicator_list"]
    for i, iIndicator in enumerate(added_indicator_list):
        iIndicator = set_indicator_default(iIndicator, indicator_list)
        iIndicator["指标代码"] = f"Ind{len(indicator_list) + i}"
        indicator_list.append(iIndicator)
    print(
        f"user_input={user_input}",
        f"added_indicator_list={pformat(added_indicator_list)}",
        sep="\n"
    )

    print("===")

# 指标咨询
if __name__ == "__main__":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_consulting_agent')

    user_input = input(f"你好，请告诉我你想要咨询的指标:")
    rsp = agent.run(input=user_input, indicator_external_info="")
    rsp = rsp.to_dict()
    ai_output = rsp["output"]
    print(
        f"user_input={user_input}",
        f"ai_output={pformat(ai_output)}",
        sep="\n"
    )
    print(f"相关的库指标: {pformat(rsp['lib_indicator_list'])}")
    print("===")

# 标的筛选
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('filter_sa_agent')

    # 标的筛选
    indicator_list = [
        {'指标代码': 'Ind0', '库编码': None, '指标名称': '年化超额收益', '时间频率': '日', '回溯区间': '近1年',
         '开始时间': None, '截止时间': None},
        {'指标代码': 'Ind1', '库编码': None, '指标名称': '正收益概率', '时间频率': '日', '回溯区间': '近3个月',
         '开始时间': None, '截止时间': None}
    ]
    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    requirement = input("你好，我是一个标的筛选智能助手, 请告诉我你的标的筛选需求:")
    rsp = agent.run(requirement=requirement, indicator_list=indicator_list)
    rsp = rsp.to_dict()
    sec_filter = rsp["filter"][0]
    print(f"requirement={requirement}", f"indicator_list={indicator_list}", f"filter={sec_filter}", sep="\n")
    all_filled = False
    while not all_filled:
        adjusted_filter, all_filled = {}, True
        for jKey, jVal in sec_filter.items():
            if jVal is None:
                adjusted_filter[jKey] = input(f"请确认指标筛选的分项口径 {jKey}:")
                if not adjusted_filter[jKey]:
                    adjusted_filter[jKey] = None
                    all_filled = False
            else:
                adjusted_filter[jKey] = jVal
        sec_filter = adjusted_filter.copy()
    print(f"requirement={requirement}", f"indicator_list={indicator_list}", f"adjusted_filter={adjusted_filter}",
          sep="\n")

    print("===")

# 筛选修改
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('filter_modification_agent')

    indicator_list = [
        {'指标代码': 'Ind0', '库编码': None, '指标名称': '年化超额收益', '时间频率': '日', '回溯区间': '近1年',
         '开始时间': None, '截止时间': None},
        {'指标代码': 'Ind1', '库编码': None, '指标名称': '正收益概率', '时间频率': '日', '回溯区间': '近3月',
         '开始时间': None, '截止时间': None}
    ]
    sec_filter = {
        "资产类型": "公募基金",
        "产品池": "所有",
        "条件表达式": "$Ind1$ > 0.5 and $Ind2$ < 0.08",
        "开始时间": "2024-10-31",
        "截止时间": "2024-10-31"
    }
    print(f"当前的指标列表: {pformat(indicator_list)}")
    print(f"当前的筛选条件: {pformat(sec_filter)}")
    user_input = input(f"请告诉我你筛选条件修改的说明:")
    rsp = agent.run(input=user_input, indicator_list=indicator_list, filter=sec_filter)
    rsp = rsp.to_dict()
    adjusted_sec_filter = rsp["filter"][0]
    print(
        f"user_input={user_input}",
        f"adjusted_sec_filter={pformat(adjusted_sec_filter)}",
        sep="\n"
    )

    print("===")

# 指标计算
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')

    # 指标计算
    indicator_args = {'指标名称': '最大回撤', '时间频率': '日', '回溯区间': '近1年', '开始时间': '2024-10-01',
                      '截止时间': '2024-10-31'}
    indicator_name = indicator_args.get("指标名称")

    indicator_info = input(f"你好，我是一个指标计算智能助手, 请告诉我关于指标 '{indicator_name}' 的描述:")
    rsp = agent.run(indicator_name=indicator_name, indicator_args=indicator_args, indicator_info=indicator_info,
                    indicator_external_info="")
    rsp = rsp.to_dict()
    indicator_algorithm = rsp["output"]
    print(
        f"indicator_name={indicator_name}",
        f"indicator_args={indicator_args}",
        f"indicator_info={indicator_info}",
        f"indicator_algorithm={indicator_algorithm}",
        sep="\n")

    print("===")

# 指标算法修改
if __name__ == "__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('indicator_algorithm_modification_agent')

    # 指标计算
    indicator_args = {'指标名称': '最大回撤', '时间频率': '日', '回溯区间': '近1年', '开始时间': '2024-10-01',
                      '截止时间': '2024-10-31'}
    indicator_name = indicator_args.get("指标名称")
    indicator_algorithm = '为了计算“最大回撤”指标，我们需要遵循以下步骤：\n\n### 数据依赖\n1. **账户每日价值数据**：需要获取从2023年10月1日到2024年10月31日期间的账户每日价值数据。这些数据用于计算每日的账户价值变化。\n\n### 计算算法步骤\n\n1. **数据准备**：\n   - 收集从2023年10月1日到2024年10月31日期间的账户每日价值数据。\n   - 确保数据的完整性和准确性，处理任何缺失值或异常值。\n\n2. **初始化变量**：\n   - `max_drawdown`：初始化为0，用于存储最大回撤值。\n   - `peak_value`：初始化为0，用于存储当前的最高账户价值。\n\n3. **遍历每日账户价值数据**：\n   - 对于每一天的账户价值`current_value`：\n     - 如果`current_value`大于`peak_value`，则更新`peak_value`为`current_value`。\n     - 计算当前回撤：`drawdown = 1 - (current_value / peak_value)`.\n     - 如果`drawdown`大于`max_drawdown`，则更新`max_drawdown`为`drawdown`。\n\n4. **计算最大回撤率**：\n   - 将`max_drawdown`转换为百分比形式：`max_drawdown_percentage = max_drawdown * 100`.\n\n5. **输出结果**：\n   - 输出最大回撤率`max_drawdown_percentage`。\n\n### 注意事项\n- 确保在计算过程中，`peak_value`始终是当前日期之前的最高账户价值。\n- 处理数据时，注意时间序列的顺序，确保从早到晚的顺序遍历。\n- 在计算过程中，避免除以零的情况，确保`peak_value`不为零。\n\n通过上述步骤，可以准确计算出指定时间范围内的最大回撤率。'

    user_input = input(f"你好，请告诉我关于指标 '{indicator_name}' 的算法修改意见:")
    rsp = agent.run(input=user_input, indicator_name=indicator_name, indicator_args=indicator_args,
                    indicator_algorithm=indicator_algorithm)
    rsp = rsp.to_dict()
    indicator_algorithm = rsp["output"]
    print(
        f"indicator_name={indicator_name}",
        f"indicator_args={pformat(indicator_args)}",
        f"indicator_algorithm={indicator_algorithm}",
        sep="\n")

    print("===")

# 意图识别
if __name__ == "__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('user_intent_parse_agent')

    # indicator_list = [
    #     {'指标代码': 'Ind0', '库编码': None, '指标名称': '年化超额收益', '时间频率': '日', '回溯区间': '近1年', '开始时间': None, '截止时间': None},
    #     {'指标代码': 'Ind1', '库编码': None, '指标名称': '正收益概率', '时间频率': '日', '回溯区间': '近3个月', '开始时间': None, '截止时间': None}
    # ]
    indicator_list = []
    sec_filter = {}
    indicator_algorithm = {}

    user_input = input(f"你好，说点什么吧:")
    rsp = agent.run(
        input=user_input,
        filter=sec_filter,
        indicator_list=indicator_list,
        indicator_algorithm=indicator_algorithm,
        indicator_modification="",
        filter_modification="",
        indicator_algorithm_modification=""
    )
    rsp = rsp.to_dict()
    user_intent = rsp["output"]
    print(
        f"indicator_list={pformat(indicator_list)}",
        f"sec_filter={pformat(sec_filter)}",
        f"user_input={user_input}",
        f"user_intent={user_intent}",
        sep="\n")

    print("===")

# 量化知识咨询
if __name__ == "__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('quant_consulting_agent')

    user_input = input(f"你好，请告诉我你想要咨询的问题:")
    rsp = agent.run(input=user_input, quant_external_info="")
    rsp = rsp.to_dict()
    ai_output = rsp["output"]
    print(
        f"user_input={user_input}",
        f"ai_output={pformat(ai_output)}",
        sep="\n"
    )

    print("===")
