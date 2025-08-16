#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2025/2/14 10:53
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : smart_selector_agent_v*.py
# @Software: PyCharm


import numpy as np
import pandas as pd
import re
import time
import signal
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from time import sleep
from prettyprinter import pformat
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from sample_standard_app.app.core.agent.asset_research.utils import *
from sample_standard_app.app.core.agent.asset_research.sa_agent import validate_indicator_query, IndicatorQueryPrompt, \
    set_indicator_default, set_filter_default


def append_list(l, e):
    l.append(e)
    return e

##############################
# 状态管理模块
##############################
@dataclass(frozen=True)
class State:
    status: str = "INIT"
    indicator_list: List[Dict] = field(default_factory=list)
    filter_condition: Dict = field(default_factory=dict)
    code_versions: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    extracted_data: List[Any] = field(default_factory=list)
    filtered_data: List[Any] = field(default_factory=list)
    calculation_results: Dict = field(default_factory=dict)
    memory: Dict = field(default_factory=dict)  # 持久化存储

    def update(self, **kwargs):
        return State(**{**self.__dict__, **kwargs})


class StateManager:
    def __init__(self, max_iter=15):
        self.max_iter = max_iter
        self.state_history = []

    def run_loop(self, initial_state: State, dispatcher, checker):
        current_state = initial_state
        for _ in range(self.max_iter):
            action = self.select_action(current_state)
            new_state = dispatcher.dispatch(action, current_state)

            if checker(new_state):
                return new_state

            current_state = self.merge_states(current_state, new_state)
            self.state_history.append(current_state)
        return current_state

    def select_action(self, state: State) -> str:
        action_map = {
            "INIT": "check_requirements",
            "READY_EXECUTE": "execute_extraction",
            "EXTRACTED": "execute_filter",
            "FILTERED": "execute_calculation",
            "ERROR": "handle_error"
        }
        return action_map.get(state.status, "default_handler")

    def merge_states(self, old: State, new: State) -> State:
        return State(
            status=new.status,
            indicator_list=new.indicator_list or old.indicator_list,
            filter_condition=new.filter_condition or old.filter_condition,
            code_versions=old.code_versions + new.code_versions,
            errors=old.errors + new.errors,
            extracted_data=new.extracted_data or old.extracted_data,
            filtered_data=new.filtered_data or old.filtered_data,
            calculation_results={**old.calculation_results, **new.calculation_results},
            memory={**old.memory, **new.memory}
        )


