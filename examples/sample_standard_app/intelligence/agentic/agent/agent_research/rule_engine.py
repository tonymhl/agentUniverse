#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) Antfin, Inc. All rights reserved.
# @Time    : 2025/2/24 10:42
# @Author  : tonymhl
# @email   : mahongli.mhl@antgroup.com
# @Version : Python3
# @File    : rule_engine.py
# @Software: PyCharm


import requests
import json


def single_calc_async(rule: dict):
    url = "https://bigoal.alipay.com/research/finbase-quant/single_calc_async"

    response = requests.request("POST", url, headers={
        'Content-Type': 'application/json',
    }, data=json.dumps(rule, ensure_ascii=False))

    print(response.json())
    return response.json()["calc_trace_id"]


def get_single_calc_result(calc_trace_id: str):
    url = "https://bigoal.alipay.com/research/finbase-quant/get_single_calc_result"

    payload = json.dumps({
        "calc_trace_id": calc_trace_id
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.json())
    return response.json()


if __name__ == '__main__':
    # 股票demo
    # rule = {
    #     "target_space": "STOCK",
    #     "target_range": {
    #         "A_STOCK": "SH;SZ;BJ"
    #     },
    #     "filter_rule": "$1 >= 9569300 && $2 >= 10000000000",
    #     "param_config": {
    #         "$1": {
    #             "data_id": "gildatav2_qt_stockperformance",
    #             "res_field": "turnovervolume",
    #             "res_type": "double",
    #             "date_key": "tradingday"
    #         },
    #         "$2": {
    #             "data_id": "gildatav2_qt_stockperformance",
    #             "res_field": "totalmv",
    #             "res_type": "double",
    #             "date_key": "tradingday"
    #         }
    #     }
    # }

    # 基金demo的rule
    rule = {
        "target_space": "FUND",
        "target_range": {
            "PRODUCT_CATEGORY": "FUND_PUBLIC"
        },
        "filter_rule": "FI002233 > 0.02 &&  FI002237 == true && $1 > 0 && $2 > 0.5",
        "param_config": {
            "$1": {
                "ns_code": "fund.indicator.cum_return",
                "filters": {
                    "frequency": [
                        "day"
                    ],
                    "period": [
                        "6m"
                    ]
                },
                "res_field": "value",
                "res_type": "double"
            },
            "$2": {
                "data_id": "AntAlpha_fap_fund_factor_rank_obts_quarter",
                "filters": {
                    "factor": [
                        "cum_return"
                    ],
                    "rank_scope": [
                        "FundResearchScope"
                    ]
                },
                "res_field": "rank_pct",
                "res_type": "double",
                "date_key": "the_datetime"
            }
        }
    }

    # 发起异步规则计算
    calc_trace_id = single_calc_async(rule)

    # 轮询结果
    while True:
        import time

        time.sleep(1)
        res = get_single_calc_result(calc_trace_id)

        if res['calc_status'] == 200 or res['calc_status'] == 500:
            break

    print(f"calc_status = {res['calc_status']}")
    print(f"match count = {res['total_count']}")
    print(f"match datas = {res['datas']}")








