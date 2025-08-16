#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/22 17:55
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : smart_selector_app.py
# @Software: PyCharm

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import json
from pathlib import Path
from pprint import pformat
from time import sleep
import traceback
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager

# Set display options for pandas
pd.set_option('display.max_columns', None)

# Get script directory and project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

# Import functions and utilities from the original script
from sample_standard_app.app.core.agent.asset_research.smart_selector_demo_v3 import *
from sample_standard_app.app.core.agent.asset_research.utils import *

# Import frontend configurations and utilities
from sample_standard_app.app.frontend.frontend_config import (
    PAGE_CONFIG,
    APP_CONFIG,
    UI_CONFIG,
    EXAMPLES,
    STATIC_DIR
)

# Define constants
MAX_RETRIES = 3

# =========================
# Initialize Agents and Systems
# =========================

# Global variable to store agent instances
agents = {
    'intent_agent': None,
    'schedule_agent': None,
    'indicator_query_sa_agent': None,
    'filter_sa_agent': None,
    'indicator_calculator_sa_agent': None,
    'indicator_extraction_agent': None,
    'filter_indicator_agent': None,
    'indicator_calculation_agent': None,
    'free_answer_agent': None,
    'quant_consulting_agent': None,
    'indicator_consulting_agent': None,
    'indicator_modification_agent': None,
    'indicator_adding_agent': None,
    'filter_modification_agent': None,
    'indicator_algorithm_modification_agent': None,
    'debug_agent': None,
    'eval_agent': None
}


def initialize_agents():
    """初始化所有需要的agents"""
    if not any(agents.values()):  # 只在所有agent都未初始化时执行
        try:
            # 获取当前文件的绝对路径
            current_file = Path(__file__).resolve()
            # 获取项目根目录
            project_root = current_file.parent.parent.parent.parent
            # 设置配置文件路径
            QE_ENV = os.environ.get('QE_ENV', 'dev')
            if QE_ENV == 'prd':
                config_path = project_root / 'sample_standard_app/config/config.toml'
            else:
                config_path = project_root / 'sample_standard_app/config/config_dev.toml'

            from agentuniverse.base.util.env_util import get_from_env
            USE_OB_PROXY = get_from_env('USE_OB_PROXY')
            print(f'USE_OB_PROXY={USE_OB_PROXY}')
            OB_PROXY_URL = get_from_env('OB_PROXY_URL')
            print(f'OB_PROXY_URL={OB_PROXY_URL}')

            try:
                print(f'config_path={config_path}')
                schedule_agent = AgentManager().get_instance_obj('schedule_agent')
                if not schedule_agent:
                    AgentUniverse().start(config_path=str(config_path))
            except ValueError as e:
                # 处理配置未设置的情况
                import traceback
                traceback.print_exc()
                print(f"Error: {e}. Cannot retrieve schedule_agent due to unconfigured AppConfiger.")
                AgentUniverse().start(config_path=str(config_path))
                pass

            # 初始化所有需要的agents
            agents['intent_agent'] = AgentManager().get_instance_obj(
                'user_intent_parse_agent')  # Initialize intent_agent
            agents['schedule_agent'] = AgentManager().get_instance_obj('schedule_agent')
            agents['indicator_query_sa_agent'] = AgentManager().get_instance_obj('indicator_query_sa_agent')
            agents['filter_sa_agent'] = AgentManager().get_instance_obj('filter_sa_agent')
            agents['indicator_calculator_sa_agent'] = AgentManager().get_instance_obj('indicator_calculator_sa_agent')
            agents['indicator_extraction_agent'] = AgentManager().get_instance_obj('indicator_nscode_extraction_agent')
            agents['filter_indicator_agent'] = AgentManager().get_instance_obj('filter_indicator_agent')
            agents['indicator_calculation_agent'] = AgentManager().get_instance_obj('indicator_calculation_agent')
            agents['free_answer_agent'] = AgentManager().get_instance_obj('free_answer_agent')
            agents['quant_consulting_agent'] = AgentManager().get_instance_obj('quant_consulting_agent')
            agents['indicator_consulting_agent'] = AgentManager().get_instance_obj('indicator_consulting_agent')
            agents['indicator_modification_agent'] = AgentManager().get_instance_obj('indicator_modification_agent')
            agents['indicator_adding_agent'] = AgentManager().get_instance_obj('indicator_adding_agent')
            agents['filter_modification_agent'] = AgentManager().get_instance_obj('filter_modification_agent')
            agents['indicator_algorithm_modification_agent'] = AgentManager().get_instance_obj(
                'indicator_algorithm_modification_agent')
            agents['debug_agent'] = AgentManager().get_instance_obj('code_debug_agent')
            agents['eval_agent'] = AgentManager().get_instance_obj('code_evaluation_agent')

            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            st.error(f"Agent初始化失败: {str(e)}")
            return False
    return True


