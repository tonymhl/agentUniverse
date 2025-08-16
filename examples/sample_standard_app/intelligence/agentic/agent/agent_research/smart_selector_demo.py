# !/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Time    : 2024/11/30 16:20
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: smart_selector_demo.py
import pandas as pd
from prettyprinter import pformat

from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from sa_agent import validate_indicator_query, IndicatorQueryPrompt, set_indicator_default, set_filter_default
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager


def get_indicator_query_rslt(rsp):
    indicator_list = rsp.to_dict()["indicator_list"]
    print(f"indicator_list={indicator_list}")
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
    print(f"indicator_list={indicator_list}")
    return indicator_list


def get_filter_rslt(rsp):
    rsp = rsp.to_dict()
    sec_filter = rsp["filter"][0]
    print(f"filter={sec_filter}")
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
    print(f"filter={adjusted_filter}")
    return sec_filter


def get_indicator_calculator_rslt(indicator_query, agent):
    indicator_args = indicator_query.copy()
    indicator_id = indicator_args.pop("指标代码", None)
    indicator_args.pop("库编码", None)
    indicator_name = indicator_args.get("指标名称")

    indicator_info = input(f"请告诉我关于指标 '{indicator_name}' 的描述和要求:\n>>>")
    rsp = agent.run(indicator_name=indicator_name, indicator_args=str(indicator_args), indicator_info=indicator_info,
                    indicator_external_info="")
    rsp = rsp.to_dict()
    return {"指标代码": indicator_id, "指标名称": indicator_name, "用户描述": indicator_info, "指标算法": rsp["output"]}


def gen_indicator_calculator_rslt(indicator_query, user_info, agent):
    indicator_args = indicator_query.copy()
    indicator_id = indicator_args.pop("指标代码", None)
    indicator_args.pop("库编码", None)
    indicator_name = indicator_args.get("指标名称")

    rsp = agent.run(indicator_name=indicator_name, indicator_args=indicator_args, indicator_info=user_info,
                    indicator_external_info="")
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


