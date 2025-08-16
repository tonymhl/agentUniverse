# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/12/27 12:07
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: smart_selector_agent.py
import numpy as np
import pandas as pd
from prettyprinter import pformat

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from agentuniverse.base.util.logging.logging_util import LOGGER
from sample_standard_app.app.core.agent.asset_research.sa_agent import validate_indicator_query, IndicatorQueryPrompt, set_indicator_default, set_filter_default


def append_list(l, e):
    l.append(e)
    return e

def get_indicator_query_rslt(rsp):
    indicator_list = rsp.to_dict()["indicator_list"]
    LOGGER.info(f"indicator_list={indicator_list}")
    adjusted_query = []
    for i, iQuery in enumerate(indicator_list):
        for jKey, jVal in list(iQuery.items()):
            ijPrompt = IndicatorQueryPrompt[jKey]
            ijPrompt = (f"({ijPrompt})" if ijPrompt else "")
            if jVal is None:
                ijInputPrompt = f"请输入指标 '{iQuery['指标名称']}' 的分项口径 '{jKey}'{ijPrompt.format(current=str(jVal))}: "
            else:
                ijInputPrompt = f"请确认指标 '{iQuery['指标名称']}' 的分项口径 '{jKey}'{ijPrompt.format(current=str(jVal))}: "
            iNewVal = input(ijInputPrompt).strip()
            if (jVal is not None) and (not iNewVal): continue
            if iNewVal: iQuery[jKey] = iNewVal
            if iQuery[jKey] is None:
                iError = {jKey: f"分项口径 '{jKey}' 不能为空"}
            else:
                iError, iQuery = validate_indicator_query(iQuery, keys=[jKey])
            while iError:
                ijInputPrompt = f"输入错误: {iError[jKey]}, \n请重新输入指标 '{iQuery['指标名称']}' 的分项口径 '{jKey}'{ijPrompt.format(current=str(iQuery[jKey]))}: "
                iNewVal = input(ijInputPrompt).strip()
                if iNewVal: iQuery[jKey] = iNewVal
                if iQuery[jKey] is None:
                    iError = {jKey: f"分项口径 '{jKey}' 不能为空"}
                else:
                    iError, iQuery = validate_indicator_query(iQuery, keys=[jKey])
        iQuery["指标代码"] = f"Ind{i}"
        adjusted_query.append(iQuery)
    indicator_list = adjusted_query
    LOGGER.info(f"indicator_list={indicator_list}")
    return indicator_list

def get_filter_rslt(rsp):
    rsp = rsp.to_dict()
    sec_filter = rsp["filter"][0]
    LOGGER.info(f"filter={sec_filter}")
    all_filled = False
    while not all_filled:
        adjusted_filter, all_filled = {}, True
        for jKey, jVal in sec_filter.items():
            if jVal is None:
                adjusted_filter[jKey] = input(f"请确认指标筛选的分项口径 '{jKey}': ")
                if not adjusted_filter[jKey]:
                    adjusted_filter[jKey] = None
                    all_filled = False
            else:
                adjusted_filter[jKey] = jVal
        sec_filter = adjusted_filter.copy()
    LOGGER.info(f"filter={adjusted_filter}")
    return sec_filter

def get_indicator_calculator_rslt(indicator_query, agent):
    indicator_args = indicator_query.copy()
    indicator_id = indicator_args.pop("指标代码", None)
    indicator_args.pop("库编码", None)
    indicator_name = indicator_args.get("指标名称")

    indicator_info = input(f"请告诉我关于指标 '{indicator_name}' 的描述和要求:\n>>>")
    rsp = agent.run(indicator_name=indicator_name, indicator_args=str(indicator_args), indicator_info=indicator_info, indicator_external_info="")
    rsp = rsp.to_dict()
    return {"指标代码": indicator_id, "指标名称": indicator_name, "用户描述": indicator_info, "指标算法": rsp["output"]}