##############################
# 执行部分
##############################
class ExecutionDispatcher:
    def __init__(self):
        self.handlers = {
            "check_requirements": self.handle_check_requirements,
            "execute_extraction": self.handle_extraction,
            "execute_filter": self.handle_filter,
            "execute_calculation": self.handle_calculation,
            "handle_error": self.handle_error,
            "default_handler": self.handle_default
        }
        self.sanitizer = CodeSanitizer()
        # self.validator = ValidationPipeline()

    def dispatch(self, action: str, state: State) -> State:
        return self.handlers[action](state)

    def handle_check_requirements(self, state: State) -> State:
        if not state.memory.get("all_filled"):
            print("系分项未填写完整，请重新填写")
            return state.update(status="ERROR", errors=["Requirements not fully filled"])
        return state.update(status="READY_EXECUTE")

    def handle_extraction(self, state: State) -> State:
        print("开始执行指标提取任务")
        try:
            # IndicatorExtractionTask逻辑
            agent = AgentManager().get_instance_obj('indicator_nscode_extraction_agent')
            extracted_data = []
            for ind in state.indicator_list:
                if pd.notnull(ind.get("库编码")):
                    print(f"{ind}, 开始执行指标提取任务")
                    res = agent.run(input=ind, error_info=state.errors)
                    extracted_data.append(res.to_dict()["data"])
                else:
                    print(f"{ind}, 无库编码，跳过指标提取任务")
            print(f"指标提取完成, 提取结果: {extracted_data}")
            return state.update(status="EXTRACTED", extracted_data=extracted_data)
        except Exception as e:
            return state.update(status="FILTERED", errors=[f"{ind} Extraction failed: {str(e)}"])  # 修改状态为"FILTERED", 直接执行指标计算

    def handle_filter(self, state: State) -> State:
        print("开始执行指标筛选任务")
        if not state.extracted_data:
            print("缺少指标数据，跳过指标筛选任务")
            return state.update(status="FILTERED")  # 修改状态为"FILTERED", 直接执行指标计算
        try:
            # IndicatorFilteringTask逻辑
            code = self._generate_filter_code(state)
            # 打印代码
            print(f"开始执行代码: \n {code}")
            result = execute_filter_code(code, state.extracted_data)
            if not result.empty:
                print(f"指标筛选完成, 筛选结果: {result}")
                return state.update(status="FILTERED", filtered_data=result)
            else:
                print("指标筛选结果为空")
                return state.update(status="FILTERED")
        except Exception as e:
            return state.update(status="ERROR", errors=[f"Filter failed: {str(e)}"])

    def _generate_filter_code(self, state: State) -> str:
        agent = AgentManager().get_instance_obj('filter_indicator_agent')
        res = agent.run(
            requirement=state.memory.get("task"),
            indicator_list=state.indicator_list,
            indicator_data=state.extracted_data,
            filter_condition=state.filter_condition,
            error_info=state.errors
        )
        code = extract_code_from_output(res.to_dict()['output'])
        return self.sanitizer.sanitize(code)

    def handle_calculation(self, state: State) -> State:
        print("开始执行指标计算任务")
        try:
            # IndicatorCalculationTask逻辑
            results = {}
            for ind in state.indicator_list:
                if pd.isnull(ind.get("库编码")):
                    code, data = self._generate_calculation_code(ind, state)
                    # 打印代码
                    print(f"{ind}, 开始执行代码: \n {code}")
                    result = execute_calculation_code(code, data)
                    if not result.empty:
                        print(f"{ind}, 指标计算完成, 计算结果: \n {result}")
                        results[ind["指标代码"]] = result
                    else:
                        print(f"{ind}, 指标计算失败, 处理中...")
                        return state.update(status="ERROR", errors=[f"Calculation failed, result is empty"])

            print(f"指标计算完成, 计算结果: {results}")
            return state.update(status="COMPLETED", calculation_results=results)
        except Exception as e:
            return state.update(status="ERROR", errors=[f"Calculation failed: {str(e)}"])

    def _generate_calculation_code(self, indicator: Dict, state: State):
        agent = AgentManager().get_instance_obj('indicator_calculation_agent')
        NV_data = self._get_nv_data(indicator)
        res = agent.run(
            indicator_list=indicator,
            indicator_algorithm=state.memory.get("indicator_algorithm", {}),
            NV_data=NV_data,
            error_info=state.errors
        )
        code = extract_code_from_output(res.to_dict()['output'])
        return self.sanitizer.sanitize(code), NV_data

    def _get_nv_data(self, indicator: Dict) -> pd.DataFrame:
        start_date = indicator.get("开始时间", "")
        end_date = indicator.get("截止时间", "")
        asset_type = indicator.get("资产类型", "")

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
            print(f"不支持的资产类型: {asset_type}")
            NV_data = get_mutual_fund_NV(start_date, end_date)

        # 去除后缀
        # NV_data['symbol'] = NV_data['symbol'].apply(lambda x: x.split('.')[0])
        # NV_data = NV_data.rename(columns={'net_value_date': 'the_datetime', 'restored_net_value': 'value'})
        print(f"NV_data:\n{NV_data}")

        return NV_data

    def handle_error(self, state: State) -> State:
        error_msg = state.errors[-1] if state.errors else "Unknown error"
        print(f"需要处理错误: {error_msg}")
        choice = input("是否重试? (y/n): ").lower()
        if choice == 'y':
            if "Calculation" in state.errors[-1]:
                return state.update(status="FILTERED", errors=state.errors[:-1])
            elif "Filter" in state.errors[-1]:
                return state.update(status="EXTRACTED", errors=state.errors[-1])
            return state.update(status="FILTERED", errors=state.errors[-1])
        return state.update(status="FAILED")

    def handle_default(self, state: State) -> State:
        return state


##############################
# 安全验证模块
##############################
class CodeSanitizer:
    forbidden_patterns = [
        r"os\.(system|popen)",
        r"subprocess\.",
        r"__import__",
        r"eval\("
    ]

    def sanitize(self, code: str) -> str:
        for pattern in self.forbidden_patterns:
            if re.search(pattern, code):
                raise SecurityError(f"检测到危险模式: {pattern}")
        return code


