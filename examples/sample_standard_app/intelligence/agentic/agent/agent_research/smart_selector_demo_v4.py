#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/26 17:37
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : smart_selector_demo_v4.py
# @Software: PyCharm


import pandas as pd
from prettyprinter import pformat

from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from sa_agent import validate_indicator_query, IndicatorQueryPrompt, set_indicator_default, set_filter_default
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager


from sample_standard_app.app.core.agent.asset_research.sa_agent import validate_indicator_query, IndicatorQueryPrompt, set_indicator_default, set_filter_default
from agentuniverse.base.util.logging.logging_util import LOGGER
from sample_standard_app.app.core.agent.asset_research.utils import *
# from agentuniverse_ant_ext.connector.odps.universal_odps_operator import UniversalODPSOperator, Column, Partition
import traceback
from time import sleep


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


def generate_calculation_code(iQuery, indicator_algorithm, error_info):
    # 获取indicator_calculation_agent实例
    indicator_calculation_agent = AgentManager().get_instance_obj('indicator_calculation_agent')
    asset_type = iQuery["资产类型"]
    start_date = iQuery["开始时间"]
    end_date = iQuery["截止时间"]

    # 检查并处理 None 值
    if start_date is None or '':
        start_date = ''
    else:
        # 检查并添加 00:00:00 到日期末尾
        if not start_date.endswith('00:00:00'):
            start_date = f"{start_date} 00:00:00"
        else:
            start_date = start_date

    if end_date is None or '':
        end_date = ''
    else:
        # 检查并添加 00:00:00 到日期末尾
        if not end_date.endswith('00:00:00'):
            end_date = f"{end_date} 00:00:00"
        else:
            end_date = end_date

    if asset_type == "公募基金":
        # 查询公募数据
        NV_data = get_mutual_fund_NV(start_date, end_date)
    else:
        LOGGER.error(f"不支持的资产类型: {asset_type}")
        NV_data = get_mutual_fund_NV(start_date, end_date)

    # 去除后缀
    # NV_data['symbol'] = NV_data['symbol'].apply(lambda x: x.split('.')[0])
    # NV_data = NV_data.rename(columns={'net_value_date': 'the_datetime', 'restored_net_value': 'value'})
    LOGGER.info(f"NV_data:\n{NV_data}")

    # Call indicator calculation agent
    res_calc = indicator_calculation_agent.run(
        indicator_list=iQuery,
        indicator_algorithm=indicator_algorithm,
        NV_data=NV_data,
        error_info=error_info
    )
    LOGGER.info(f"indicator_calculation_agent result:\n{res_calc.to_dict()['output']}")

    # Extract and execute calculation code
    code_str = extract_code_from_output(res_calc.to_dict()['output'])
    LOGGER.info(f"Extracted calculation code:\n{code_str}")

    if not validate_calculation_code(code_str):
        LOGGER.error("Invalid calculation code generated")
        raise ValueError("Generated code failed validation")

    return code_str, NV_data


def generate_code_for_indicator_filter(requirement, indicator_list, indicator_data, sec_filter, error_info):
    # 获取filter_indicator_agent实例
    filter_indicator_agent = AgentManager().get_instance_obj('filter_indicator_agent')

    # 调用filter_indicator_agent进行指标筛选代码生成
    res_filter = filter_indicator_agent.run(
        requirement=requirement,
        indicator_list=indicator_list,
        indicator_data=indicator_data,
        filter_condition=sec_filter,
        error_info=error_info
    )
    output = res_filter.to_dict()['output']
    LOGGER.info(f"filter_indicator_agent产出代码: \n {output}")

    # 提取代码
    code_str = extract_code_from_output(output)
    return code_str