# =========================
# Session State Initialization
# =========================
def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'messages': [],
        'retry_count': 0,
        'max_retries': MAX_RETRIES,
        'current_task': None,
        'task_list': [],
        'indicator_list': [],
        'indicator_dict': {},
        'indicator_algorithm': {},
        'sec_filter': {},
        'indicator_data': [],
        'filtered_data': None,
        'execution_results': {},
        'user_input': "",
        'task_stage': "idle",
        'awaiting_modification': False
        # idle, scheduling, awaiting_confirmation, indicator_extraction, indicator_filter, indicator_calculation, completed, error_scheduling, etc.
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =========================
# Messaging Functions
# =========================
def add_message(role: str, content: str, display_as: str = None):
    """添加消息到对话历史并立即显示"""
    # 如果 display_as 是 DataFrame，转换为可序列化的格式并保存元数据
    if isinstance(display_as, pd.DataFrame):
        message = {
            "role": role,
            "content": content,
            "display_type": "dataframe",  # 添加类型标记
            "display_as": {
                "data": display_as.to_dict(),  # 数据
                "metadata": {
                    "index": display_as.index.to_list(),
                    "columns": display_as.columns.to_list(),
                    "dtypes": {col: str(dtype) for col, dtype in display_as.dtypes.items()}
                }
            }
        }
    else:
        message = {
            "role": role,
            "content": content,
            "display_type": "text",  # 添加类型标记
            "display_as": display_as or content
        }
    st.session_state.messages.append(message)
    display_chat_message(message)


def display_chat_message(message):
    """显示聊天消息"""
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        with st.chat_message("assistant"):
            # 处理 DataFrame 展示
            if message["display_type"] == "dataframe":
                try:
                    # 从存储的字典重建 DataFrame
                    df_data = message["display_as"]["data"]
                    df_metadata = message["display_as"]["metadata"]

                    # 重建 DataFrame
                    df = pd.DataFrame.from_dict(df_data)

                    # 恢复列的数据类型
                    for col, dtype_str in df_metadata["dtypes"].items():
                        try:
                            if "float" in dtype_str:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                            elif "int" in dtype_str:
                                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')  # 使用可空整数类型
                        except Exception:
                            continue  # 如果转换失败，保持原样

                    # 使用容器确保稳定展示
                    with st.container():
                        # 使用 st.dataframe 的高级特性来提供更稳定的展示
                        st.dataframe(
                            df,
                            hide_index=True,
                            use_container_width=False,  # 改为 False，不撑满屏幕
                            width=1200,  # 设置固定宽度
                            column_config={
                                col: st.column_config.NumberColumn(
                                    col,
                                    format="%.4f",
                                    width="medium",  # 设置列宽
                                ) for col in df.select_dtypes(include=['float64']).columns
                            }
                        )

                        # 添加数据统计信息容器
                        with st.expander("查看数据统计信息", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**行数:** {len(df)}")
                            with col2:
                                st.markdown(f"**列数:** {len(df.columns)}")

                            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                            if not numeric_cols.empty:
                                st.markdown("**数值列统计:**")
                                st.dataframe(
                                    df[numeric_cols].describe(),
                                    use_container_width=True
                                )

                        # 添加下载按钮
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                        data_hash = hash(str(df.shape))
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 下载数据",
                            data=csv,
                            file_name=f"data_{timestamp}.csv",
                            mime="text/csv",
                            key=f"download_btn_{timestamp}_{data_hash}",
                            help="下载数据为CSV格式"
                        )
                except Exception as e:
                    st.error(f"DataFrame 显示错误: {str(e)}")
                    st.markdown(message["content"])

            # 处理其他展示内容
            elif message["display_type"] == "text":
                if message["display_as"] != message["content"]:
                    st.markdown(message["display_as"])
                if message["content"]:
                    st.markdown(message["content"])


# =========================
# Progress Display Functions
# =========================
def display_progress(title, steps, current_step):
    """显示进度指示器"""
    with st.container():
        st.markdown(f"### {title}")
        progress_bar = st.progress(0)
        progress = current_step / len(steps)
        progress_bar.progress(progress)

        for i, step in enumerate(steps):
            status_class = "active" if i == current_step else ""
            st.markdown(
                f"""
                <div class="status-indicator {status_class}">
                    {'✓' if i < current_step else '⚪' if i > current_step else '▶'} {step}
                </div>
                """,
                unsafe_allow_html=True
            )


def show_loading_message(message):
    """显示加载消息"""
    return st.markdown(f"""
        <div class="loading-animation">
            <p>{message}</p>
        </div>
    """, unsafe_allow_html=True)


def get_alternative_indicator(indicator):
    indicator_knowledge = KnowledgeManager().get_instance_obj("NL2Indicator_knowledge")
    alternative_indicators = {}
    alternative_num = 3
    MetaData = {}
    if indicator["资产类型"]:
        MetaData["fap_asset_type"] = indicator["资产类型"]
    iAlternativeIndicators = indicator_knowledge.query_knowledge(query_str=indicator["指标名称"],
                                                                 similarity_top_k=alternative_num)
    return [{"库编码": iDoc.id, "指标名称": iDoc.metadata["chi_name"], "元信息": iDoc.metadata} for iDoc in
            iAlternativeIndicators]