# TODO: 验证逻辑 ValidationPipeline
# class ValidationPipeline:
#     def validate(self, code: str, data: pd.DataFrame) -> dict:
#         return {
#             "syntax": self._validate_syntax(code),
#             "logic": self._validate_logic(code, data),
#             "performance": self._validate_performance(code, data)
#         }
#
#     def _validate_syntax(self, code: str) -> dict:
#         try:
#             compile(code, '<string>', 'exec')
#             return {"valid": True}
#         except Exception as e:
#             return {"valid": False, "message": str(e)}
#
#     def _validate_logic(self, code: str, data: pd.DataFrame) -> dict:
#         eval_agent = AgentManager().get_instance_obj('code_evaluation_agent')
#         res = agent.run(code=code, data_summary=data.describe().to_dict())
#         res = eval_agent.run(
#             code=code,
#             indicator_data=data,
#             result=result
#         )
#         return res.to_dict()
#
#     def _validate_performance(self, code: str, data: pd.DataFrame) -> dict:
#         try:
#             with time_limit(500):
#                 start = time.time()
#                 execute_in_sandbox(code, data)
#                 return {"time": time.time() - start, "status": "success"}
#         except TimeoutError:
#             return {"status": "timeout"}


##############################
# 核心Agent类
##############################
class SmartSelectorAgent(Agent):
    def __init__(self):
        super().__init__()
        self._Memory = dict(
            task_list=[],
            indicator_list=[],
            alternative_indicators={},
            indicator_dict={},
            indicator_algorithm={},
            sec_filter={},
            all_filled=False
        )
        # self.execution_manager = StateManager()
        # self.execution_dispatcher = ExecutionDispatcher()

    def input_keys(self) -> list[str]:
        return ['input']

    def output_keys(self) -> list[str]:
        return ["output", "output_list", "status", "ext_info"]

    def execute(self, input_object: InputObject, agent_input: dict):
        OutputList, ExtInfo = [], {}
        user_input = agent_input["input"]

        if user_input.lower() == "yes" and self._Memory['all_filled']:
            # 执行链路
            return self._execute_operations(OutputList, ExtInfo)
        else:
            # 意图识别&系分生成
            return self._handle_intent_processing(user_input, OutputList, ExtInfo)

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result

    def _handle_intent_processing(self, user_input: str, OutputList: list, ExtInfo: dict) -> dict:
        # 意图识别
        intent_agent = AgentManager().get_instance_obj('user_intent_parse_agent')
        rsp = intent_agent.run(
            input=user_input,
            filter=self._Memory["sec_filter"],
            indicator_list=self._Memory["indicator_list"],
            indicator_algorithm=self._Memory["indicator_algorithm"],
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
                ExtInfo["adjusted_indicator_algorithm"] = output.get('adjusted_indicator_algorithm', {})
                print(
                    append_list(OutputList, f"调整后的指标列表: {pformat(output['adjusted_indicator_list'])}"))
                print(append_list(OutputList,
                                  f"调整后的衍生指标算法: {pformat(output.get('adjusted_indicator_algorithm', {}))}"))
            elif user_intent == "新增指标":
                output = self._handle_indicator_adding(user_input)
                print(append_list(OutputList, "新增后的指标列表: "))
                for i, iQuery in enumerate(self._Memory["indicator_list"]):
                    print(append_list(OutputList, f"{pformat(iQuery)}"))
                    print(append_list(OutputList,
                                      f"候选指标: {pformat(self._Memory['alternative_indicators'][iQuery['指标代码']])}"))
                ExtInfo["added_indicator_algorithm"] = output.get("added_indicator_algorithm", {})
                if output.get("added_indicator_algorithm"):
                    print(append_list(OutputList,
                                      f"新增的衍生指标算法: {pformat(output['added_indicator_algorithm'])}"))
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
            else:  # 闲聊
                output = self._handle_free_answer(user_input)
                print(append_list(OutputList, output["output"]))
        indicator_list = self._Memory["indicator_list"]
        sec_filter = self._Memory["sec_filter"]
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
        self._Memory["all_filled"] = all_filled
        # Output = {"output": "\n".join(OutputList), "output_list": OutputList, "status": self._Memory,
        #           "ext_info": ExtInfo}

        # 完整性检查
        self._check_completeness(OutputList)
        return self._build_output(OutputList, ExtInfo)

    def _execute_operations(self, OutputList: list, ExtInfo: dict) -> dict:
        # 使用状态机执行后续操作
        initial_state = State(
            memory=self._Memory,
            indicator_list=self._Memory['indicator_list'],
            filter_condition=self._Memory['sec_filter']
        )

        # final_state = self.execution_manager.run_loop(
        final_state = StateManager().run_loop(
            initial_state,
            # self.execution_dispatcher,
            ExecutionDispatcher(),
            lambda s: s.status in ["COMPLETED", "FAILED"]
        )

        # 收集结果
        OutputList.extend([
            f"指标提取结果: {final_state.extracted_data}",
            f"指标筛选结果: {final_state.filtered_data}",
            f"计算结果: {final_state.calculation_results}"
        ])
        print(f"Final_state: {final_state.status}")

        return self._build_output(OutputList, ExtInfo, final_state)

    def _check_completeness(self, OutputList: list):
        # 完整性检查
        missing = get_indicator_missing_key(self._Memory['indicator_list'])
        if missing:
            OutputList.append(f"缺失字段: {pformat(missing)}")
            self._Memory['all_filled'] = False

    def _build_output(self, OutputList: list, ExtInfo: dict, state: State = None) -> dict:
        output = {
            "output": "\n".join(OutputList),
            "output_list": OutputList,
            "ext_info": ExtInfo,
            "status": {
                "memory": self._Memory,
                "execution_state": state.__dict__ if state else None
            }
        }
        print(pformat(output))
        return output

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
        indicator_list = self._Memory["indicator_list"]
        indicator_dict = self._Memory["indicator_dict"]
        indicator_algorithm = self._Memory["indicator_algorithm"]
        alternative_indicators = self._Memory["alternative_indicators"]

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
        self._Memory["indicator_list"] = adjusted_indicator_list
        if adjusted_indicator_algorithm:
            output["adjusted_indicator_algorithm"] = adjusted_indicator_algorithm
            indicator_algorithm.update(adjusted_indicator_algorithm)
        return output

    def _handle_indicator_adding(self, user_input):
        indicator_adding_agent = AgentManager().get_instance_obj('indicator_adding_agent')
        indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
        indicator_knowledge = KnowledgeManager().get_instance_obj("indicator_knowledge")
        indicator_list = self._Memory["indicator_list"]
        indicator_dict = self._Memory["indicator_dict"]
        indicator_algorithm = self._Memory["indicator_algorithm"]
        alternative_indicators = self._Memory["alternative_indicators"]
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
        indicator_list = self._Memory["indicator_list"]
        sec_filter = self._Memory["sec_filter"]

        rsp = filter_modification_agent.run(input=user_input, indicator_list=indicator_list, filter=sec_filter)
        rsp = rsp.to_dict()
        sec_filter = rsp["filter"][0]
        self._Memory["sec_filter"] = sec_filter
        return {"sec_filter": sec_filter}

    def _handle_indicator_algorithm_modification(self, user_input):
        indicator_algorithm_modification_agent = AgentManager().get_instance_obj('indicator_algorithm_modification_agent')
        indicator_list = self._Memory["indicator_list"]
        indicator_algorithm = self._Memory["indicator_algorithm"]

        adjusted_indicator_algorithm = []
        for iInd, iIndicator in indicator_algorithm.items():
            if iIndicator["指标名称"] not in user_input:
                continue
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
        alternative_indicators = self._Memory["alternative_indicators"]
        alternative_num = 3

        # 任务编排
        print(append_list(OutputList, "======================== 任务编排 ========================"))
        rsp = schedule_agent.run(requirement=user_input)
        task_list = rsp.to_dict()["output"]
        if task_list == "非法需求":
            print(append_list(OutputList, "您输入的并非有效的量化分析需求，请修改后重新输入"))
            task_list = []
        else:
            task_list = [iTask.strip() for iTask in task_list.split(">")]
        print(append_list(OutputList, f"任务编排: {task_list}"))
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
                    if pd.notnull(iIndicator["库编码"]):
                        continue
                    iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="", agent=indicator_calculator_sa_agent)
                    indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                print(append_list(OutputList, f"衍生指标算法: {pformat(indicator_algorithm)}"))
            else:
                print(append_list(OutputList, f"======================== 系分生成: {iTask} ========================"))
                print(append_list(OutputList, f"不支持的任务: {iTask}"))
        self._Memory["indicator_list"] = indicator_list
        self._Memory["indicator_dict"] = indicator_dict
        self._Memory["sec_filter"] = sec_filter
        self._Memory["indicator_algorithm"] = indicator_algorithm
        return OutputList, {"task_list": task_list}


# 工具函数
##############################
@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutError("执行超时")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class SecurityError(Exception):
    pass


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



if __name__ == '__main__':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('smart_selector_agent_v*')

    # requirement = "我想提取固收+近1年年化收益超过0.02，且近1年最大回撤不超过50%的产品，开始时间为'2025-01-01'"
    user_input = input("你好，我是一个量化分析智能助手, 请告诉我你的量化分析需求（输入q退出）: ")
    while user_input:
        if user_input.lower() == 'q':
            break
        result = agent.run(input=user_input)
        print("\n处理结果:", result.to_dict()["output"])
        user_input = input(">>>")

    print("======================== 结束 ========================")