def execute_task_with_verification(task_type, code_str, data, task, kwargs):
    """执行任务并进行验证"""
    debug_agent = AgentManager().get_instance_obj('code_debug_agent')
    eval_agent = AgentManager().get_instance_obj('code_evaluation_agent')

    # 代码调试阶段
    debug_result = debug_agent.run(
        code_str=code_str,
        indicator_data=data,
        task=task
    )

    if not debug_result.to_dict()['output']:
        LOGGER.error(f"代码验证失败: {debug_result.to_dict()['output']}")
        return None
    else:
        LOGGER.info(f"{debug_result.to_dict()['output']}")
        bool_value_str = extract_debug_result(debug_result.to_dict()['output'])
        bool_value = extract_boolean(bool_value_str)
        LOGGER.info(bool_value)
        if bool_value is False:
            LOGGER.error(f"代码验证失败: {debug_result.to_dict()['output']}")
            # 是否重试
            retry = input("是否重试? (y/n): ").lower()
            if retry == 'y':
                if task_type == "filter":
                    code_str = generate_code_for_indicator_filter(requirement=kwargs.get('user_input'),
                                                                  indicator_list=kwargs.get('indicator_list'),
                                                                  indicator_data=kwargs.get('indicator_data'),
                                                                  sec_filter=kwargs.get('filter_condition'),
                                                                  error_info=kwargs.get('error_info')
                                                                  )
                    return execute_task_with_verification(task_type, code_str, data, task, kwargs)
                elif task_type == "calculation":
                    code_str, NV_data = generate_calculation_code(iQuery=kwargs.get('iQuery'),
                                                                  indicator_algorithm=kwargs.get('iAlgorithm'),
                                                                  error_info=kwargs.get('error_info')
                                                                  )
                    return execute_task_with_verification(task_type, code_str, data, task, kwargs)
            else:
                LOGGER.info("继续执行")
                pass
        else:
            LOGGER.info("代码验证通过")

    # 执行代码
    try:
        if task_type == "filter":
            result = execute_filter_code(code_str, data)
        elif task_type == "calculation":
            result = execute_calculation_code(code_str, data)
    except Exception as e:
        LOGGER.error(f"代码执行失败: {str(e)}")
        # 是否重试
        retry = input("是否重试? (y/n): ").lower()
        if retry == 'y':
            if task_type == "filter":
                code_str = generate_code_for_indicator_filter(requirement=kwargs.get('user_input'),
                                                              indicator_list=kwargs.get('indicator_list'),
                                                              indicator_data=kwargs.get('indicator_data'),
                                                              sec_filter=kwargs.get('filter_condition'),
                                                              error_info=kwargs.get('error_info')
                                                              )
                return execute_task_with_verification(task_type, code_str, data, task, kwargs)
            elif task_type == "calculation":
                code_str, NV_data = generate_calculation_code(iQuery=kwargs.get('iQuery'),
                                                              indicator_algorithm=kwargs.get('iAlgorithm'),
                                                              error_info=kwargs.get('error_info'))
                return execute_task_with_verification(task_type, code_str, data, task, kwargs)
        else:
            print("用户取消操作")
            return None

    # 评估结果
    eval_result = eval_agent.run(
        code=code_str,
        indicator_data=data,
        result=result,
        task=task
    )

    eval_result = eval_result.to_dict()['output']
    if not eval_result:
        LOGGER.warn(f"未产出评估意见")
        user_confirm = input("结果可能不满足要求，是否重新生成代码? (y/n): ")
        if user_confirm.lower() == 'y':
            if task_type == "filter":
                code_str = generate_code_for_indicator_filter(requirement=kwargs.get('user_input'),
                                                              indicator_list=kwargs.get('indicator_list'),
                                                              indicator_data=kwargs.get('indicator_data'),
                                                              sec_filter=kwargs.get('filter_condition'),
                                                              error_info=kwargs.get('error_info')
                                                              )
                return execute_task_with_verification(task_type, code_str, data, task, kwargs)
            elif task_type == "calculation":
                code_str, NV_data = generate_calculation_code(iQuery=kwargs.get('iQuery'),
                                                              indicator_algorithm=kwargs.get('iAlgorithm'),
                                                              error_info=kwargs.get('error_info')
                                                              )
                return execute_task_with_verification(task_type, code_str, data, task, kwargs)
        else:
            print("用户取消操作")
            return None
    else:
        LOGGER.info(f"评估意见: {eval_result}")
    return result