# =========================
# Task Handling Functions
# =========================
def handle_task_scheduling(user_input: str):
    """处理任务编排和系分生成。"""
    add_message("assistant", "正在进行任务编排和系分生成...")
    st.session_state.task_stage = "scheduling"

    try:
        # 任务编排
        rsp = agents['schedule_agent'].run(requirement=user_input)
        task_list = rsp.to_dict().get("output", "")

        if task_list == "非法需求":
            add_message("assistant", "您输入的并非有效的量化分析需求，请修改后重新输入。")
            st.session_state.task_stage = "idle"
            return False

        add_message("assistant", f"任务编排完成，任务列表为：\n{task_list}")
        st.session_state.task_list = [iTask.strip() for iTask in task_list.split(">")]
        analysis_results = []

        # 初始化字典
        st.session_state.indicator_algorithm = {}
        st.session_state.indicator_dict = {}
        alternative_indicators = {}

        # 系分生成
        for iTask in st.session_state.task_list.copy():
            if iTask == "指标提取":
                rsp = agents['indicator_query_sa_agent'].run(requirement=user_input,
                                                             indicator_list="年化超额收益, 正收益概率",
                                                             )
                indicator_list = rsp.to_dict().get("indicator_list", [])
                for i, query in enumerate(indicator_list):
                    query = set_indicator_default(query)
                    query["指标代码"] = f"Ind{i}"
                    st.session_state.indicator_list.append(query)
                    st.session_state.indicator_dict[query["指标代码"]] = query
                analysis_results.append(("指标列表", st.session_state.indicator_list))

            elif iTask == "标的筛选":
                rsp = agents['filter_sa_agent'].run(requirement=user_input,
                                                    indicator_list=st.session_state.indicator_list,
                                                    )
                sec_filter = rsp.to_dict().get("filter", [{}])[0]
                sec_filter = set_filter_default(sec_filter, indicator_list=st.session_state.indicator_list)
                st.session_state.sec_filter = sec_filter
                analysis_results.append(("筛选条件", sec_filter))

            elif iTask == "指标计算":
                for query in st.session_state.indicator_list:
                    if query.get("库编码") is None:
                        rsp = agents['indicator_calculator_sa_agent'].run(input=query, user_info="")
                        algorithm = rsp.to_dict().get("output", "")
                        st.session_state.indicator_algorithm[query["指标代码"]] = algorithm
                analysis_results.append(("衍生指标算法", st.session_state.indicator_algorithm))

            elif iTask == "指标口径修改":
                rsp = agents['indicator_modification_agent'].run(input=user_input,
                                                                 indicator_list=st.session_state.indicator_list,
                                                                 )
                rsp = rsp.to_dict()
                adjusted_indicator_list = rsp.get("indicator_list", [])
                add_message("assistant", f"调整后的指标列表: {pformat(adjusted_indicator_list)}")
                adjusted_indicator_algorithm = {}
                for i, iIndicator in enumerate(adjusted_indicator_list):
                    if (iIndicator != st.session_state.indicator_dict.get(iIndicator["指标代码"])) and (
                            not iIndicator["在指标库"]):
                        iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="",
                                                                   agent=agents['indicator_calculator_sa_agent'])
                        adjusted_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                    st.session_state.indicator_dict[iIndicator["指标代码"]] = iIndicator
                st.session_state.indicator_list = adjusted_indicator_list
                if adjusted_indicator_algorithm:
                    add_message("assistant", f"调整后的衍生指标算法: {pformat(adjusted_indicator_algorithm)}")
                    st.session_state.indicator_algorithm.update(adjusted_indicator_algorithm)

                # 动态添加"指标计算"任务
                if any(not ind.get("在指标库", False) and ind["指标代码"] not in st.session_state.indicator_algorithm
                       for ind in st.session_state.indicator_list):
                    if "指标计算" not in st.session_state.task_list:
                        st.session_state.task_list.append("指标计算")
                        add_message("assistant", "检测到有指标不在指标库中，已添加“指标计算”任务。")

            elif iTask == "新增指标":
                rsp = agents['indicator_adding_agent'].run(input=user_input,
                                                           indicator_list=st.session_state.indicator_list,
                                                           lib_indicator_list="年化超额收益, 正收益概率",
                                                           )
                rsp = rsp.to_dict()
                added_indicator_list = rsp.get("indicator_list", [])
                added_indicator_algorithm = {}
                for i, iIndicator in enumerate(added_indicator_list):
                    iIndicator = set_indicator_default(iIndicator, st.session_state.indicator_list)
                    iIndicator["指标代码"] = f"Ind{len(st.session_state.indicator_list) + i}"
                    st.session_state.indicator_list.append(iIndicator)
                    st.session_state.indicator_dict[iIndicator["指标代码"]] = iIndicator
                    if not iIndicator["在指标库"]:
                        iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="",
                                                                   agent=agents['indicator_calculator_sa_agent'])
                        added_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                add_message("assistant", f"新增后的指标列表: {pformat(st.session_state.indicator_list)}")
                if added_indicator_algorithm:
                    add_message("assistant", f"新增的衍生指标算法: {pformat(added_indicator_algorithm)}")
                    st.session_state.indicator_algorithm.update(added_indicator_algorithm)

                # 动态添加"指标计算"任务
                if any(not ind.get("在指标库", False) and ind["指标代码"] not in st.session_state.indicator_algorithm
                       for ind in st.session_state.indicator_list):
                    if "指标计算" not in st.session_state.task_list:
                        st.session_state.task_list.append("指标计算")
                        add_message("assistant", "检测到有指标不在指标库中，已添加“指标计算”任务。")

            else:
                add_message("assistant", f"不支持的任务类型: {iTask}")

        # 动态检查并添加"指标计算"任务
        if any(not ind.get("在指标库", False) and ind["指标代码"] not in st.session_state.indicator_algorithm for ind in
               st.session_state.indicator_list):
            if "指标计算" not in st.session_state.task_list:
                st.session_state.task_list.append("指标计算")
                add_message("assistant", "检测到有指标不在指标库中，已添加“指标计算”任务。")

        # 显示任务编排和系统分析结果
        display_text = ["**任务编排结果：**\n"]
        display_text.extend([f"- {task}" for task in st.session_state.task_list])
        display_text.append("\n")

        for title, content in analysis_results:
            display_text.append(f"\n**{title}：**\n```json\n{json.dumps(content, indent=2, ensure_ascii=False)}\n```")

        add_message(
            "assistant",
            "请确认系分是否正确，如需修改请直接提出修改意见，确认无误请输入'yes'或'确认'。",
            "\n".join(display_text)
        )
        st.session_state.task_stage = "awaiting_confirmation"
        return True

    except Exception as e:
        add_message("assistant", f"任务编排过程中出错：{str(e)}\n是否重试？", "⚠️ **任务编排出错**\n\n是否重试？")
        st.session_state.task_stage = "error_scheduling"
        return False


