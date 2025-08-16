# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2025/01/21 19:56
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: asset_interpret_agent.py
import re
import json
import datetime as dt

import pandas as pd
from prettyprinter import pformat

from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject
from sample_standard_app.app.core.agent.asset_research.sa_agent import extract_json


class BrightSpotExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', "word_cnt"]

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        # planner_input['the_product'] = input_object.get_data('the_product')
        planner_input['word_cnt'] = str(int(input_object.get_data('word_cnt')))
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["bright_spot"] = extract_json(result["output"])
        return result

class BrightListExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', "word_cnt"]

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['word_cnt'] = str(int(input_object.get_data('word_cnt')))
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["bright_list"] = extract_json(result["output"])
        return result


# 亮点抽取
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('bright_spot_extract_agent')

    # 提报亮点
    user_input = """
    亮点: 当前市场下，本策略有何优势？: 本策略在股、债等不同风格、不同品类的资产之间进行轮动，收益来源多元化，风险更分散。以债券打底求稳健，适当关注股票增强收益，当前震荡市也力争给用户优秀体验。
    策略优势: 主要投资于固定收益类资产、高优债权，辅以少量优质权益或转债类资产提升收益，在严控下行风险的情况下，追求资产长期稳健增值。
    未来展望:
    展望后市，宏观环境仍旧处于相对低位，企业盈利筑底而宏观流动性较为宽松，周期象限来看，时钟模型判断为复苏前期，但较以往周期不同的是，就目前观测到现象而言，中国经济正处于结构调整，新旧动能换挡的阶段，本轮宏观周期在底部的时间可能较以往更长，经济复苏的斜率相对偏缓，A股盈利短期内大概率很难出现明显改善。但更多积极的因素正在酝酿，货币、财政、产业等一揽子政策的力度明显增强，且政策协同发力，落地见效的周期和效果有望进一步提升，市场大概率已经走出最悲观的场景，后续有望震荡上行，趋势性和结构性的机会并存。
    债券层面，长端利率跟随经济预期修复而快速上行，波动率急剧放大。中短期来看，股债跷跷板是较大的影响因素，如果权益市场继续走强，可能导致利率上行，投资者赎回，债市短期承压较大。从长期来看，当前尚不能判断基本面拐点的到来，需要关注数据验证，等待经济上行或通胀回升的信号。同时，产品目前持仓偏向价值，而价值风格与债券有相对明显的负相关性，出于充分分散组合波动的考虑，考虑以配置信用债基为主，同时维持一定比例的7-10国开债仓位，保持中性以上的久期水平，与组合的权益部分形成对冲。
    股票层面，A股市场暴力反弹，各类风格和宽基指数呈现普涨普跌格局，绝对波幅的差异更多体现为板块本身的弹性。从估值水平和盈利预期来看，市场前期调整相对充分，即使经过近期的快速上涨，估值明显修复，但赔率机会仍在。流动性和情绪层面，市场自9月24日后，持续大幅放量，并在10月8日创出3.5万亿的历史极值后缓慢回落。目前来看，市场第一轮快速上涨大概率结束，进入震荡整固阶段，且随着成交额逐步回归常态，市场大概率由资金驱动回归基本面驱动，要加强对于组合结构的关注。
    风格层面，组合主要关注以下四个配置方向，一是长期来看走势稳健、今年以来表现较强且从股息率看有安全边际的红利板块，作为组合的底仓，但适量控制配置比例。二是调整充分的板块大概率反弹的幅度也会更高，所以可以关注弹性更高、市值偏小、风格偏成长的宽基，如创业板指和中证500等。三是港股整体估值水平较A股仍具优势，恒生国企指数和部分港股通高分红标的值得重点关注。四是部分仓位配置于未来可能有向上弹性的板块，增强组合的进攻属性，目前主要为TMT和非银金融，后续可能增加关注汽车、资源股等板块。
    """

    # 定期报告里的投资策略描述
    # user_input = """
    # 本产品以获取绝对收益为基本目标，在匹配投资者风险偏好和持有期限的基础上，采用最大概率完成投资者目标收益，并追求尽可能高的收益回报的投资方法。具体执行上：在战略层面，以价值投资为核心，制定长期的资产配置计划，主要关注宏观经济的周期、各类资产的估值水平，以及企业的盈利状况等；在战术层面，以趋势投资为核心，主要关注基本面的边际变化、各类资产的价格走势、以及机构投资者的行为等，在资产配置计划的基础上，灵活调整产品资产结构，把握中期波段收益；在更短期的时间维度上，本产品会高频监控净值波动，通过科学的回撤控制方法，在不过多干扰主动管理的前提下，对净值进行有效的下行保护。
    # """

    #
    # user_input = input("你好，我是一个亮点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    rsp = agent.run(input=user_input, word_cnt=40, verbose=True)
    rsp = rsp.to_dict()
    bright_spot = rsp["bright_spot"]
    if bright_spot: bright_spot = bright_spot[0]
    else: bright_spot = {}
    print(f"bright_spot={pformat(bright_spot)}")

    print("===")