def get_user_confirmation(task_name: str, task_info: dict = None) -> bool:
    """获取用户确认是否执行任务"""
    print(f"\n======================== 准备执行: {task_name} ========================")
    if task_info:
        print("\n当前任务信息:")
        for key, value in task_info.items():
            print(f"{key}: {value}")

    confirmation = input("\n是否继续执行该任务? (y/n): ")
    return confirmation.lower().strip() == 'y'


def handle_code_generation_error(error: Exception, agent, **kwargs):
    """处理代码生成错误，使用错误信息优化代码生成"""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    }

    # 将错误信息添加到agent输入中
    kwargs['error_info'] = error_info

    # 重新生成代码
    try:
        return agent.run(**kwargs)
    except Exception as e:
        LOGGER.error(f"Code regeneration failed: {str(e)}")
        return None


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

    indicator_nscode_select_agent = AgentManager().get_instance_obj('indicator_nscode_select_agent')
    # indicator_extraction_agent = AgentManager().get_instance_obj('indicator_extraction_agent')
    indicator_extraction_agent = AgentManager().get_instance_obj('indicator_nscode_extraction_agent')
    filter_indicator_agent = AgentManager().get_instance_obj('filter_indicator_agent')
    indicator_calculation_agent = AgentManager().get_instance_obj('indicator_calculation_agent')
    debug_agent = AgentManager().get_instance_obj('code_debug_agent')
    eval_agent = AgentManager().get_instance_obj('code_evaluation_agent')

    # requirement = "我想提取固收+近1年年化收益超过0.8，且近3个月最大回撤不超过50%的产品"
    # requirement = "我想提取专户近1年年化超额收益超过0.8，且近3个月最大回撤不超过50%的产品，'开始时间'为'2024-01-01'，'产品池'为'专户'"
    # requirement = 我想提取固收+近1年年化收益超过0.02，且近1年最大回撤不超过50%的公募产品，开始时间为'2024-01-01'

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
                    iAlternativeIndicators = indicator_knowledge.query_knowledge(query_str=iIndicator["指标名称"], similarity_top_k=alternative_num)
                    alternative_indicators[iIndicator["指标代码"]] = [{"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in iAlternativeIndicators]
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
                        for i, iQuery in enumerate(indicator_list):
                            iQuery = set_indicator_default(iQuery)
                            iQuery["指标代码"] = f"Ind{i}"
                            indicator_list[i] = iQuery
                            indicator_dict[iQuery["指标代码"]] = iQuery
                            iAlternativeIndicators = indicator_knowledge.query_knowledge(query_str=iQuery["指标名称"], similarity_top_k=alternative_num)
                            alternative_indicators[iQuery["指标代码"]] = [{"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in iAlternativeIndicators]
                            print(f"{pformat(iQuery)}")
                            print(f"候选指标: {pformat(alternative_indicators[iQuery['指标代码']])}")
                    elif iTask == "标的筛选":
                        if not all((pd.notnull(iQuery.get("库编码", None)) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in indicator_list):
                            task_list = ["指标计算", iTask] + task_list
                            continue
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        rsp = filter_sa_agent.run(requirement=user_input, indicator_list=indicator_list)
                        rsp = rsp.to_dict()
                        sec_filter = rsp["filter"][0]
                        sec_filter = set_filter_default(sec_filter, indicator_list=indicator_list)
                        print(f"筛选条件: {pformat(sec_filter)}")
                    elif iTask == "指标计算":
                        if all((pd.notnull(iQuery.get("库编码", None)) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in indicator_list):
                            print("所有的指标已经在指标库中或者已经生成了算法, 不需要衍生计算!")
                            continue
                        print(f"\n======================== 系分生成: {iTask} ========================")
                        for i, iQuery in enumerate(indicator_list):
                            if pd.notnull(iQuery["库编码"]): continue
                            iAlgorithm = gen_indicator_calculator_rslt(iQuery, user_info="", agent=indicator_calculator_sa_agent)
                            indicator_algorithm[iQuery["指标代码"]] = iAlgorithm
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

    # =================================================
    # 指标选择
    task_info = {
        "指标列表": pformat(indicator_list),
        "候选指标": pformat(alternative_indicators),
    }

    if not get_user_confirmation("指标选择", task_info):
        print("用户取消指标选择任务")

    indicator_list_new = []
    max_retries = 3
    retry_count = 0
    while indicator_list_new == [] and retry_count < max_retries:
        try:
            LOGGER.info("开始指标选择")
            error_info = ''
            res = indicator_nscode_select_agent.run(indicator_list=indicator_list,
                                                    alternative_indicators=alternative_indicators,
                                                    error_info=error_info)
            indicator_list_new = res.to_dict()["indicator_list"]
            LOGGER.info(f"选择的指标列表: {indicator_list_new}")

            if indicator_list_new is not None:
                LOGGER.info(f"指标nscode选择成功")
            else:
                raise ValueError(f"指标nscode选择失败")
        except Exception as e:
            retry_count += 1
            LOGGER.error(f"提取失败 (尝试 {retry_count}/{max_retries}): {str(e)}")

            if retry_count < max_retries:
                print("\n尝试使用错误信息优化指标选择...")
                res = handle_code_generation_error(
                    e,
                    indicator_nscode_select_agent,
                    indicator_list=indicator_list,
                    alternative_indicators=alternative_indicators
                )
                if res is None:
                    continue

            if retry_count == max_retries:
                if not get_user_confirmation("是否继续尝试提取?"):
                    break
                retry_count = 0

    print("匹配完成")
    # =================================================
    # 指标提取部分
    task_info = {
        "指标列表": pformat(indicator_list),
        "匹配后指标列表": pformat(indicator_list_new),
    }

    if not get_user_confirmation("指标提取", task_info):
        print("用户取消指标提取任务")

    indicator_data = []
    max_retries = 3
    retry_count = 0

    while indicator_data == [] and retry_count < max_retries:
        LOGGER.info("开始指标提取")
        LOGGER.info("基于新的匹配后指标列表", pformat(indicator_list_new))
        try:
            for i, iQuery in enumerate(indicator_list_new):
                error_info = ''
                LOGGER.info(f"开始提取指标 {i + 1}/{len(indicator_list_new)}: {iQuery['指标名称']}")
                res = indicator_extraction_agent.run(input=iQuery, error_info=error_info)
                data = res.to_dict()["data"]

                if data is not None:
                    LOGGER.info(f"指标 {iQuery['指标名称']} 提取成功")
                    indicator_data.append(data)
                else:
                    raise ValueError(f"指标 {iQuery['指标名称']} 提取结果为空")
        except Exception as e:
            retry_count += 1
            LOGGER.error(f"提取失败 (尝试 {retry_count}/{max_retries}): {str(e)}")

            if retry_count < max_retries:
                print("\n尝试使用错误信息优化提取逻辑...")
                res = handle_code_generation_error(
                    e,
                    indicator_extraction_agent,
                    input=iQuery
                )
                if res is None:
                    continue

            if retry_count == max_retries:
                if not get_user_confirmation("是否继续尝试提取?"):
                    break
                retry_count = 0

    print("指标提取完成")
    # =================================================
    # 指标筛选部分
    sleep(2)
    task_info = {
        "筛选条件": pformat(sec_filter),
        "可用指标": pformat(indicator_list)
    }

    if not get_user_confirmation("指标筛选", task_info):
        print("用户取消指标筛选任务")

    LOGGER.info("开始指标筛选任务")
    code_str = None
    filtered_data = None
    max_retries = 3
    retry_count = 0
    error_info = ''
    indicator_data = convert_indicator_data_to_df(indicator_data)
    # indicator_data = filter_with_asset_pool(indicator_data, sec_filter)

    while filtered_data is None and retry_count < max_retries:
        try:
            if code_str is None:
                code_str = generate_code_for_indicator_filter(
                    user_input,
                    indicator_list,
                    indicator_data,
                    sec_filter,
                    error_info
                )

            # 执行校验及筛选
            filtered_data = execute_task_with_verification(
                "filter",
                code_str,
                indicator_data,
                sec_filter,
                kwargs={
                    "user_input": user_input,
                    "indicator_list": indicator_list,
                    "indicator_data": indicator_data,
                    "sec_filter": sec_filter,
                    "error_info": error_info
                }
            )
            if filtered_data is not None:
                LOGGER.info(f"指标筛选成功: \n {filtered_data}")

        except Exception as e:
            retry_count += 1
            LOGGER.error(f"筛选失败 (尝试 {retry_count}/{max_retries}): {str(e)}")

            if retry_count < max_retries:
                print("\n尝试使用错误信息优化筛选代码...")
                code_str = None  # 重置代码字符串
                res = handle_code_generation_error(
                    e,
                    filter_indicator_agent,
                    requirement=user_input,
                    indicator_list=indicator_list,
                    indicator_data=indicator_data,
                    filter_condition=sec_filter
                )
                if res is not None:
                    continue
            if retry_count == max_retries:
                if not get_user_confirmation("是否继续尝试筛选?"):
                    break
                retry_count = 0

    print("指标筛选完成")

    # =================================================
    # 指标计算部分
    sleep(2)
    task_info = {
        "待计算指标": [ind["指标名称"] for ind in indicator_list if not ind["库编码"]],
        "计算算法": pformat(indicator_algorithm)
    }

    if not get_user_confirmation("指标计算", task_info):
        print("用户取消指标计算任务")

    LOGGER.info("开始指标计算")
    for i, iQuery in enumerate(indicator_list):
        if iQuery["库编码"]:
            continue

        error_info = ''
        LOGGER.info(f"开始计算指标 {i + 1}/{len(indicator_list)}: {iQuery['指标名称']}")
        iAlgorithm = indicator_algorithm[iQuery["指标代码"]]

        calculation_result = None
        retry_count = 0

        while calculation_result is None and retry_count < max_retries:
            try:
                code_str, NV_data = generate_calculation_code(iQuery, iAlgorithm, error_info)

                # 执行校验及计算
                calculation_result = execute_task_with_verification(
                    "calculation",
                    code_str,
                    NV_data,
                    iAlgorithm,
                    kwargs={"iQuery": iQuery, "iAlgorithm": iAlgorithm, 'error_info': error_info}
                )

                if calculation_result is not None:
                    LOGGER.info(f"指标 {iQuery['指标名称']} 计算成功")
                    LOGGER.info(f"计算结果: \n {calculation_result}")

            except Exception as e:
                retry_count += 1
                LOGGER.error(f"计算失败 (尝试 {retry_count}/{max_retries}): {str(e)}")

                if retry_count < max_retries:
                    print(f"\n尝试使用错误信息优化计算代码...")
                    res = handle_code_generation_error(
                        e,
                        indicator_calculation_agent,
                        iQuery=iQuery,
                        iAlgorithm=iAlgorithm
                    )
                    if res is not None:
                        continue
                if retry_count == max_retries:
                    if not get_user_confirmation(f"是否继续尝试计算指标 {iQuery['指标名称']}?"):
                        break
                    retry_count = 0

    print("指标计算完成")