def handle_system_analysis_modification(user_input: str):
    """处理系分修改请求。"""
    add_message("assistant", "正在处理系分修改请求...")
    st.session_state.task_stage = "modifying_analysis"

    try:
        rsp = agents['free_answer_agent'].run(
            input=user_input,
            context={
                "task_list": st.session_state.task_list,
                "indicator_list": st.session_state.indicator_list,
                "indicator_algorithm": st.session_state.indicator_algorithm,
                "sec_filter": st.session_state.sec_filter
            },
        )
        modified_input = rsp.to_dict().get("output", "")
        if not modified_input:
            add_message("assistant", "❓ **无法理解修改请求**\n\n请重新输入。")
            return False

        # 重置任务状态
        st.session_state.task_list = []
        st.session_state.indicator_list = []
        st.session_state.indicator_algorithm = {}
        st.session_state.sec_filter = {}
        st.session_state.indicator_data = []
        st.session_state.filtered_data = None
        st.session_state.execution_results = {}
        st.session_state.retry_count = 0
        st.session_state.task_stage = "idle"

        # 重新进行任务编排
        if handle_task_scheduling(modified_input):
            return True

    except Exception as e:
        add_message("assistant", "⚠️ **系分修改出错**\n\n是否重试？", f"系分修改过程中出错：{str(e)}\n")
        st.session_state.task_stage = "error_modifying_analysis"
        return False


def handle_indicator_extraction():
    """处理指标提取任务"""
    add_message("assistant", "开始执行指标提取任务...")
    st.session_state.indicator_data = []
    st.session_state.task_stage = "indicator_extraction"

    try:
        steps = ["映射参数", "从META提取指标", "验证结果", "完成"]
        for i, query in enumerate(st.session_state.indicator_list):
            display_progress(
                f"正在提取指标 ({i + 1}/{len(st.session_state.indicator_list)})",
                steps,
                1
            )

            loading_placeholder = st.empty()
            with loading_placeholder:
                show_loading_message(f"正在提取指标: {query['指标名称']}...")

            error_info = ''
            rsp = agents['indicator_extraction_agent'].run(input=query, error_info=error_info)
            data = rsp.to_dict().get("data", None)

            if data is not None:
                st.session_state.indicator_data.append(data)
                # 修改数据展示方式
                df_display = data.get('数据', pd.DataFrame())
                add_message(
                    "assistant",
                    f"指标 **{query['指标名称']}** 提取成功",
                    df_display
                )
            else:
                error_msg = f"指标 {query['指标名称']} 提取结果为空"
                add_message("assistant", error_msg)
                raise ValueError(error_msg)

            loading_placeholder.empty()
            display_progress(
                f"正在提取指标 ({i + 1}/{len(st.session_state.indicator_list)})",
                steps,
                3
            )

        add_message(
            "assistant",
            "所有指标提取完成！是否继续执行标的筛选？(输入'yes'或'确认'继续)",
            "**✅ 指标提取任务完成**\n\n是否继续执行标的筛选？"
        )
        st.session_state.task_stage = "awaiting_execution_confirmation"
        st.session_state.retry_count = 0
        return True

    except Exception as e:
        st.session_state.retry_count += 1
        error_msg = f"提取失败 (尝试 {st.session_state.retry_count}/{st.session_state.max_retries}): {str(e)}"
        add_message("assistant", error_msg)

        if st.session_state.retry_count < st.session_state.max_retries:
            add_message("assistant", "🔄 **优化提取逻辑**\n\n尝试使用错误信息优化提取逻辑...")
            sleep(1)  # 给用户时间查看错误信息
            return handle_indicator_extraction()  # 递归重试
        else:
            add_message(
                "assistant",
                "⚠️ **达到最大重试次数**\n\n是否继续尝试？(输入'retry'重试；输入'继续'以跳过此步骤)"
            )
            st.session_state.retry_count = 0

    return False


