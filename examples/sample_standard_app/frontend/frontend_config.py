#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2024/12/22 17:55
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : frontend_config.py
# @Software: PyCharm


import os
from pathlib import Path

# 基础路径配置
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMP_DIR = BASE_DIR / "temp"

# 创建必要的目录
TEMP_DIR.mkdir(exist_ok=True)

# 应用配置
APP_CONFIG = {
    "title": "智能指标分析系统",
    "description": "基于AI的金融指标分析工具",
    "version": "1.0.0",
    "debug": True
}

# 页面配置
PAGE_CONFIG = {
    "page_title": APP_CONFIG["title"],
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# 任务配置
TASK_CONFIG = {
    "max_retries": 3,
    "timeout": 300,  # 秒
    "batch_size": 100
}

# 示例配置
EXAMPLES = [
    {
        "title": "固收+产品筛选",
        "description": "基于年化收益和最大回撤的筛选分析",
        "query": "我想提取公募近1年年化收益超过0.02，且近1年最大回撤不超过50%的产品，开始时间为'2024-01-01'",
        "icon": "📊"
    },
    {
        "title": "股票型基金分析",
        "description": "基于超额收益和最大回撤的综合分析",
        "query": "分析公募基金中近3年超额收益大于0，且近一年最大回撤小于0.2的产品",
        "icon": "📈"
    }
]

# 界面配置
UI_CONFIG = {
    "chat_input_height": 120,
    "chat_input_width": "95%",
    "max_display_rows": 20,
    "chart_height": 450,
    "animation_speed": 800
}