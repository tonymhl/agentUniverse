#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/22 17:55
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : frontend_utils.py
# @Software: PyCharm


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any


def create_indicator_visualization(data: pd.DataFrame, indicator_name: str) -> go.Figure:
    """创建指标可视化图表"""
    fig = px.line(data, x='the_datetime', y='value',
                  title=f'{indicator_name}趋势图',
                  labels={'the_datetime': '日期', 'value': '指标值'})
    fig.update_layout(showlegend=True)
    return fig


def format_indicator_results(results: Dict[str, Any]) -> pd.DataFrame:
    """格式化指标计算结果"""
    if isinstance(results, pd.DataFrame):
        return results
    elif isinstance(results, dict):
        return pd.DataFrame.from_dict(results)
    else:
        raise ValueError("Unsupported result format")


def generate_summary_report(filtered_data: pd.DataFrame,
                            calculation_results: Dict[str, pd.DataFrame]) -> str:
    """生成分析总结报告"""
    report = []
    report.append("# 分析结果总结")

    # 筛选结果统计
    if filtered_data is not None:
        report.append("\n## 筛选结果")
        report.append(f"- 符合条件的产品数量: {len(filtered_data)}")

    # 计算结果统计
    if calculation_results:
        report.append("\n## 指标计算结果")
        for indicator, result in calculation_results.items():
            report.append(f"\n### {indicator}")
            report.append(f"- 样本数量: {len(result)}")
            report.append(f"- 均值: {result['value'].mean():.4f}")
            report.append(f"- 中位数: {result['value'].median():.4f}")

    return "\n".join(report)