def handle_indicator_filter():
    """处理指标筛选任务"""
    steps = ["准备数据", "生成筛选逻辑", "执行筛选", "验证结果"]
    current_step = 0
    error_info = ''

    add_message("assistant", "开始执行标的筛选任务...")
    st.session_state.task_stage = "indicator_filter"

    try:
        display_progress("指标筛选", steps, current_step)

        # 检查依赖
        if not st.session_state.indicator_data:
            add_message(
                "assistant",
                "⚠️无法执行标的筛选: **缺少指标数据**\n\n请先完成指标提取。(输入'继续'则跳过该步骤继续执行后续任务)"
            )
            return False

        # 准备筛选数据
        with st.spinner("正在准备筛选数据..."):
            indicator_data = convert_indicator_data_to_df(st.session_state.indicator_data)
            current_step = 1
            display_progress("指标筛选", steps, current_step)

        # 生成筛选代码
        with st.spinner("正在生成筛选逻辑..."):
            code_str = generate_code_for_indicator_filter(
                requirement=st.session_state.user_input,
                indicator_list=st.session_state.indicator_list,
                indicator_data=indicator_data,
                sec_filter=st.session_state.sec_filter,
                error_info=error_info
            )
            current_step = 2
            display_progress("指标筛选", steps, current_step)

        # 修改代码展示方式
        add_message("assistant", "筛选逻辑生成完毕：\n```python\n" + code_str + "\n```")

        # 执行校验及筛选
        add_message("assistant", "开始进入筛选执行模块...")
        filtered_data = execute_task_with_verification(
            "filter",
            code_str,
            indicator_data,
            st.session_state.sec_filter,
            kwargs={
                "user_input": st.session_state.user_input,
                "indicator_list": st.session_state.indicator_list,
                "indicator_data": indicator_data,
                "sec_filter": st.session_state.sec_filter,
                "error_info": error_info
            }
        )

        if filtered_data is not None:
            st.session_state.filtered_data = filtered_data
            # 更新状态
            add_message(
                "assistant",
                f"""**✅ 筛选完成**\n- 符合条件的数据数量：{len(filtered_data)}""",
                filtered_data
            )
            st.session_state.task_stage = "awaiting_next_task_confirmation"
            add_message(
                "assistant",
                "是否继续执行指标计算？(输入'yes'或'确认'继续)",
                "**✅ 标的筛选任务完成**\n\n是否继续执行指标计算？"
            )
            st.session_state.retry_count = 0
            return True
        else:
            add_message(
                "assistant",
                "**❌ 筛选结果为空**\n\n是否需要调整筛选条件？"
            )
            return False

    except Exception as e:
        st.session_state.retry_count += 1
        error_msg = f"筛选失败 (尝试 {st.session_state.retry_count}/{st.session_state.max_retries}): {str(e)}"
        add_message("assistant", error_msg)

        if st.session_state.retry_count < st.session_state.max_retries:
            add_message("assistant", "🔄 **优化筛选逻辑**\n\n尝试重新筛选...")
            sleep(1)
            return handle_indicator_filter()  # 递归重试
        else:
            add_message(
                "assistant",
                "⚠️ **达到最大重试次数**\n\n是否继续尝试筛选？(输入'retry'重试；输入'继续'以跳过此步骤)"
            )
            st.session_state.retry_count = 0

    return False


