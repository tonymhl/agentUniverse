# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/11/30 16:20
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: smart_selector_demo_v2.py

from sa_agent import validate_indicator_query, IndicatorQueryPrompt
from agentuniverse.base.util.logging.logging_util import LOGGER
from utils import *
from agentuniverse_ant_ext.connector.odps.universal_odps_operator import UniversalODPSOperator, Column, Partition


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
    indicator_args.pop("在指标库", None)
    indicator_name = indicator_args.get("指标名称")

    indicator_info = input(f"请告诉我关于指标 '{indicator_name}' 的描述和要求:\n>>>")
    rsp = agent.run(indicator_name=indicator_name, indicator_args=str(indicator_args), indicator_info=indicator_info,
                    indicator_external_info="")
    rsp = rsp.to_dict()
    return {"指标代码": indicator_id, "指标名称": indicator_name, "用户描述": indicator_info, "指标算法": rsp["output"]}


def generate_calculation_code(iQuery, indicator_algorithm):
    code_str = ""
    indicator_id = iQuery["指标代码"]
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
        NV_data=NV_data
    )
    # Extract and execute calculation code
    code_str = extract_code_from_output(res_calc.to_dict()['output'])
    LOGGER.info(f"Extracted calculation code:\n{code_str}")

    if not validate_calculation_code(code_str):
        LOGGER.error("Invalid calculation code generated")
        raise ValueError("Generated code failed validation")

    try:
        calculation_result = execute_calculation_code(code_str, NV_data)
        if calculation_result is None or calculation_result.empty:
            LOGGER.warn("No results found after calculation")
        else:
            LOGGER.info(f"calculation results:\n{calculation_result}")
    except Exception as e:
        LOGGER.error(f"Error during filter execution: {str(e)}")
        raise

    return code_str, calculation_result


if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    schedule_agent = AgentManager().get_instance_obj('schedule_agent')
    indicator_query_sa_agent = AgentManager().get_instance_obj('indicator_query_sa_agent')
    indicator_calculator_sa_agent = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
    filter_sa_agent = AgentManager().get_instance_obj('filter_sa_agent')
    # indicator_extraction_agent = AgentManager().get_instance_obj('indicator_extraction_agent')
    indicator_extraction_agent = AgentManager().get_instance_obj('indicator_nscode_extraction_agent')
    filter_indicator_agent = AgentManager().get_instance_obj('filter_indicator_agent')
    indicator_calculation_agent = AgentManager().get_instance_obj('indicator_calculation_agent')

    # 用户输入
    print("======================== 需求输入 ========================")
    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    # requirement = "我想提取固收+近1年年化收益率超过0.8，且近一年最大回撤不超过50%的产品"
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
    indicator_algorithm = {}
    while task_list:
        iTask = task_list.pop(0)
        if iTask == "指标提取":
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = indicator_query_sa_agent.run(requirement=requirement, indicator_list="年化超额收益, 正收益概率")
            indicator_list = get_indicator_query_rslt(rsp)

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
            if not all((iQuery.get("在指标库", False) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in
                       indicator_list):
                task_list = ["指标计算", iTask] + task_list
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")
            rsp = filter_sa_agent.run(requirement=requirement, indicator_list=indicator_list)
            sec_filter = get_filter_rslt(rsp)

            # Convert indicator data to DataFrames
            indicator_data_dict = convert_indicator_data_to_df(indicator_data)
            # 调用filter_indicator_agent进行指标筛选代码生成
            res_filter = filter_indicator_agent.run(
                requirement=requirement,
                indicator_list=indicator_list,
                indicator_data=indicator_data_dict,
                filter_condition=sec_filter
            )
            print((res_filter.to_dict()['output']))
            LOGGER.info(f"filter_indicator_agent产出代码: \n {(res_filter.to_dict()['output'])}")

            # 提取代码
            code_str = extract_code_from_output(res_filter.to_dict()['output'])
            LOGGER.info(f"Generated filter code:\n{code_str}")

            if not validate_filter_code(code_str):
                LOGGER.error("Invalid filter code generated")
                raise ValueError("Generated code failed validation")

            try:
                filtered_results = execute_filter_code(code_str, indicator_data_dict)
                if filtered_results is None or filtered_results.empty:
                    LOGGER.warn("No results found after filtering")
                else:
                    LOGGER.info(f"Filtered results:\n{filtered_results}")
            except Exception as e:
                LOGGER.error(f"Error during filter execution: {str(e)}")
                raise

        elif iTask == "指标计算":
            if all((iQuery.get("在指标库", False) or (iQuery["指标代码"] in indicator_algorithm)) for iQuery in
                   indicator_list):
                print("所有的指标已经在指标库中或者已经生成了算法, 不需要衍生计算!")
                continue
            print(f"\n======================== 系分生成: {iTask} ========================")
            for i, iQuery in enumerate(indicator_list):
                if iQuery["在指标库"]: continue
                iAlgorithm = get_indicator_calculator_rslt(iQuery, indicator_calculator_sa_agent)
                indicator_algorithm[iQuery["指标代码"]] = iAlgorithm
            print(f"indicator_algorithm={indicator_algorithm}")

            # 产出代码进行计算
            for i, iQuery in enumerate(indicator_list):
                if iQuery["在指标库"]: continue
                iAlgorithm = indicator_algorithm[iQuery["指标代码"]]
                LOGGER.info(f"indicator_algorithm[{iQuery['指标代码']}]={iAlgorithm}")
                try:
                    code_str, calculation_result = generate_calculation_code(iQuery, iAlgorithm)
                    LOGGER.info(f"Generated calculation code:\n{code_str}")
                    LOGGER.info(f"\n Calculation result:\n{calculation_result}")
                except Exception as e:
                    LOGGER.error(f"Error generating or executing calculation code: {str(e)}")
                    raise

        else:
            print(f"\n======================== 系分生成: {iTask} ========================")
            raise Exception(f"不支持的任务: {iTask}")

    print("===")


