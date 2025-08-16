# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/11/30 16:20
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: smart_selector_demo.py

from agentuniverse.base.util.logging.logging_util import LOGGER
from utils import *

if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    schedule_agent = AgentManager().get_instance_obj('schedule_agent')
    indicator_query_sa_agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
    filter_sa_agent = AgentManager().get_instance_obj('filter_sa_agent')
    indicator_extraction_agent = AgentManager().get_instance_obj('indicator_extraction_agent')
    filter_indicator_agent = AgentManager().get_instance_obj('filter_indicator_agent')
    indicator_calculation_agent = AgentManager().get_instance_obj('indicator_calculation_agent')

    # 用户输入
    print("======================== 需求输入 ========================")
    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    # requirement = "我想提取固收+近1年年化收益率超过0.8，且近一年最大回撤不超过50%的产品，随后进行“指标计算”"
    # 使用近一年的年化收益数据计算新的指标夏普比率，无风险利率取2%"
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
    while task_list:
        iTask = task_list.pop(0)
        if iTask == "指标提取":
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = indicator_query_sa_agent.run(requirement=requirement, indicator_list="")
            indicator_list = rsp.to_dict()["indicator_list"]
            print(f"indicator_list={indicator_list}")
            adjusted_query, all_filled = [], False
            while not all_filled:
                adjusted_query, all_filled = [], True
                for i, iQuery in enumerate(indicator_list):
                    for jKey, jVal in iQuery.items():
                        if jVal is None:
                            iQuery[jKey] = input(f"请确认指标 '{iQuery['指标名称']}' 的分项口径 '{jKey}': ")
                            if not iQuery[jKey]:
                                iQuery[jKey] = None
                                all_filled = False
                    iQuery["指标代码"] = f"Ind{i}"
                    adjusted_query.append(iQuery)
                indicator_list = adjusted_query
            for i, iQuery in enumerate(indicator_list): iQuery["指标代码"] = f"Ind{i}"
            print(f"indicator_list={indicator_list}")

            indicator_data = []
            for i, iQuery in enumerate(indicator_list):
                res = indicator_extraction_agent.run(input=iQuery)
                data = res.to_dict()["data"]
                LOGGER.info(f"指标提取结果{i}:{data}")
                if data is not None:
                    LOGGER.info(f"指标提取结果{i}:{data}")
                    indicator_data.append(data)
                else:
                    LOGGER.warn(f"指标提取结果{i}为空或无法解析")

        elif iTask == "标的筛选":
            if not all(iQuery.get("在指标库", False) for iQuery in indicator_list):
                task_list = ["指标计算", iTask] + task_list
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = filter_sa_agent.run(requirement=requirement, indicator_list=indicator_list)
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

            # Convert indicator data to DataFrames
            indicator_data_dict = convert_indicator_data_to_df(indicator_data)
            # 调用filter_indicator_agent进行指标筛选代码生成
            res_filter = filter_indicator_agent.run(requirement=requirement,
                                                    indicator_list=indicator_list,
                                                    indicator_data=indicator_data_dict,
                                                    filter_condition=adjusted_filter)
            print((res_filter.to_dict()['output']))
            LOGGER.info(f"filter_indicator_agent产出代码: \n {(res_filter.to_dict()['output'])}")

            # 提取代码
            code_str = extract_code_from_output(res_filter.to_dict()['output'])
            LOGGER.info(f"Extracted filter code:\n{code_str}")

            try:
                filtered_results = execute_filter_code(code_str, indicator_data_dict)
                LOGGER.info(f"Filtered results 代码执行结果:\n{filtered_results}")
            except Exception as e:
                LOGGER.error(f"Failed to execute filter code: {str(e)}")

        elif iTask == "指标计算":
            if all(iQuery.get("在指标库", False) for iQuery in indicator_list):
                print("所有的指标已经在指标库中, 不需要衍生计算!")
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")

            # Convert indicator data to DataFrames
            indicator_data_dict = convert_indicator_data_to_df(indicator_data)

            # Call indicator calculation agent
            res_calc = indicator_calculation_agent.run(
                requirement=requirement,
                indicator_list=indicator_list,
                indicator_data=indicator_data_dict
            )

            print(res_calc.to_dict()['output'])
            LOGGER.info(f"indicator_calculation_agent产出代码: \n {res_calc.to_dict()['output']}")

            # Extract and execute calculation code
            code_str = extract_code_from_output(res_calc.to_dict()['output'])
            LOGGER.info(f"Extracted calculation code:\n{code_str}")

            try:
                calculated_results = execute_calculation_code(code_str, indicator_data_dict)
                LOGGER.info(f"Calculation results:\n{calculated_results}")
                indicator_data.append({
                    "指标代码": f"Ind{len(indicator_data)}",
                    "数据": calculated_results.to_dict('records')
                })

            except Exception as e:
                LOGGER.error(f"Failed to execute calculation code: {str(e)}")
            raise NotImplementedError(f"未实现的任务: {iTask}")
        else:
            print(f"\n======================== 系分生成: {iTask} ========================")
            raise Exception(f"不支持的任务: {iTask}")

    print("===")