# 亮点抽取
if __name__ == '__main__':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    # agent = AgentManager().get_instance_obj('bright_list_extract_agent_v1')
    # agent = AgentManager().get_instance_obj('manager_bright_list_extract_agent')
    agent = AgentManager().get_instance_obj('org_bright_list_extract_agent')

    user_input = """
    1998年3月6日，经中国证监会批准，南方基金管理有限公司作为国内首批规范的基金管理公司正式成立，成为我国“新基金时代”的起始标志。
    2018年1月4日，南方基金管理有限公司整体变更设立为南方基金管理股份有限公司（以下简称“南方基金”）。2019年7月30日，经中国证监会核准，南方基金完成实施员工持股计划，通过员工持股和股东增资，注册资本增至36172万元人民币。目前，南方基金有8家股东，分别为华泰证券股份有限公司、深圳市投资控股有限公司、厦门国际信托有限公司、兴业证券股份有限公司、厦门合泽吉企业管理合伙企业（有限合伙）、厦门合泽祥企业管理合伙企业（有限合伙）、厦门合泽益企业管理合伙企业（有限合伙）、厦门合泽盈企业管理合伙企业（有限合伙）。
	南方基金总部设在深圳，北京、上海、深圳、南京、成都、合肥六地设有分公司，在深圳和香港设有子公司-南方资本管理有限公司（深圳子公司）和南方东英资产管理有限公司（香港子公司）。南方东英是境内基金公司获批成立的第一家境外分支机构；南方资本下设南方股权子公司，主要从事私募股权投资业务。南方基金总部设在深圳，北京、上海、深圳、南京、成都、合肥六地设有分公司，在深圳和香港设有子公司-南方资本管理有限公司（深圳子公司）和南方东英资产管理有限公司（香港子公司）。南方东英是境内基金公司获批成立的第一家境外分支机构；南方资本下设南方股权子公司，主要从事私募股权投资业务。
	截至2023年6月30日，南方基金母子公司合并资产管理规模19956亿元。其中南方基金母公司规模18832亿元，位居行业前列。南方基金公募基金规模11389亿元，客户数量1.95亿，累计向客户分红1774亿元，管理公募基金共337只，产品涵盖股票型、混合型、债券型、货币型、指数型、QDII型、FOF型等。南方基金非公募业务规模7443亿元，在行业中持续保持优势地位。南方资本子公司规模222亿元，南方东英子公司规模902亿元。南方基金已发展成为产品种类丰富、业务领域全面、经营业绩优秀、资产管理规模位居前列的基金管理公司之一。
    """
    print(f"input={pformat(user_input)}")

    rsp = agent.run(input=user_input, word_cnt=40, verbose=True)
    rsp = rsp.to_dict()
    bright_list = rsp["bright_list"]
    if bright_list: bright_list = bright_list[0]
    else: bright_list = {}
    print(f"bright_list={pformat(bright_list)}")

    print("===")