def gen_indicator_calculator_rslt(indicator_query, user_info, agent):
    indicator_args = indicator_query.copy()
    indicator_id = indicator_args.pop("指标代码", None)
    indicator_args.pop("库编码", None)
    indicator_name = indicator_args.get("指标名称")

    rsp = agent.run(indicator_name=indicator_name, indicator_args=indicator_args, indicator_info=user_info, indicator_external_info="")
    rsp = rsp.to_dict()
    return {"指标代码": indicator_id, "指标名称": indicator_name, "用户描述": user_info, "指标算法": rsp["output"]}

def get_indicator_missing_key(indicator_list):
    missing_keys = {}
    for iIndicator in indicator_list:
        for iKey, iVal in iIndicator.items():
            if pd.isnull(iVal) and (iKey!="库编码"):
                missing_keys.setdefault(iIndicator["指标名称"], []).append(iKey)
    return missing_keys

def get_alternative_indicator(indicator, knowledge, alternative_num):
    MetaData = {}
    if indicator["资产类型"]:
        MetaData["fap_asset_type"] = indicator["资产类型"]
    iAlternativeIndicators = knowledge.query_knowledge(query_str=indicator["指标名称"], similarity_top_k=alternative_num)
    return [{"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in iAlternativeIndicators]


class SmartSelectorAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input']

    def output_keys(self) -> list[str]:
        return ["output", "output_list", "status", "ext_info"]

    def _handle_free_answer(self, user_input):
        free_answer_agent = AgentManager().get_instance_obj('free_answer_agent')

        rsp = free_answer_agent.run(input=user_input)
        rsp = rsp.to_dict()
        return {"output": rsp["output"]}

    def _handle_quant_consulting(self, user_input):
        quant_consulting_agent = AgentManager().get_instance_obj('quant_consulting_agent')
        rsp = quant_consulting_agent.run(input=user_input, quant_external_info="")
        rsp = rsp.to_dict()
        return {"output": rsp["output"]}

    def _handle_indicator_consulting(self, user_input):
        indicator_consulting_agent = AgentManager().get_instance_obj('indicator_consulting_agent')
        rsp = indicator_consulting_agent.run(input=user_input, indicator_external_info="")
        rsp = rsp.to_dict()
        return {"output": rsp["output"], "lib_indicator_list": rsp['lib_indicator_list']}

    def _handle_indicator_modification(self, user_input):
        indicator_modification_agent = AgentManager().get_instance_obj('indicator_modification_agent')
        indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
        indicator_list = self._Memeory["indicator_list"]
        indicator_dict = self._Memeory["indicator_dict"]
        indicator_algorithm = self._Memeory["indicator_algorithm"]
        alternative_indicators = self._Memeory["alternative_indicators"]

        rsp = indicator_modification_agent.run(input=user_input, indicator_list=indicator_list, alternative_indicators=alternative_indicators)
        rsp = rsp.to_dict()
        adjusted_indicator_list = rsp["indicator_list"]
        output = {"adjusted_indicator_list": adjusted_indicator_list}

        adjusted_indicator_algorithm = {}
        for i, iIndicator in enumerate(adjusted_indicator_list):
            if (iIndicator != indicator_dict[iIndicator["指标代码"]]) and pd.isnull(iIndicator["库编码"]):
                iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                adjusted_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
            indicator_dict[iIndicator["指标代码"]] = iIndicator
        self._Memeory["indicator_list"] = adjusted_indicator_list
        if adjusted_indicator_algorithm:
            output["adjusted_indicator_algorithm"] = adjusted_indicator_algorithm
            indicator_algorithm.update(adjusted_indicator_algorithm)
        return output

    def _handle_indicator_adding(self, user_input):
        indicator_adding_agent = AgentManager().get_instance_obj('indicator_adding_agent')
        indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
        indicator_knowledge = KnowledgeManager().get_instance_obj("indicator_knowledge")
        indicator_list = self._Memeory["indicator_list"]
        indicator_dict = self._Memeory["indicator_dict"]
        indicator_algorithm = self._Memeory["indicator_algorithm"]
        alternative_indicators = self._Memeory["alternative_indicators"]
        alternative_num = 3

        rsp = indicator_adding_agent.run(input=user_input, indicator_list=indicator_list, lib_indicator_list="")
        rsp = rsp.to_dict()
        added_indicator_list = rsp["indicator_list"]
        added_indicator_algorithm = {}
        for i, iIndicator in enumerate(added_indicator_list):
            iIndicator = set_indicator_default(iIndicator, indicator_list)
            iIndicator["指标代码"] = f"Ind{len(indicator_list) + i}"
            indicator_list.append(iIndicator)
            indicator_dict[iIndicator["指标代码"]] = iIndicator
            if pd.isnull(iIndicator["库编码"]):
                iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                added_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
            alternative_indicators[iIndicator["指标代码"]] = get_alternative_indicator(iIndicator, indicator_knowledge, alternative_num=alternative_num)
        indicator_algorithm.update(added_indicator_algorithm)
        return {"added_indicator_algorithm": added_indicator_algorithm, "added_indicator_list": added_indicator_list}

    def _handle_filter_modification(self, user_input):
        filter_modification_agent = AgentManager().get_instance_obj('filter_modification_agent')
        indicator_list = self._Memeory["indicator_list"]
        sec_filter = self._Memeory["sec_filter"]

        rsp = filter_modification_agent.run(input=user_input, indicator_list=indicator_list, filter=sec_filter)
        rsp = rsp.to_dict()
        sec_filter = rsp["filter"][0]
        self._Memeory["sec_filter"] = sec_filter
        return {"sec_filter": sec_filter}

    def _handle_indicator_algorithm_modification(self, user_input):
        indicator_algorithm_modification_agent = AgentManager().get_instance_obj('indicator_algorithm_modification_agent')
        indicator_list = self._Memeory["indicator_list"]
        indicator_algorithm = self._Memeory["indicator_algorithm"]

        adjusted_indicator_algorithm =[]
        for iInd, iIndicator in indicator_algorithm.items():
            if iIndicator["指标名称"] not in user_input: continue
            for iQuery in indicator_list:
                if iQuery["指标名称"] == iIndicator["指标名称"]:
                    iIndicatorArgs = iQuery.copy()
                    break
            rsp = indicator_algorithm_modification_agent.run(input=user_input, indicator_name=iIndicator["指标名称"], indicator_args=iIndicatorArgs, indicator_algorithm=iIndicator)
            rsp = rsp.to_dict()
            iIndicator["指标算法"] = rsp["output"]
            adjusted_indicator_algorithm.append(iIndicator)
        return {"adjusted_indicator_algorithm": adjusted_indicator_algorithm}

    def _handle_quant_requirement(self, user_input):
        OutputList = []
        schedule_agent = AgentManager().get_instance_obj('schedule_agent')
        indicator_query_sa_agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
        filter_sa_agent = AgentManager().get_instance_obj('filter_sa_agent')
        indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
        indicator_knowledge = KnowledgeManager().get_instance_obj("indicator_knowledge")
        alternative_indicators = self._Memeory["alternative_indicators"]
        alternative_num = 3

        # 任务编排
        print(append_list(OutputList,"======================== 任务编排 ========================"))
        rsp = schedule_agent.run(requirement=user_input)
        task_list = rsp.to_dict()["output"]
        if (task_list == "非法需求"):
            print(append_list(OutputList, "您输入的并非有效的量化分析需求，请修改后重新输入"))
            task_list = []
        else:
            task_list = [iTask.strip() for iTask in task_list.split(">")]
        print(append_list(OutputList,f"任务编排: {task_list}"))
        # 任务系分
        indicator_algorithm = {}
        indicator_dict = {}
        while task_list:
            iTask = task_list.pop(0)
            if iTask == "指标提取":
                print(append_list(OutputList, f"======================== 系分生成: {iTask} ========================"))
                rsp = indicator_query_sa_agent.run(requirement=user_input, indicator_list="")
                indicator_list = rsp.to_dict()["indicator_list"]
                print(append_list(OutputList, "指标列表: "))
                for i, iIndicator in enumerate(indicator_list):
                    iIndicator = set_indicator_default(iIndicator)
                    iIndicator["指标代码"] = f"Ind{i}"
                    indicator_list[i] = iIndicator
                    indicator_dict[iIndicator["指标代码"]] = iIndicator
                    alternative_indicators[iIndicator["指标代码"]] = get_alternative_indicator(iIndicator, indicator_knowledge, alternative_num=alternative_num)
                    print(append_list(OutputList, f"{pformat(iIndicator)}"))
                    print(append_list(OutputList, f"候选指标: {pformat(alternative_indicators[iIndicator['指标代码']])}"))
            elif iTask == "标的筛选":
                if not all((pd.notnull(iIndicator.get("库编码", None)) or (iIndicator["指标代码"] in indicator_algorithm)) for iIndicator in indicator_list):
                    task_list = ["指标计算", iTask] + task_list
                    continue
                print(append_list(OutputList, f"======================== 系分生成: {iTask} ========================"))
                rsp = filter_sa_agent.run(requirement=user_input, indicator_list=indicator_list)
                rsp = rsp.to_dict()
                sec_filter = rsp["filter"][0]
                sec_filter = set_filter_default(sec_filter, indicator_list=indicator_list)
                print(append_list(OutputList, f"筛选条件: {pformat(sec_filter)}"))
            elif iTask == "指标计算":
                if all((pd.notnull(iIndicator.get("库编码", None)) or (iIndicator["指标代码"] in indicator_algorithm)) for iIndicator in indicator_list):
                    print(append_list(OutputList, "所有的指标已经在指标库中或者已经生成了算法, 不需要衍生计算!"))
                    continue
                print(append_list(OutputList, f"======================== 系分生成: {iTask} ========================"))
                for i, iIndicator in enumerate(indicator_list):
                    if pd.notnull(iIndicator["库编码"]): continue
                    iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                    indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                print(append_list(OutputList, f"衍生指标算法: {pformat(indicator_algorithm)}"))
            else:
                print(append_list(OutputList, f"======================== 系分生成: {iTask} ========================"))
                print(append_list(OutputList, f"不支持的任务: {iTask}"))
        self._Memeory["indicator_list"] = indicator_list
        self._Memeory["indicator_dict"] = indicator_dict
        self._Memeory["sec_filter"] = sec_filter
        self._Memeory["indicator_algorithm"] = indicator_algorithm
        return OutputList, {"task_list": task_list}

    def execute(self, input_object: InputObject, agent_input: dict):
        OutputList, ExtInfo = [], {}
        intent_agent = AgentManager().get_instance_obj('user_intent_parse_agent')

        if not hasattr(self, "_Memeory"):
            self._Memeory = dict(
                task_list = [],
                indicator_list = [],
                alternative_indicators = {},
                indicator_dict = {},
                indicator_algorithm = {},
                sec_filter = {},
                all_filled = False
            )

        user_input = agent_input["input"]
        if (user_input.lower()=="yes") and self._Memeory["indicator_list"] and self._Memeory["all_filled"]:
            print(append_list(OutputList, f"系分生成完毕, 下面生成执行代码"))
            raise NotImplementedError

        # 意图识别
        rsp = intent_agent.run(
            input=user_input,
            filter=self._Memeory["sec_filter"],
            indicator_list=self._Memeory["indicator_list"],
            indicator_algorithm=self._Memeory["indicator_algorithm"],
            indicator_modification="",
            indicator_adding="",
            filter_modification="",
            indicator_algorithm_modification=""
        )
        rsp = rsp.to_dict()
        intent_list = [intent.strip() for intent in rsp["output"].split(",")]
        if ("筛选条件修改" in intent_list) and ("新增指标" not in intent_list):
            intent_list.insert(intent_list.index("筛选条件修改"), "新增指标")
        ExtInfo["intent_list"] = intent_list
        print(append_list(OutputList, f"用户意图: {intent_list}"))
        for user_intent in intent_list:
            if user_intent == "量化知识咨询":
                output = self._handle_quant_consulting(user_input)
                print(append_list(OutputList, output["output"]))
            elif user_intent == "指标信息咨询":
                output = self._handle_indicator_consulting(user_input)
                ExtInfo["lib_indicator_list"] = output['lib_indicator_list']
                print(append_list(OutputList, pformat(output["output"])))
                print(append_list(OutputList, f"相关的库指标: {pformat(output['lib_indicator_list'])}"))
            elif user_intent == "指标口径修改":
                output = self._handle_indicator_modification(user_input)
                ExtInfo["adjusted_indicator_list"] = output['adjusted_indicator_list']
                ExtInfo["adjusted_indicator_algorithm"] = output['adjusted_indicator_algorithm']
                print(append_list(OutputList, f"调整后的指标列表: {pformat(output['adjusted_indicator_list'])}"))
                print(append_list(OutputList, f"调整后的衍生指标算法: {pformat(output['adjusted_indicator_algorithm'])}"))
            elif user_intent == "新增指标":
                output = self._handle_indicator_adding(user_input)
                print(append_list(OutputList,"新增后的指标列表: "))
                for i, iQuery in enumerate(self._Memeory["indicator_list"]):
                    print(append_list(OutputList, f"{pformat(iQuery)}"))
                    print(append_list(OutputList, f"候选指标: {pformat(self._Memeory['alternative_indicators'][iQuery['指标代码']])}"))
                ExtInfo["added_indicator_algorithm"] = output["added_indicator_algorithm"]
                if output["added_indicator_algorithm"]:
                    print(append_list(OutputList, f"新增的衍生指标算法: {pformat(output['added_indicator_algorithm'])}"))
            elif user_intent == "筛选条件修改":
                output = self._handle_filter_modification(user_input)
                print(append_list(OutputList, f"调整后的筛选条件: {pformat(output['sec_filter'])}"))
            elif user_intent == "指标算法修改":
                output = self._handle_indicator_algorithm_modification(user_input)
                ExtInfo["adjusted_indicator_algorithm"] = output["adjusted_indicator_algorithm"]
                for iIndicator in output["adjusted_indicator_algorithm"]:
                    print(append_list(OutputList, f"{iIndicator['指标名称']} 调整后的衍生指标算法: "))
                    print(append_list(OutputList, iIndicator["指标算法"]))
            elif user_intent == "量化分析需求":
                iOutputList, iExtInfo = self._handle_quant_requirement(user_input)
                OutputList += iOutputList
                ExtInfo.update(iExtInfo)
            else: # 闲聊
                output = self._handle_free_answer(user_input)
                print(append_list(OutputList, output["output"]))
        indicator_list = self._Memeory["indicator_list"]
        sec_filter = self._Memeory["sec_filter"]
        all_filled = True
        if indicator_list:
            missing_keys = get_indicator_missing_key(indicator_list)
            if missing_keys:
                print(append_list(OutputList, "以下这些指标的分项必填，请补充完整:"))
                print(append_list(OutputList, pformat(missing_keys)))
                all_filled = False
        if sec_filter:
            missing_keys = [iKey for iKey, iVal in sec_filter.items() if pd.isnull(iVal)]
            if missing_keys:
                print(append_list(OutputList, "以下这些筛选条件的分项必填，请补充完整:"))
                print(append_list(OutputList, pformat(missing_keys)))
                all_filled = False
        if indicator_list and all_filled:
            print(append_list(OutputList, "请确认系分是否满足需求, 是请输入yes, 否则请给出修改意见"))
        self._Memeory["all_filled"] = all_filled
        Output = {"output": "\n".join(OutputList), "output_list": OutputList, "status": self._Memeory, "ext_info": ExtInfo}
        return Output

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


if __name__ == '__main__':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('smart_selector_agent')

    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    user_input = input("你好，我是一个量化分析智能助手, 请告诉我你的量化分析需求:")
    while user_input:
        rsp = agent.run(input=user_input)
        rsp = rsp.to_dict()
        user_input = input(">>>")

    LOGGER.info("===")