def handle_indicator_calculation():
    """处理指标计算任务。"""
    add_message("assistant", "开始执行指标计算任务...")
    st.session_state.task_stage = "indicator_calculation"

    try:
        for i, query in enumerate(st.session_state.indicator_list):
            if query.get("库编码"):
                pass
                # continue  # 跳过已在指标库中的指标

            add_message("assistant", f"开始计算指标 **{query['指标名称']}**..., 首先获取净值数据...")
            loading_placeholder = st.empty()
            with loading_placeholder:
                show_loading_message(f"正在获取净值数据: {query['资产类型']}...")

            error_info = ''
            iAlgorithm = st.session_state.indicator_algorithm.get(query["指标代码"], "")

            calculation_result = None
            retry_count = 0

            while calculation_result is None and retry_count < MAX_RETRIES:
                try:
                    code_str, NV_data = generate_calculation_code(
                        iQuery=query,
                        indicator_algorithm=iAlgorithm,
                        error_info=error_info
                    )
                    # 净值数据展示
                    add_message("assistant", f"""**✅ 净值获取完成**\n- 数据量：{len(NV_data)} \n""", NV_data)
                    # 代码展示
                    add_message("assistant", f"计算逻辑生成完毕：\n```python\n{code_str}\n```")

                    # 执行校验及计算
                    calculation_result = execute_task_with_verification(
                        "calculation",
                        code_str,
                        NV_data,
                        iAlgorithm,
                        kwargs={
                            "iQuery": query,
                            "iAlgorithm": iAlgorithm,
                            'error_info': error_info
                        }
                    )

                    if calculation_result is not None:
                        st.session_state.execution_results[f'calculation_{query["指标代码"]}'] = calculation_result
                        add_message(
                            "assistant",
                            f"指标 **{query['指标名称']}** 计算成功。",
                            calculation_result
                        )

                except Exception as e:
                    retry_count += 1
                    add_message("assistant", f"计算失败 (尝试 {retry_count}/{MAX_RETRIES}): {str(e)}")

                    if retry_count < MAX_RETRIES:
                        add_message("assistant", "尝试使用错误信息优化计算代码...",
                                    "🔄 **优化计算代码**\n\n尝试重新计算...")
                        res = handle_code_generation_error(
                            e,
                            agents['indicator_calculation_agent'],
                            iQuery=query,
                            indicator_algorithm=iAlgorithm,
                        )
                        if res is not None:
                            continue  # 重新生成代码
                    else:
                        add_message("assistant", f"已达到最大重试次数，跳过指标 **{query['指标名称']}** 的计算。")
                        break  # 跳过该指标的计算

        add_message("assistant", "🎉 **任务完成**\n\n所有指标计算完成。")
        st.session_state.task_stage = "completed"
        return True

    except Exception as e:
        add_message("assistant", f"⚠️ **指标计算出错**：{str(e)}\n\n是否重试？")
        st.session_state.task_stage = "error_indicator_calculation"
        return False


def handle_code_generation_error(error: Exception, agent, **kwargs):
    """处理代码生成错误，使用错误信息优化代码生成"""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    }

    # 将错误信息添加到 agent 输入中
    kwargs['error_info'] = error_info

    # 重新生成代码
    try:
        res = agent.run(**kwargs)
        return res
    except Exception as e:
        add_message("assistant", f"❌ **代码再生成失败** :\n {str(e)} \n请检查错误原因。")
        return None


def execute_task_with_verification(task_type, code_str, data, task, kwargs):
    """执行任务并进行验证"""
    # 代码调试阶段
    debug_agent = agents['debug_agent']
    eval_agent = agents['eval_agent']

    add_message("assistant", "正在进行代码调试...")
    debug_result = debug_agent.run(
        code_str=code_str,
        indicator_data=data,
        task=task,
    )
    debug_output = debug_result.to_dict().get('output', True)
    if not debug_output:
        add_message("assistant", "⚠️ 代码调试未通过，正在重新生成...\n```python\n" + code_str + "\n```")
        return None
    else:
        add_message("assistant", "✅ 代码调试通过.", debug_output)

    # 执行代码
    try:
        add_message("assistant", "正在执行代码...\n```python\n" + code_str + "\n```")
        if task_type == "filter":
            result = execute_filter_code(code_str, data)
        elif task_type == "calculation":
            result = execute_calculation_code(code_str, data)
        else:
            raise ValueError(f"未知的任务类型: {task_type}")

        # 修改结果展示方式
        if isinstance(result, pd.DataFrame):
            add_message(
                "assistant",
                "执行结果如下：",
                result
            )
        else:
            add_message("assistant", f"执行结果: {result}")

    except Exception as e:
        error_msg = f"代码执行失败: {str(e)}"
        add_message("assistant", error_msg)

        # 是否重试
        add_message(
            "assistant",
            "⚠️ **执行失败**\n\n是否重试？(输入'retry'重试)"
        )
        return None

    # 评估结果
    add_message("assistant", "正在评估执行结果...")
    eval_result = eval_agent.run(
        code=code_str,
        indicator_data=data,
        result=result,
        task=task,
    )

    eval_output = eval_result.to_dict().get('output', "")

    if not eval_output:
        add_message(
            "assistant",
            "⚠️ **评估未通过**\n\n是否重新生成？(输入'retry'重试)"
        )
        return None
    else:
        add_message(
            "assistant",
            f"✅ **评估通过**\n\n{eval_output}"
        )

    return result