# v0 版本
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    schedule_agent = AgentManager().get_instance_obj('schedule_agent')
    indicator_query_sa_agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
    indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
    filter_sa_agent = AgentManager().get_instance_obj('filter_sa_agent')

    # 用户输入
    print("======================== 需求输入 ========================")
    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月最大回撤不超过50%的产品"
    requirement = input("你好，我是一个量化分析智能助手, 请告诉我你的量化分析需求:\n>>>")

    # 任务编排
    print("\n======================== 任务编排 ========================")
    rsp = schedule_agent.run(requirement=requirement)
    task_list = rsp.to_dict()["output"]
    while (task_list == "非法需求"):
        requirement = input("您输入的并非有效的量化分析需求，请修改后重新输入:\n>>>")
        rsp = schedule_agent.run(requirement=requirement)
        task_list = rsp.to_dict()["output"]
    task_list = [iTask.strip() for iTask in task_list.split(">")]
    print(f"task_list={task_list}")

    # 任务系分
    indicator_algorithm = {}
    while task_list:
        iTask = task_list.pop(0)
        if iTask == "指标提取":
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = indicator_query_sa_agent.run(requirement=requirement, indicator_list="年化超额收益, 正收益概率")
            indicator_list = get_indicator_query_rslt(rsp)
        elif iTask == "标的筛选":
            if not all((pd.notnull(iQuery.get("库编码", None)) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in indicator_list):
                task_list = ["指标计算", iTask] + task_list
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = filter_sa_agent.run(requirement=requirement, indicator_list=indicator_list)
            sec_filter = get_filter_rslt(rsp)
        elif iTask == "指标计算":
            if all((pd.notnull(iQuery.get("库编码", None)) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in indicator_list):
                print("所有的指标已经在指标库中或者已经生成了算法, 不需要衍生计算!")
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")
            for i, iQuery in enumerate(indicator_list):
                if pd.notnull(iQuery["库编码"]): continue
                iAlgorithm = get_indicator_calculator_rslt(iQuery, indicator_calculator_sa_agent)
                indicator_algorithm[iQuery["指标代码"]] = iAlgorithm
            print(f"indicator_algorithm={indicator_algorithm}")
        else:
            print(f"\n======================== 系分生成: {iTask} ========================")
            raise Exception(f"不支持的任务: {iTask}")

    print("===")

# v1 版本
if __name__ == "__main__":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    intent_agent = AgentManager().get_instance_obj('user_intent_parse_agent')
    free_answer_agent = AgentManager().get_instance_obj('free_answer_agent')
    quant_consulting_agent = AgentManager().get_instance_obj('quant_consulting_agent')
    indicator_consulting_agent = AgentManager().get_instance_obj('indicator_consulting_agent')
    indicator_modification_agent = AgentManager().get_instance_obj('indicator_modification_agent')
    indicator_adding_agent = AgentManager().get_instance_obj('indicator_adding_agent')
    filter_modification_agent = AgentManager().get_instance_obj('filter_modification_agent')
    indicator_algorithm_modification_agent = AgentManager().get_instance_obj('indicator_algorithm_modification_agent')
    schedule_agent = AgentManager().get_instance_obj('schedule_agent')
    indicator_query_sa_agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
    filter_sa_agent = AgentManager().get_instance_obj('filter_sa_agent')
    indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
    indicator_knowledge = KnowledgeManager().get_instance_obj("indicator_knowledge")

    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    # requirement = "我想提取专户近1年年化超额收益超过0.8，且近3个月最大回撤不超过50%的产品"

    task_list = []
    indicator_list = []
    alternative_indicators, alternative_num = {}, 3
    indicator_dict = {}
    indicator_algorithm = {}
    sec_filter = {}
    user_input = input("你好，我是一个量化分析智能助手, 请告诉我你的量化分析需求:\n>>>")
    while user_input:
        rsp = intent_agent.run(
            input=user_input,
            filter=sec_filter,
            indicator_list=indicator_list,
            indicator_algorithm=indicator_algorithm,
            indicator_modification="",
            indicator_adding="",
            filter_modification="",
            indicator_algorithm_modification=""
        )
        rsp = rsp.to_dict()
        intent_list = [intent.strip() for intent in rsp["output"].split(",")]
        if ("筛选条件修改" in intent_list) and ("新增指标" not in intent_list): intent_list.insert(intent_list.index("筛选条件修改"), "新增指标")
        print(f"DEBUG: 用户意图: {intent_list}")
        for user_intent in intent_list:
            if user_intent == "量化知识咨询":
                rsp = quant_consulting_agent.run(input=user_input, quant_external_info="")
                rsp = rsp.to_dict()
                print(pformat(rsp["output"]))
            elif user_intent == "指标信息咨询":
                rsp = indicator_consulting_agent.run(input=user_input, indicator_external_info="")
                rsp = rsp.to_dict()
                print(pformat(rsp["output"]))
                print(f"相关的库指标: {pformat(rsp['lib_indicator_list'])}")
            elif user_intent == "指标口径修改":
                rsp = indicator_modification_agent.run(input=user_input, indicator_list=indicator_list, alternative_indicators=alternative_indicators)
                rsp = rsp.to_dict()
                adjusted_indicator_list = rsp["indicator_list"]
                print(f"调整后的指标列表: {pformat(adjusted_indicator_list)}")
                adjusted_indicator_algorithm = {}
                for i, iIndicator in enumerate(adjusted_indicator_list):
                    if (iIndicator!=indicator_dict[iIndicator["指标代码"]]) and pd.isnull(iIndicator["库编码"]):
                        iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                        adjusted_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                    indicator_dict[iIndicator["指标代码"]] = iIndicator
                indicator_list = adjusted_indicator_list
                if adjusted_indicator_algorithm:
                    print(f"调整后的衍生指标算法: {pformat(adjusted_indicator_algorithm)}")
                    indicator_algorithm.update(adjusted_indicator_algorithm)
            elif user_intent == "新增指标":
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
                    alternative_indicators[iQuery["指标代码"]] = get_alternative_indicator(iIndicator, indicator_knowledge, alternative_num=alternative_num)
                print("新增后的指标列表: ")
                for i, iQuery in enumerate(indicator_list):
                    print(f"{pformat(iQuery)}")
                    print(f"候选指标: {pformat(alternative_indicators[iQuery['指标代码']])}")
                indicator_algorithm.update(added_indicator_algorithm)
                if added_indicator_algorithm:
                    print(f"新增的衍生指标算法: {pformat(added_indicator_algorithm)}")
            elif user_intent == "筛选条件修改":
                rsp = filter_modification_agent.run(input=user_input, indicator_list=indicator_list, filter=sec_filter)
                rsp = rsp.to_dict()
                sec_filter = rsp["filter"][0]
                print(f"调整后的筛选条件: {pformat(sec_filter)}")
            elif user_intent == "指标算法修改":
                for iInd, iIndicator in indicator_algorithm.items():
                    if iIndicator["指标名称"] not in user_input: continue
                    for iQuery in indicator_list:
                        if iQuery["指标名称"] == iIndicator["指标名称"]:
                            iIndicatorArgs = iQuery.copy()
                            break
                    rsp = indicator_algorithm_modification_agent.run(input=user_input, indicator_name=iIndicator["指标名称"], indicator_args=iIndicatorArgs, indicator_algorithm=iIndicator)
                    rsp = rsp.to_dict()
                    iIndicator["指标算法"] = rsp["output"]
                    print(f"{iIndicator['指标名称']} 调整后的衍生指标算法: ")
                    print(iIndicator["指标算法"])
            elif user_intent == "量化分析需求":
                # 任务编排
                print("\n======================== 任务编排 ========================")
                rsp = schedule_agent.run(requirement=user_input)
                task_list = rsp.to_dict()["output"]
                if (task_list == "非法需求"):
                    print("您输入的并非有效的量化分析需求，请修改后重新输入")
                    task_list = []
                else:
                    task_list = [iTask.strip() for iTask in task_list.split(">")]
                print(f"任务编排: {task_list}")
                # 任务系分
                indicator_algorithm = {}
                indicator_dict = {}
                while task_list:
                    iTask = task_list.pop(0)
                    if iTask == "指标提取":
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        rsp = indicator_query_sa_agent.run(requirement=user_input, indicator_list="")
                        indicator_list = rsp.to_dict()["indicator_list"]
                        print("指标列表: ")
                        for i, iIndicator in enumerate(indicator_list):
                            iIndicator = set_indicator_default(iIndicator)
                            iIndicator["指标代码"] = f"Ind{i}"
                            indicator_list[i] = iIndicator
                            indicator_dict[iIndicator["指标代码"]] = iIndicator
                            alternative_indicators[iIndicator["指标代码"]] = get_alternative_indicator(iIndicator, indicator_knowledge, alternative_num=alternative_num)
                            print(f"{pformat(iIndicator)}")
                            print(f"候选指标: {pformat(alternative_indicators[iIndicator['指标代码']])}")
                    elif iTask == "标的筛选":
                        if not all((pd.notnull(iIndicator.get("库编码", None)) or (iIndicator["指标代码"] in indicator_algorithm)) for iIndicator in indicator_list):
                            task_list = ["指标计算", iTask] + task_list
                            continue
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        rsp = filter_sa_agent.run(requirement=user_input, indicator_list=indicator_list)
                        rsp = rsp.to_dict()
                        sec_filter = rsp["filter"][0]
                        sec_filter = set_filter_default(sec_filter, indicator_list=indicator_list)
                        print(f"筛选条件: {pformat(sec_filter)}")
                    elif iTask == "指标计算":
                        if all((pd.notnull(iIndicator.get("库编码", None)) or (iIndicator["指标代码"] in indicator_algorithm)) for iIndicator in indicator_list):
                            print("所有的指标已经在指标库中或者已经生成了算法, 不需要衍生计算!")
                            continue
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        for i, iIndicator in enumerate(indicator_list):
                            if pd.notnull(iIndicator["库编码"]): continue
                            iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                            indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                        print(f"衍生指标算法: {pformat(indicator_algorithm)}")
                    else:
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        raise Exception(f"不支持的任务: {iTask}")
            else:  # 闲聊
                rsp = free_answer_agent.run(input=user_input)
                rsp = rsp.to_dict()
                print(pformat(rsp["output"]))
                break
        all_filled = True
        if indicator_list:
            missing_keys = get_indicator_missing_key(indicator_list)
            if missing_keys:
                print("以下这些指标的分项必填，请补充完整:")
                print(pformat(missing_keys))
                all_filled = False
        if sec_filter:
            missing_keys = [iKey for iKey, iVal in sec_filter.items() if pd.isnull(iVal)]
            if missing_keys:
                print("以下这些筛选条件的分项必填，请补充完整:")
                print(pformat(missing_keys))
                all_filled = False
        if indicator_list and all_filled:
            if_ok = input("请确认系分是否 OK, OK 请输入 yes, 否则给出修改意见: >>>")
            if if_ok.lower().strip() == "yes":
                print("系分生成完毕!")
                break
            else:
                user_input = if_ok
        else:
            user_input = input("请说点啥: >>>")

    print("===")