def display_welcome_page():
    """显示欢迎页面"""
    # 设置页面配置
    st.set_page_config(**PAGE_CONFIG)

    # 加载自定义CSS
    with open(STATIC_DIR / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # 欢迎页面内容
    st.markdown("""
        <div class="welcome-container">
            <div class="welcome-header">
                <h1>🤖 智能量化分析助手</h1>
                <p>基于AI的智能化量化分析工具，助您快速完成数据分析任务</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 示例查询部分
    st.markdown("### 💡 快速开始")
    st.markdown("选择以下示例或输入您的自定义需求：")

    # 使用两列布局展示示例
    col1, col2 = st.columns(2)
    for i, example in enumerate(EXAMPLES):
        with [col1, col2][i % 2]:
            st.markdown(f"""
                <div class="example-card">
                    <h4>{example['icon']} {example['title']}</h4>
                    <p>{example['description']}</p>
                    <code>{example['query']}</code>
                </div>
            """, unsafe_allow_html=True)


# =========================
# Main Application
# =========================
def main():
    """主应用程序"""
    if not initialize_agents():
        st.error("系统初始化失败，请检查配置并重试。")
        return

    init_session_state()

    print(f'st.session_state={st.session_state}')

    # 显示欢迎页面
    if not st.session_state.messages:
        display_welcome_page()

    # 显示历史消息
    for message in st.session_state.messages:
        display_chat_message(message)

    # 用户输入
    if prompt := st.chat_input("请输入您的分析需求...", key="chat_input"):
        add_message("user", prompt)
        st.session_state.user_input = prompt  # 保存用户输入

        if st.session_state.task_stage == "idle":
            # 初始阶段，通过intent_agent解析意图
            rsp = agents['intent_agent'].run(
                input=prompt,
                filter=st.session_state.sec_filter,
                indicator_list=st.session_state.indicator_list,
                indicator_algorithm=st.session_state.indicator_algorithm,
                indicator_modification="",
                indicator_adding="",
                filter_modification="",
                indicator_algorithm_modification="",
            )
            rsp = rsp.to_dict()
            intent_list = [intent.strip() for intent in rsp.get("output", "").split(",")]
            if ("筛选条件修改" in intent_list) and ("新增指标" not in intent_list):
                intent_list.insert(intent_list.index("筛选条件修改"), "新增指标")
            add_message("assistant", f"意图识别中: 用户意图: {intent_list}")

            for user_intent in intent_list:
                if user_intent == "量化知识咨询":
                    rsp = agents['quant_consulting_agent'].run(input=prompt, quant_external_info="")
                    rsp = rsp.to_dict()
                    add_message("assistant", pformat(rsp.get("output", "")))

                elif user_intent == "指标信息咨询":
                    rsp = agents['indicator_consulting_agent'].run(input=prompt, indicator_external_info="",
                                                                   indicator_internal_info="")
                    rsp = rsp.to_dict()
                    add_message("assistant", pformat(rsp.get("output", "")))

                elif user_intent == "指标口径修改":
                    rsp = agents['indicator_modification_agent'].run(input=prompt,
                                                                     indicator_list=st.session_state.indicator_list
                                                                     )
                    rsp = rsp.to_dict()
                    adjusted_indicator_list = rsp.get("indicator_list", [])
                    add_message("assistant", f"调整后的指标列表: {pformat(adjusted_indicator_list)}")
                    adjusted_indicator_algorithm = {}
                    for i, iIndicator in enumerate(adjusted_indicator_list):
                        if (iIndicator != st.session_state.indicator_dict.get(iIndicator["指标代码"], {})) and (
                        not iIndicator.get("在指标库", False)):
                            iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="",
                                                                       agent=agents['indicator_calculator_sa_agent'])
                            adjusted_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                        st.session_state.indicator_dict[iIndicator["指标代码"]] = iIndicator
                    st.session_state.indicator_list = adjusted_indicator_list
                    if adjusted_indicator_algorithm:
                        add_message("assistant", f"调整后的衍生指标算法: {pformat(adjusted_indicator_algorithm)}")
                        st.session_state.indicator_algorithm.update(adjusted_indicator_algorithm)

                elif user_intent == "新增指标":
                    rsp = agents['indicator_adding_agent'].run(input=prompt,
                                                               indicator_list=st.session_state.indicator_list,
                                                               lib_indicator_list="年化超额收益, 正收益概率",
                                                               )
                    rsp = rsp.to_dict()
                    added_indicator_list = rsp.get("indicator_list", [])
                    added_indicator_algorithm = {}
                    for i, iIndicator in enumerate(added_indicator_list):
                        iIndicator = set_indicator_default(iIndicator, st.session_state.indicator_list)
                        iIndicator["指标代码"] = f"Ind{len(st.session_state.indicator_list) + i}"
                        st.session_state.indicator_list.append(iIndicator)
                        st.session_state.indicator_dict[iIndicator["指标代码"]] = iIndicator
                        if not iIndicator.get("在指标库", False):
                            iAlgorithm = gen_indicator_calculator_rslt(iIndicator, user_info="",
                                                                       agent=agents['indicator_calculator_sa_agent'])
                            added_indicator_algorithm[iIndicator["指标代码"]] = iAlgorithm
                    add_message("assistant", f"新增后的指标列表: {pformat(st.session_state.indicator_list)}")
                    if added_indicator_algorithm:
                        add_message("assistant", f"新增的衍生指标算法: {pformat(added_indicator_algorithm)}")
                        st.session_state.indicator_algorithm.update(added_indicator_algorithm)

                elif user_intent == "筛选条件修改":
                    rsp = agents['filter_modification_agent'].run(input=prompt,
                                                                  indicator_list=st.session_state.indicator_list,
                                                                  filter=st.session_state.sec_filter,
                                                                  )
                    rsp = rsp.to_dict()
                    sec_filter = rsp.get("filter", [{}])[0]
                    sec_filter = set_filter_default(sec_filter, indicator_list=st.session_state.indicator_list)
                    st.session_state.sec_filter = sec_filter
                    add_message("assistant", f"调整后的筛选条件: {pformat(sec_filter)}")

                elif user_intent == "指标算法修改":
                    for iInd, iAlgorithm in st.session_state.indicator_algorithm.items():
                        iIndicator = st.session_state.indicator_dict.get(iInd)
                        if iIndicator and iIndicator["指标名称"] not in prompt:
                            continue
                        rsp = agents['indicator_algorithm_modification_agent'].run(input=prompt,
                                                                                   indicator_name=iIndicator[
                                                                                       "指标名称"],
                                                                                   indicator_args=iIndicator,
                                                                                   )
                        rsp = rsp.to_dict()
                        updated_algorithm = rsp.get("output", "")
                        st.session_state.indicator_algorithm[iInd] = updated_algorithm
                        add_message("assistant", f"{iIndicator['指标名称']} 调整后的衍生指标算法:\n{updated_algorithm}")

                elif user_intent == "量化分析需求":
                    # 任务编排
                    if handle_task_scheduling(prompt):
                        st.session_state.current_task = "system_analysis"

                else:  # 闲聊或其他意图
                    rsp = agents['free_answer_agent'].run(input=prompt,
                                                          )
                    rsp = rsp.to_dict()
                    add_message("assistant", rsp.get("output", ""))
                    break  # 如果是闲聊，结束处理

        else:
            # 根据当前任务阶段处理用户输入
            if st.session_state.task_stage == "awaiting_confirmation":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    if "指标提取" in st.session_state.task_list:
                        if handle_indicator_extraction():
                            st.session_state.current_task = "indicator_extraction"
                        elif prompt.lower() not in ['r', 'retry', '重试']:
                            st.session_state.task_stage = "awaiting_execution_confirmation"
                            st.session_state.current_task = "indicator_extraction"
                else:
                    handle_system_analysis_modification(prompt)

            elif st.session_state.task_stage == "awaiting_execution_confirmation":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    if "标的筛选" in st.session_state.task_list:
                        if handle_indicator_filter():
                            st.session_state.current_task = "indicator_filter"
                        elif prompt.lower() not in ['r', 'retry', '重试']:
                            st.session_state.task_stage = "awaiting_next_task_confirmation"
                            st.session_state.current_task = "indicator_filter"
                elif prompt.lower() in ['r', 'retry', '重试']:
                    handle_indicator_extraction()

            elif st.session_state.task_stage == "awaiting_next_task_confirmation":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    if "指标计算" in st.session_state.task_list:
                        if handle_indicator_calculation():
                            st.session_state.current_task = "completed"
                    else:
                        add_message(
                            "assistant",
                            "🎉 **所有任务执行完成!**\n\n您可以开始新的分析需求。"
                        )
                        st.session_state.task_stage = "completed"
                        st.session_state.current_task = None
                elif prompt.lower() in ['r', 'retry', '重试']:
                    handle_indicator_filter()

            elif st.session_state.task_stage == "error_scheduling":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    handle_task_scheduling(st.session_state.user_input)
                else:
                    add_message("assistant", "操作已取消。")
                    st.session_state.task_stage = "idle"

            elif st.session_state.task_stage == "error_modifying_analysis":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    handle_system_analysis_modification(prompt)
                else:
                    add_message("assistant", "操作已取消。")
                    st.session_state.task_stage = "idle"

            elif st.session_state.task_stage == "error_indicator_calculation":
                if prompt.lower() in ['y', 'yes', '确认', '继续']:
                    handle_indicator_calculation()
                else:
                    add_message("assistant", "操作已取消。")
                    st.session_state.task_stage = "idle"

            else:
                # 如果不是预期的阶段，比如闲聊
                rsp = agents['free_answer_agent'].run(input=prompt,
                                                      )
                rsp = rsp.to_dict()
                add_message("assistant", rsp.get("output", ""))

        st.rerun()


if __name__ == "__main__":
    main()

# 要运行应用程序，请使用以下命令：
# streamlit run sample_standard_app/app/frontend/smart_selector_app.py

