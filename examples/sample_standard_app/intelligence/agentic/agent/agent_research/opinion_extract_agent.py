# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2025/01/01 21:31
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: opinion_extract_agent.py
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


def merge_opinion(opinion_list, subject_field="主体", drop_na_subject=True, direction_field=None):
    merged_dict, SubjectCnt = {}, {}
    for i, iOpinion in enumerate(opinion_list):
        iSubject = iOpinion.get(subject_field, None)
        if drop_na_subject and (iSubject is None): continue
        iMergedOpition = merged_dict.setdefault(iOpinion[subject_field], {})
        iMergedOpition[subject_field] = iSubject
        for jKey, jVal in iOpinion.items():
            if jKey != subject_field:
                ijList = iMergedOpition.get(jKey, [])
                ijList += [None] * (SubjectCnt.setdefault(iSubject, 0) - len(ijList))
                ijList.append(jVal)
                iMergedOpition[jKey] = ijList
        SubjectCnt[iSubject] += 1
    if direction_field:
        for iSubject, iOpinion in merged_dict.items():
            if direction_field in iOpinion:
                iDirectionList = pd.Series(iOpinion[direction_field])
                iDirectionList = iDirectionList.where(iDirectionList!="无", None).dropna().unique()
                if (iDirectionList.shape[0]==0) or (iDirectionList.shape[0]>1):
                    iOpinion[direction_field] = "无"
                else:
                    iOpinion[direction_field] = iDirectionList[0]
    return list(merged_dict.values())

class OpinionExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'the_date']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['the_date'] = input_object.get_data('the_date')
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_list"] = extract_json(result["output"])
        return result

class OpinionExtractRewriteAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'the_date', 'word_cnt']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['the_date'] = input_object.get_data('the_date')
        planner_input['word_cnt'] = str(int(input_object.get_data('word_cnt')))
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["dim_opinion"] = extract_json(result["output"])
        return result

# 废弃
class OpinionExtractMarkAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'the_date', 'word_cnt', 'focus']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['the_date'] = input_object.get_data('the_date')
        planner_input['focus'] = input_object.get_data('focus')
        planner_input['word_cnt'] = str(int(input_object.get_data('word_cnt')))
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["marked_opinion"] = extract_json(result["output"])
        return result

class OpinionTraceAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'opinion']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['opinion'] = input_object.get_data('opinion')
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result

class OpinionMarkAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'the_date']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['the_date'] = input_object.get_data('the_date')
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result

class SubjectExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['opinion_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['opinion_list'] = "[" + "\n".join(json.dumps(iOpinion, ensure_ascii=False) for iOpinion in input_object.get_data("opinion_list")) + "]"
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_list"] = extract_json(result["output"])
        return result

class LSSubjectMatchAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['opinion_list', 'subject_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['opinion_list'] = "["+"\n".join(json.dumps(iOpinion, ensure_ascii=False) for iOpinion in input_object.get_data("opinion_list"))+"]"
        planner_input['subject_list'] = ",".join(input_object.get_data('subject_list'))
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_list"] = extract_json(result["output"])
        return result

class SubjectMatchAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['opinion_list', 'subject_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['opinion_list'] = "["+"\n".join(json.dumps(iOpinion, ensure_ascii=False) for iOpinion in input_object.get_data("opinion_list"))+"]"
        planner_input['subject_list'] = ",".join(input_object.get_data('subject_list'))
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_list"] = extract_json(result["output"])
        return result

class DirectionExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['opinion_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['opinion_list'] = "[" + "\n".join(json.dumps(iOpinion, ensure_ascii=False) for iOpinion in input_object.get_data("opinion_list")) + "]"
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_list"] = extract_json(result["output"])
        return result

class ReviewExtractAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input', 'the_date', 'word_cnt', 'direction']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        planner_input['the_date'] = input_object.get_data('the_date')
        planner_input['direction'] = input_object.get_data('direction')
        planner_input['word_cnt'] = str(int(input_object.get_data('word_cnt')))
        if input_object.get_data('verbose', False):
            prompt = self.agent_model.profile["instruction"].format(**planner_input)
            print(f"{self.agent_model.info['name']}: prompt=", prompt, sep="\n")
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result

class LSLabelAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['opinion_list']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['opinion_list'] = json.dumps(input_object.get_data("opinion_list"), ensure_ascii=False)
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        result = planner_result.copy()
        result["opinion_label"] = extract_json(result["output"])
        return result


# 观点抽取
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('opinion_extract_agent')

    user_input = """
    国内方面，三季度前两个月经济延续下行。制造业PMI在三季度前两个月进一步走低，8月回落至49.1，9月止跌回升至49.8，连续5个月下滑后企稳回升。消费者信心指数和就业预期指数继续下行，叠加收入增速下降，消费整体走弱。8月社会消费品零售总额同比增速从前值2.7%回落至2.1%，季调环比增速再次负增长，环比下跌0.01%，指向居民消费下行，与核心CPI环比增速节奏一致。
    在经济下行压力的背景下，国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“促进房地产市场止跌回稳”的新表述。本次会议对于提振经济预期和增强资本市场信心均具有积极的信号作用，后续需重点关注增量财政政策力度以及财政发力方向，财政最终的落地情况是经济基本面能否扎实企稳回升的关键。
    海外方面，美联储在9月议息会议宣布降息50BP，基本符合市场预期。其中SEP文件显示美联储将2024年美国GDP增速预测由2.1%下调至2%，失业率由4%上调至4.4%，核心PCE通胀由2.8%下调至2.6%。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），2025年再降息100BP（6月时预期为75BP）。根据鲍威尔的表述，这次50BP的降息幅度，市场可以看做是美联储确保货币政策不落后于经济的承诺，鲍威尔坚定地表明了预防性降息以及全力保持经济强劲的立场。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，美国经济处于良好状态，而美联储致力于保持当前的增长韧性。美国7月新增非农就业11.4万人（初值）大幅不及预期引发市场对于美国衰退的担忧，引发了全球一轮衰退交易；8月新增非农回升至14.2万人；9月新增非农25.4万人，大幅超出市场预期，为3月以来新高，并且7月和8月均有所上修，3个月平均新增就业人数回升至18.6万人，9月失业率为4.1%，较8月继续下行0.1个百分点，连续2个月下行。虽然就业市场在降温，但是大幅走弱的概率依然较低，薪资增速依旧保持较为强劲状态。根据领先指标，薪资增速会延续回落，总体来看，劳动力市场依旧健康，那么美国经济最大的基本盘（消费），就没有大幅走弱。美国三季度的经济保持较强韧性，根据亚特兰大联储的GDPNowcast模型的最新预测，三季度GDP环比折年增速2.5%（10月1日的最新预测），保持较强韧性。随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，对中国权益资产整体偏利好。
    2024年三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。底层逻辑，从行业成长空间、业绩增速与估值匹配度、预期差三个角度选择，同时结合当下宏观政策刺激与获益情况，当前三季度我们对几个行业进行了一定调整：维持电力设备、家电、军工、美容护理、汽车、传媒超配，维持食品饮料、房地产、银行、煤炭、石油石化低配，减持公用事业，加仓非银、计算机、医药。
    成长之星业绩基准是沪深300指数，该指数是中国经济增长的微观缩影，龙头效应明显，过去三年表现承压，反映了市场较低的经济预期，产能过剩和价格通缩仍然制约经济向上动力。我们动态调整组合希望在经济增长与预期的差距中间寻求平衡，缩小行业偏离度有利于保证我们跟上基准，再通过行业配置和个股选择跑赢基准。基金整体仓位维持稳定，随着申购规模加大，仓位略有下降。
    从投资策略上，我们看重性价比，性价比是风险和收益的平衡，也是基本面和估值的结合。我们认为性价比可以用预期年回报率/风险来量化。预期年回报率包括业绩增长、估值变化、股息率、回购水平、实际利率等成分构成。而风险方面我们考虑多个层次的风险，公司层面的营运风险和财务风险，行业层面政策风险，宏观层面地缘政治风险，组合层面集中度和相关度等。通过性价比策略可用于行业内比较，也能够进行跨行业比较；可用于成长股比较，也能够价值股比较，也能够对成长和价值股放在同一维度比较。
    按照这个策略我们投资三类股票类型：
    一是低估值：估值偏低，但竞争力强的行业龙头公司。行业增速5-10%左右，由于跨行业/冷门行业，容易被市场忽视的领域，公司竞争力强，长期成长路径清晰，增速10-15%左右，估值偏低未来可能有提升空间（10倍PE到12倍PE）增强回报，股东年综合回报率在25-30%左右。
    二是高成长：市场大的主流趋势的回调阶段，公司在竞争中处于极为有利的战略位置的企业。新兴行业20-30%的高速增长，公司竞争地位极为有利，能够持续三年增速快于行业，由于业绩节奏/市场风格等因素导致回调，给与远期稳态低估值，测算下来股东年综合回报率还能有30%-40%的股票。
    三是高分红及回购：供给有瓶颈，需求增长有预期差的行业，龙头公司能够通过分红和回购增强股东回报。随着经济增速下移，越来越多的行业进入稳定期，资本开支减少，企业价值分配上倾向于增加分红和回购来增强股东回报。股东年综合回报率有20-25%左右。
    四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：
    1.内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；
    2.受益于本轮市场上涨和风险偏好改善的非银、计算机、国产算力及芯片；
    3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；
    4.持续看好基于长的产业周期景气度还没结束的船舶类资产。
    """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    the_date = '2024-09-30, 三季度末'

    rsp = agent.run(input=user_input, the_date=the_date, verbose=True)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    print(f"opinion_list={pformat(opinion_list)}")

    print("===")

# 观点标记
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('opinion_mark_agent')

    user_input = """
    国内方面，三季度前两个月经济延续下行。制造业PMI在三季度前两个月进一步走低，8月回落至49.1，9月止跌回升至49.8，连续5个月下滑后企稳回升。消费者信心指数和就业预期指数继续下行，叠加收入增速下降，消费整体走弱。8月社会消费品零售总额同比增速从前值2.7%回落至2.1%，季调环比增速再次负增长，环比下跌0.01%，指向居民消费下行，与核心CPI环比增速节奏一致。
    在经济下行压力的背景下，国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“促进房地产市场止跌回稳”的新表述。本次会议对于提振经济预期和增强资本市场信心均具有积极的信号作用，后续需重点关注增量财政政策力度以及财政发力方向，财政最终的落地情况是经济基本面能否扎实企稳回升的关键。
    海外方面，美联储在9月议息会议宣布降息50BP，基本符合市场预期。其中SEP文件显示美联储将2024年美国GDP增速预测由2.1%下调至2%，失业率由4%上调至4.4%，核心PCE通胀由2.8%下调至2.6%。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），2025年再降息100BP（6月时预期为75BP）。根据鲍威尔的表述，这次50BP的降息幅度，市场可以看做是美联储确保货币政策不落后于经济的承诺，鲍威尔坚定地表明了预防性降息以及全力保持经济强劲的立场。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，美国经济处于良好状态，而美联储致力于保持当前的增长韧性。美国7月新增非农就业11.4万人（初值）大幅不及预期引发市场对于美国衰退的担忧，引发了全球一轮衰退交易；8月新增非农回升至14.2万人；9月新增非农25.4万人，大幅超出市场预期，为3月以来新高，并且7月和8月均有所上修，3个月平均新增就业人数回升至18.6万人，9月失业率为4.1%，较8月继续下行0.1个百分点，连续2个月下行。虽然就业市场在降温，但是大幅走弱的概率依然较低，薪资增速依旧保持较为强劲状态。根据领先指标，薪资增速会延续回落，总体来看，劳动力市场依旧健康，那么美国经济最大的基本盘（消费），就没有大幅走弱。美国三季度的经济保持较强韧性，根据亚特兰大联储的GDPNowcast模型的最新预测，三季度GDP环比折年增速2.5%（10月1日的最新预测），保持较强韧性。随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，对中国权益资产整体偏利好。
    2024年三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。底层逻辑，从行业成长空间、业绩增速与估值匹配度、预期差三个角度选择，同时结合当下宏观政策刺激与获益情况，当前三季度我们对几个行业进行了一定调整：维持电力设备、家电、军工、美容护理、汽车、传媒超配，维持食品饮料、房地产、银行、煤炭、石油石化低配，减持公用事业，加仓非银、计算机、医药。
    成长之星业绩基准是沪深300指数，该指数是中国经济增长的微观缩影，龙头效应明显，过去三年表现承压，反映了市场较低的经济预期，产能过剩和价格通缩仍然制约经济向上动力。我们动态调整组合希望在经济增长与预期的差距中间寻求平衡，缩小行业偏离度有利于保证我们跟上基准，再通过行业配置和个股选择跑赢基准。基金整体仓位维持稳定，随着申购规模加大，仓位略有下降。
    从投资策略上，我们看重性价比，性价比是风险和收益的平衡，也是基本面和估值的结合。我们认为性价比可以用预期年回报率/风险来量化。预期年回报率包括业绩增长、估值变化、股息率、回购水平、实际利率等成分构成。而风险方面我们考虑多个层次的风险，公司层面的营运风险和财务风险，行业层面政策风险，宏观层面地缘政治风险，组合层面集中度和相关度等。通过性价比策略可用于行业内比较，也能够进行跨行业比较；可用于成长股比较，也能够价值股比较，也能够对成长和价值股放在同一维度比较。
    按照这个策略我们投资三类股票类型：
    一是低估值：估值偏低，但竞争力强的行业龙头公司。行业增速5-10%左右，由于跨行业/冷门行业，容易被市场忽视的领域，公司竞争力强，长期成长路径清晰，增速10-15%左右，估值偏低未来可能有提升空间（10倍PE到12倍PE）增强回报，股东年综合回报率在25-30%左右。
    二是高成长：市场大的主流趋势的回调阶段，公司在竞争中处于极为有利的战略位置的企业。新兴行业20-30%的高速增长，公司竞争地位极为有利，能够持续三年增速快于行业，由于业绩节奏/市场风格等因素导致回调，给与远期稳态低估值，测算下来股东年综合回报率还能有30%-40%的股票。
    三是高分红及回购：供给有瓶颈，需求增长有预期差的行业，龙头公司能够通过分红和回购增强股东回报。随着经济增速下移，越来越多的行业进入稳定期，资本开支减少，企业价值分配上倾向于增加分红和回购来增强股东回报。股东年综合回报率有20-25%左右。
    四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：
    1.内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；
    2.受益于本轮市场上涨和风险偏好改善的非银、计算机、国产算力及芯片；
    3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；
    4.持续看好基于长的产业周期景气度还没结束的船舶类资产。
    """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    the_date = '2024-09-30, 三季度末'

    rsp = agent.run(input=user_input, the_date=the_date, verbose=True)
    rsp = rsp.to_dict()
    marked_output = rsp["output"]
    print(f"marked_output={pformat(marked_output)}")

    print("===")

# 观点抽取改写
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('opinion_extract_rewrite_agent')

    user_input = """
    4.1基金经理（或基金经理小组）简介
    姓名,职务,任本基金的基金经理期限,证券从业年限,说明任职日期,离任日期任婧,本基金基金经理,2022年11月18日,-,7年,女，北京大学金融硕士，具有基金从业资格。2017年7月加入南方基金，任权益研究部电动车行业研究员；2022年11月18日至今，任南方兴盛混合基金经理；2024年3月25日至今，任南方智锐混合基金经理。    注：1、本基金首任基金经理的任职日期为本基金合同生效日，后任基金经理的任职日期以及历任基金经理的离任日期为公司相关会议作出决定的公告（生效）日期；
    2、证券从业年限计算标准遵从中国证监会《证券基金经营机构董事、监事、高级管理人员及从业人员监督管理办法》中关于证券基金从业人员范围的相关规定。
    4.2管理人对报告期内本基金运作遵规守信情况的说明
    本报告期内，本基金管理人严格遵守《中华人民共和国证券投资基金法》等有关法律法规、中国证监会和本基金基金合同的规定，本着诚实信用、勤勉尽责的原则管理和运用基金资产，在严格控制风险的基础上，为基金份额持有人谋求利益。本报告期内，本基金运作整体合法合规，没有损害基金份额持有人利益。基金的投资范围、投资比例及投资组合符合有关法律法规及基金合同的规定。
    4.3公平交易专项说明
    4.3.1公平交易制度的执行情况
    本报告期内，本基金管理人严格执行《证券投资基金管理公司公平交易制度指导意见》，完善相应制度及流程，通过系统和人工等各种方式在各业务环节严格控制交易公平执行，公平对待旗下管理的所有基金和投资组合。
    4.3.2异常交易行为的专项说明
    本基金于本报告期内不存在异常交易行为。本报告期内基金管理人管理的所有投资组合参与的交易所公开竞价同日反向交易成交较少的单边交易量超过该证券当日成交量的5%的交易次数为49次，是由于指数投资组合的投资策略导致。
    4.4报告期内基金投资策略和运作分析
    2024年市场波动较大，全年整体市场收涨。此外24年随着时间阶段不同的市场表现出一定的风格分化，整体上市值的大小在2024年成为很多时间段决定超额收益的重要因子之一。回顾全年的经济数据，我们发现出口的韧性还是比较强劲的，欧美市场和新兴市场轮番有亮点体现，这不仅仅体现在一些行业的补库需求中，还有一些细分行业体现出终端需求渗透率的提升，这毫无疑问是更有持续性的长期方向。
    针对2025年我们保持一个积极的观点，一方面22年以来，国内的制造业产能扩张已经开始放缓，虽然这可能还需要一些时间来消化，但整体上算是一个好的开始，特别是目前亏损比较严重，资产负债表上负担比较重的行业有望先迎来出清。
    此外随着产业结构的变化，一些传统产业的供需结构也在出现变化，此前市场逐渐认知到铜铝的下游电力/新能源的需求占比提升能够在一定程度上对冲传统地产需求的下行，目前随着新能源特别是锂电需求的持续增长，这样的品种也在逐渐变多，不排除未来的2-3年可能有一些传统产业表现出意想不到的机会，这些机会有的在两三年前已经产生类似的逻辑，但由于届时新能源的需求毕竟绝对体量还不足够大，实际的供需上难以兑现，但随着时间的推移，可能未来的几年能够看到实际的兑现。
    4.5报告期内基金的业绩表现
    截至报告期末，本基金A份额净值为1.6941元，报告期内，份额净值增长率为-3.66%，同期业绩基准增长率为0.00%；本基金C份额净值为1.6759元，报告期内，份额净值增长率为-3.81%，同期业绩基准增长率为0.00%。
    4.6报告期内基金持有人数或基金资产净值预警说明
    报告期内，本基金未出现连续二十个交易日基金份额持有人数量不满二百人或者基金资产净值低于五千万元的情形。"""
    # user_input = """
    # 本基金权益投资的策略是自上而下行业维度和自下而上精选个股相结合的选股策略。本基金以追求个股绝对收益为目标，配置低估值标的作为基金底仓，同时通过横向对比各子领域板块，选择未来景气度持续改善的成长性行业作为基金的弹性仓位。三季度，权益市场先抑后扬，市场在下跌过程中，从个股绝对收益角度，组合逐步提高了仓位，随着九月底市场的暴涨，很多个股从绝对收益的角度，性价比开始下降，逐步止盈了相关的个股。产品一直坚持个股绝对收益、同时控制波动率的策略，在市场暴涨过程中，会出现阶段性落后于市场的情况。三季报中，低估值底仓以建筑、公用事业、传媒、消费等持仓为主，成长性方向以军工、医药、电子等板块投资为主。
    # """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    the_date = '2024-12-31, 四季度末'

    rsp = agent.run(input=user_input, the_date=the_date, word_cnt=200, verbose=True)
    rsp = rsp.to_dict()
    dim_opinion = rsp["dim_opinion"]
    print(f"dim_opinion={pformat(dim_opinion)}")

    print("===")

# 观点抽取标记(废弃)
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('opinion_extract_mark_agent')

    user_input = """
    国内方面，三季度前两个月经济延续下行。制造业PMI在三季度前两个月进一步走低，8月回落至49.1，9月止跌回升至49.8，连续5个月下滑后企稳回升。消费者信心指数和就业预期指数继续下行，叠加收入增速下降，消费整体走弱。8月社会消费品零售总额同比增速从前值2.7%回落至2.1%，季调环比增速再次负增长，环比下跌0.01%，指向居民消费下行，与核心CPI环比增速节奏一致。
    在经济下行压力的背景下，国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“促进房地产市场止跌回稳”的新表述。本次会议对于提振经济预期和增强资本市场信心均具有积极的信号作用，后续需重点关注增量财政政策力度以及财政发力方向，财政最终的落地情况是经济基本面能否扎实企稳回升的关键。
    海外方面，美联储在9月议息会议宣布降息50BP，基本符合市场预期。其中SEP文件显示美联储将2024年美国GDP增速预测由2.1%下调至2%，失业率由4%上调至4.4%，核心PCE通胀由2.8%下调至2.6%。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），2025年再降息100BP（6月时预期为75BP）。根据鲍威尔的表述，这次50BP的降息幅度，市场可以看做是美联储确保货币政策不落后于经济的承诺，鲍威尔坚定地表明了预防性降息以及全力保持经济强劲的立场。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，美国经济处于良好状态，而美联储致力于保持当前的增长韧性。美国7月新增非农就业11.4万人（初值）大幅不及预期引发市场对于美国衰退的担忧，引发了全球一轮衰退交易；8月新增非农回升至14.2万人；9月新增非农25.4万人，大幅超出市场预期，为3月以来新高，并且7月和8月均有所上修，3个月平均新增就业人数回升至18.6万人，9月失业率为4.1%，较8月继续下行0.1个百分点，连续2个月下行。虽然就业市场在降温，但是大幅走弱的概率依然较低，薪资增速依旧保持较为强劲状态。根据领先指标，薪资增速会延续回落，总体来看，劳动力市场依旧健康，那么美国经济最大的基本盘（消费），就没有大幅走弱。美国三季度的经济保持较强韧性，根据亚特兰大联储的GDPNowcast模型的最新预测，三季度GDP环比折年增速2.5%（10月1日的最新预测），保持较强韧性。随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，对中国权益资产整体偏利好。
    2024年三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。底层逻辑，从行业成长空间、业绩增速与估值匹配度、预期差三个角度选择，同时结合当下宏观政策刺激与获益情况，当前三季度我们对几个行业进行了一定调整：维持电力设备、家电、军工、美容护理、汽车、传媒超配，维持食品饮料、房地产、银行、煤炭、石油石化低配，减持公用事业，加仓非银、计算机、医药。
    成长之星业绩基准是沪深300指数，该指数是中国经济增长的微观缩影，龙头效应明显，过去三年表现承压，反映了市场较低的经济预期，产能过剩和价格通缩仍然制约经济向上动力。我们动态调整组合希望在经济增长与预期的差距中间寻求平衡，缩小行业偏离度有利于保证我们跟上基准，再通过行业配置和个股选择跑赢基准。基金整体仓位维持稳定，随着申购规模加大，仓位略有下降。
    从投资策略上，我们看重性价比，性价比是风险和收益的平衡，也是基本面和估值的结合。我们认为性价比可以用预期年回报率/风险来量化。预期年回报率包括业绩增长、估值变化、股息率、回购水平、实际利率等成分构成。而风险方面我们考虑多个层次的风险，公司层面的营运风险和财务风险，行业层面政策风险，宏观层面地缘政治风险，组合层面集中度和相关度等。通过性价比策略可用于行业内比较，也能够进行跨行业比较；可用于成长股比较，也能够价值股比较，也能够对成长和价值股放在同一维度比较。
    按照这个策略我们投资三类股票类型：
    一是低估值：估值偏低，但竞争力强的行业龙头公司。行业增速5-10%左右，由于跨行业/冷门行业，容易被市场忽视的领域，公司竞争力强，长期成长路径清晰，增速10-15%左右，估值偏低未来可能有提升空间（10倍PE到12倍PE）增强回报，股东年综合回报率在25-30%左右。
    二是高成长：市场大的主流趋势的回调阶段，公司在竞争中处于极为有利的战略位置的企业。新兴行业20-30%的高速增长，公司竞争地位极为有利，能够持续三年增速快于行业，由于业绩节奏/市场风格等因素导致回调，给与远期稳态低估值，测算下来股东年综合回报率还能有30%-40%的股票。
    三是高分红及回购：供给有瓶颈，需求增长有预期差的行业，龙头公司能够通过分红和回购增强股东回报。随着经济增速下移，越来越多的行业进入稳定期，资本开支减少，企业价值分配上倾向于增加分红和回购来增强股东回报。股东年综合回报率有20-25%左右。
    四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：
    1.内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；
    2.受益于本轮市场上涨和风险偏好改善的非银、计算机、国产算力及芯片；
    3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；
    4.持续看好基于长的产业周期景气度还没结束的船舶类资产。
    """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    the_date = '2024-09-30, 三季度末'

    rsp = agent.run(input=user_input, the_date=the_date, focus="关于行业板块未来发展的观点", word_cnt=200, verbose=True)
    rsp = rsp.to_dict()
    marked_opinion = rsp["marked_opinion"]
    print(f"marked_opinion={pformat(marked_opinion)}")

    print("===")

# 观点追溯
if __name__ == '__main__1':
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('opinion_trace_agent')

    user_input = """
    国内方面，三季度前两个月经济延续下行。制造业PMI在三季度前两个月进一步走低，8月回落至49.1，9月止跌回升至49.8，连续5个月下滑后企稳回升。消费者信心指数和就业预期指数继续下行，叠加收入增速下降，消费整体走弱。8月社会消费品零售总额同比增速从前值2.7%回落至2.1%，季调环比增速再次负增长，环比下跌0.01%，指向居民消费下行，与核心CPI环比增速节奏一致。
    在经济下行压力的背景下，国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“促进房地产市场止跌回稳”的新表述。本次会议对于提振经济预期和增强资本市场信心均具有积极的信号作用，后续需重点关注增量财政政策力度以及财政发力方向，财政最终的落地情况是经济基本面能否扎实企稳回升的关键。
    海外方面，美联储在9月议息会议宣布降息50BP，基本符合市场预期。其中SEP文件显示美联储将2024年美国GDP增速预测由2.1%下调至2%，失业率由4%上调至4.4%，核心PCE通胀由2.8%下调至2.6%。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），2025年再降息100BP（6月时预期为75BP）。根据鲍威尔的表述，这次50BP的降息幅度，市场可以看做是美联储确保货币政策不落后于经济的承诺，鲍威尔坚定地表明了预防性降息以及全力保持经济强劲的立场。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，美国经济处于良好状态，而美联储致力于保持当前的增长韧性。美国7月新增非农就业11.4万人（初值）大幅不及预期引发市场对于美国衰退的担忧，引发了全球一轮衰退交易；8月新增非农回升至14.2万人；9月新增非农25.4万人，大幅超出市场预期，为3月以来新高，并且7月和8月均有所上修，3个月平均新增就业人数回升至18.6万人，9月失业率为4.1%，较8月继续下行0.1个百分点，连续2个月下行。虽然就业市场在降温，但是大幅走弱的概率依然较低，薪资增速依旧保持较为强劲状态。根据领先指标，薪资增速会延续回落，总体来看，劳动力市场依旧健康，那么美国经济最大的基本盘（消费），就没有大幅走弱。美国三季度的经济保持较强韧性，根据亚特兰大联储的GDPNowcast模型的最新预测，三季度GDP环比折年增速2.5%（10月1日的最新预测），保持较强韧性。随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，对中国权益资产整体偏利好。
    2024年三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。底层逻辑，从行业成长空间、业绩增速与估值匹配度、预期差三个角度选择，同时结合当下宏观政策刺激与获益情况，当前三季度我们对几个行业进行了一定调整：维持电力设备、家电、军工、美容护理、汽车、传媒超配，维持食品饮料、房地产、银行、煤炭、石油石化低配，减持公用事业，加仓非银、计算机、医药。
    成长之星业绩基准是沪深300指数，该指数是中国经济增长的微观缩影，龙头效应明显，过去三年表现承压，反映了市场较低的经济预期，产能过剩和价格通缩仍然制约经济向上动力。我们动态调整组合希望在经济增长与预期的差距中间寻求平衡，缩小行业偏离度有利于保证我们跟上基准，再通过行业配置和个股选择跑赢基准。基金整体仓位维持稳定，随着申购规模加大，仓位略有下降。
    从投资策略上，我们看重性价比，性价比是风险和收益的平衡，也是基本面和估值的结合。我们认为性价比可以用预期年回报率/风险来量化。预期年回报率包括业绩增长、估值变化、股息率、回购水平、实际利率等成分构成。而风险方面我们考虑多个层次的风险，公司层面的营运风险和财务风险，行业层面政策风险，宏观层面地缘政治风险，组合层面集中度和相关度等。通过性价比策略可用于行业内比较，也能够进行跨行业比较；可用于成长股比较，也能够价值股比较，也能够对成长和价值股放在同一维度比较。
    按照这个策略我们投资三类股票类型：
    一是低估值：估值偏低，但竞争力强的行业龙头公司。行业增速5-10%左右，由于跨行业/冷门行业，容易被市场忽视的领域，公司竞争力强，长期成长路径清晰，增速10-15%左右，估值偏低未来可能有提升空间（10倍PE到12倍PE）增强回报，股东年综合回报率在25-30%左右。
    二是高成长：市场大的主流趋势的回调阶段，公司在竞争中处于极为有利的战略位置的企业。新兴行业20-30%的高速增长，公司竞争地位极为有利，能够持续三年增速快于行业，由于业绩节奏/市场风格等因素导致回调，给与远期稳态低估值，测算下来股东年综合回报率还能有30%-40%的股票。
    三是高分红及回购：供给有瓶颈，需求增长有预期差的行业，龙头公司能够通过分红和回购增强股东回报。随着经济增速下移，越来越多的行业进入稳定期，资本开支减少，企业价值分配上倾向于增加分红和回购来增强股东回报。股东年综合回报率有20-25%左右。
    四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：
    1.内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；
    2.受益于本轮市场上涨和风险偏好改善的非银、计算机、国产算力及芯片；
    3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；
    4.持续看好基于长的产业周期景气度还没结束的船舶类资产。
    """
    # 四季度看好内需市场的家电、汽车、互联网、医药等行业，以及非银、计算机、国产算力、芯片等板块。
    # 四季度，市场关注财政政策发力和货币政策改善流动性，投资策略聚焦内需市场的家电、汽车、互联网、医药等行业，以及受益于市场上涨的非银、计算机、国产算力及芯片等领域。
    # 在未来的投资策略中，成长之星基金计划在四季度增持内需相关及流动性受益的投资机会，主要聚焦于政策拉动需求的家电、汽车、互联网和医药等行业，以及受益于市场上涨和风险偏好改善的非银、计算机、国产算力及芯片。此外，还看好受益于流动性宽松及海外利率下行的消费耐用品、储能和创新药行业，并持续关注船舶类资产。

    opinion = """
    未来的投资策略中，成长之星基金计划在四季度增持内需相关及流动性受益的投资机会，主要聚焦于政策拉动需求的家电、汽车、互联网和医药等行业，以及受益于市场上涨和风险偏好改善的非银、计算机、国产算力及芯片。此外，还看好受益于流动性宽松及海外利率下行的消费耐用品、储能和创新药行业，并持续关注船舶类资产。
    """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    rsp = agent.run(input=user_input, opinion=opinion, verbose=True)
    rsp = rsp.to_dict()
    marked_output = rsp["output"]
    print(f"marked_output={pformat(marked_output)}")

    print("===")

# 主体抽取
if __name__ == "__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    subject_extract_agent = AgentManager().get_instance_obj('subject_extract_agent')

    opinion_list = [
        {
            '观点': '央行支持资本市场的货币工具有望进入实质性落地阶段，为市场带来实质性的资金支持，进一步稳定了投资者和国际资本的信心。',
            '论据': '展望四季度，央行支持资本市场的货币工具有望进入实质性落地阶段。不过每一次市场中长期底部都不是一蹴而就的，在当前复杂的国际政治形势和尚未企稳的经济基本面的现实面前，短期出现较大波动依然是难免的。'
        },
        {
            '观点': '随着经济进一步复苏以及政策进一步发力，资本市场信心和活跃度有望逐步恢复，基本面和量价模型会有较好的发挥空间。',
            '论据': '鉴于今年市场环境的复杂性，我们特别重视提升业绩稳定性，根据市场的演化过程不断引入新的因子和改良原有的模型，并强化选股模型对不同风格的适应能力，在保持稳重求胜的风格下追求更好的超额收益率。'
        },
        {
            '观点': '中证500指数有望迎来估值和盈利的双击。',
            '论据': '从中证500指数当前的估值水平来看，截至9月底其加权PE和整体PE分别在23倍和24倍左右，依然处于历史较为低估的水平，在历史上的分位数为23%左右，而用PB估值的话，则历史分位数更低，在市场主要宽基指数当中是历史相对估值最低的指数之一，在历史上的分位数为10%左右。未来随着经济的逐步企稳向好，作为市场中优质中盘股的代表，中证500指数有望迎来估值和盈利的双击。'
        },
        {
            '观点': '中证500指数依然是当前市场环境下进可攻、退可守的选择。',
            '论据': '我们认为做为一个价值股和成长股、周期股和非周期股、新兴行业和传统行业均相对均衡的中盘宽基指数，中证500指数依然是当前市场环境下进可攻、退可守的选择。'
        },
        {
            '观点': '以博取Alpha为主要目的的宽基增强型产品在当前市场点位仍具有很高的性价比。',
            '论据': '以分散化投资为主的量化投资在今年超大盘股引领的防御性行情下，阶段性面临一定的挑战，也本没有一种投资方法论可以通吃所有风格的行情，但是量化投资从投资理念和投资逻辑来讲并未发生本质性改变。'
        },
        {
            '观点': '中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间。',
            '论据': '我们认为中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间，我们将努力通过科学的手段增强量化模型的超额收益率水平，以此不断为客户增厚投资收益。'
        }
    ]
    print(f"opinion list={pformat(opinion_list)}")

    rsp = subject_extract_agent.run(opinion_list=opinion_list, verbose=True)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    print(f"subject extracted opinion list={pformat(opinion_list)}")

# 主体匹配
if __name__=="__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('subject_match_agent')

    opinion_list =[
        {
            '主体': None,
            '观点':
                '随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。'
                '对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，'
                '对中国权益资产整体偏利好。',
            '论据':
                '美联储在9月议息会议宣布降息50BP，基本符合市场预期。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），'
                '2025年再降息100BP（6月时预期为75BP）。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，'
                '美国经济处于良好状态，而美联储致力于保持当前的增长韧性。'
        },
        {
            '主体': None,
            '观点':
                '在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，'
                '在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。',
            '论据':
                '三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.'
                '00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。'
        },
        {
            '主体': None,
            '观点':
                '四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，'
                '“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：1.'
                '内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；2.受益于本轮市场上涨和风险偏好改善的非银、'
                '计算机、国产算力及芯片；3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；4.'
                '持续看好基于长的产业周期景气度还没结束的船舶类资产。',
            '论据':
                '国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“'
                '926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“'
                '促进房地产市场止跌回稳”的新表述。'
        }
    ]
    print(f"opinion list={pformat(opinion_list)}")

    subject_list = pd.read_excel("/Users/hst/Desktop/111指代词表及板块资产关联.xlsx", 1, index_col=None, header=0, engine="openpyxl")
    subject_list = subject_list["express_nick"].dropna().unique().tolist()

    rsp = agent.run(subject_list=subject_list, opinion_list=opinion_list)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    print(f"subject matched opinion list={pformat(opinion_list)}")

    print("===")

# 利好利空主体匹配
if __name__=="__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('ls_subject_match_agent')

    opinion_list =[
        {
            '观点':
                '随着美国开启降息周期，对实体的信贷增速有望回升，进一步支撑美国经济实现软着陆。美元降息周期有望带动美元指数温和回落利好新兴市场。'
                '对中国的利好程度更取决于自身经济基本面和政策前景。美元降息周期将提振人民币汇率，减轻汇率对中国货币及财政政策制约，'
                '对中国权益资产整体偏利好。',
            '论据':
                '美联储在9月议息会议宣布降息50BP，基本符合市场预期。点阵图表明美联储预计2024年将累计降息100BP（6月时预期为50BP），'
                '2025年再降息100BP（6月时预期为75BP）。鲍威尔在会议中明确表示，从目前美国经济数据来看，美国没有任何衰退迹象，'
                '美国经济处于良好状态，而美联储致力于保持当前的增长韧性。'
        },
        {
            '观点':
                '在中国经济转型背景下，深度挖掘具备未来增长潜力的产业趋势和受益企业进行投资，'
                '在有效控制风险的基础上实现基金资产的长期稳健增值是成长之星基金的投资目标。',
            '论据':
                '三季度，国内股票市场先抑后扬。受益于国内政策转向催化，9月中下旬国内股票市场实现快速反弹。三季度，上证指数+12.44%，深成指+19.'
                '00%，沪深300+16.07%，创业板指+29.21%，科创50+22.51%。'
        },
        {
            '观点':
                '四季度，一方面，市场关注点在于财政政策的发力程度，随着财政力度的边际扩大，有望带动经济边际回暖，从而带动居民就业和收入边际改善。另一方面，'
                '“924”央行超预期的货币政策组合拳，将有利于改善市场流动性。我们将从性价比出发，择机增持内需相关及流动性受益投资机会，主要聚焦：1.'
                '内需市场看好政策拉动需求行业如家电、汽车、互联网以及受益于人口老龄化趋势的医药等细分领域；2.受益于本轮市场上涨和风险偏好改善的非银、'
                '计算机、国产算力及芯片；3.受益于流动性宽松及海外利率下行的需求改善行业，包括消费耐用品、储能、创新药等；4.'
                '持续看好基于长的产业周期景气度还没结束的船舶类资产。',
            '论据':
                '国内宏观政策迎来积极转向。“924”新政推出一系列货币金融政策组合拳，超市场预期，凸显政策层稳经济稳市场和提振微观主体信心的决心。“'
                '926”政治局会议罕见讨论经济议题，会议强调“加大财政货币政策逆周期调节力度”的同时，就地产、消费等领域做出了积极表态，地产层面出现“'
                '促进房地产市场止跌回稳”的新表述。'
        }
    ]
    print(f"opinion list={pformat(opinion_list)}")

    subject_list = pd.read_excel("/Users/hst/Desktop/111指代词表及板块资产关联.xlsx", 1, index_col=None, header=0, engine="openpyxl")
    subject_list = subject_list["express_nick"].dropna().unique().tolist()

    rsp = agent.run(subject_list=subject_list, opinion_list=opinion_list)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    print(f"subject matched opinion list={pformat(opinion_list)}")

    print("===")

# 方向抽取
if __name__=="__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    direction_extract_agent = AgentManager().get_instance_obj('direction_extract_agent')

    opinion_list = [
        {
            '主体': '资本市场',
            '观点': '央行支持资本市场的货币工具有望进入实质性落地阶段，为市场带来实质性的资金支持，进一步稳定了投资者和国际资本的信心。',
            '论据': '展望四季度，央行支持资本市场的货币工具有望进入实质性落地阶段。不过每一次市场中长期底部都不是一蹴而就的，在当前复杂的国际政治形势和尚未企稳的经济基本面的现实面前，短期出现较大波动依然是难免的。'
        },
        {
            '主体': '资本市场',
            '观点': '随着经济进一步复苏以及政策进一步发力，资本市场信心和活跃度有望逐步恢复，基本面和量价模型会有较好的发挥空间。',
            '论据': '鉴于今年市场环境的复杂性，我们特别重视提升业绩稳定性，根据市场的演化过程不断引入新的因子和改良原有的模型，并强化选股模型对不同风格的适应能力，在保持稳重求胜的风格下追求更好的超额收益率。'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数有望迎来估值和盈利的双击。',
            '论据': '从中证500指数当前的估值水平来看，截至9月底其加权PE和整体PE分别在23倍和24倍左右，依然处于历史较为低估的水平，在历史上的分位数为23%左右，而用PB估值的话，则历史分位数更低，在市场主要宽基指数当中是历史相对估值最低的指数之一，在历史上的分位数为10%左右。未来随着经济的逐步企稳向好，作为市场中优质中盘股的代表，中证500指数有望迎来估值和盈利的双击。'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数依然是当前市场环境下进可攻、退可守的选择。',
            '论据': '我们认为做为一个价值股和成长股、周期股和非周期股、新兴行业和传统行业均相对均衡的中盘宽基指数，中证500指数依然是当前市场环境下进可攻、退可守的选择。'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间。',
            '论据': '我们认为中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间，我们将努力通过科学的手段增强量化模型的超额收益率水平，以此不断为客户增厚投资收益。'
        }
    ]
    print(f"opinion list={pformat(opinion_list)}")

    rsp = direction_extract_agent.run(opinion_list=opinion_list, verbose=True)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    print(f"direction extracted opinion list={pformat(opinion_list)}")

    print("===")

# 合并观点
if __name__=="__main__1":
    opinion_list = [
        {
            '主体': '资本市场',
            '观点': '央行支持资本市场的货币工具有望进入实质性落地阶段，为市场带来实质性的资金支持，进一步稳定了投资者和国际资本的信心。',
            '论据': '展望四季度，央行支持资本市场的货币工具有望进入实质性落地阶段。不过每一次市场中长期底部都不是一蹴而就的，在当前复杂的国际政治形势和尚未企稳的经济基本面的现实面前，短期出现较大波动依然是难免的。',
            "方向": '乐观'
        },
        {
            '主体': '资本市场',
            '观点': '随着经济进一步复苏以及政策进一步发力，资本市场信心和活跃度有望逐步恢复，基本面和量价模型会有较好的发挥空间。',
            '论据': '鉴于今年市场环境的复杂性，我们特别重视提升业绩稳定性，根据市场的演化过程不断引入新的因子和改良原有的模型，并强化选股模型对不同风格的适应能力，在保持稳重求胜的风格下追求更好的超额收益率。',
            "方向": '无'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数有望迎来估值和盈利的双击。',
            '论据': '从中证500指数当前的估值水平来看，截至9月底其加权PE和整体PE分别在23倍和24倍左右，依然处于历史较为低估的水平，在历史上的分位数为23%左右，而用PB估值的话，则历史分位数更低，在市场主要宽基指数当中是历史相对估值最低的指数之一，在历史上的分位数为10%左右。未来随着经济的逐步企稳向好，作为市场中优质中盘股的代表，中证500指数有望迎来估值和盈利的双击。',
            "方向": '乐观'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数依然是当前市场环境下进可攻、退可守的选择。',
            '论据': '我们认为做为一个价值股和成长股、周期股和非周期股、新兴行业和传统行业均相对均衡的中盘宽基指数，中证500指数依然是当前市场环境下进可攻、退可守的选择。',
            "方向": '无'
        },
        {
            '主体': '中证500指数',
            '观点': '中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间。',
            '论据': '我们认为中证500指数当前依然处于历史低估阶段，成长性良好，指数未来上涨的空间依然远大于下跌的空间，我们将努力通过科学的手段增强量化模型的超额收益率水平，以此不断为客户增厚投资收益。',
            "方向": '悲观'
        }
    ]
    print(f"opinion list={pformat(opinion_list)}")
    opinion_list = merge_opinion(opinion_list, subject_field="主体", direction_field="方向")
    print(f"merged opinion list={pformat(opinion_list)}")

    print("===")

# 抽取复盘
if __name__=="__main__":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('review_extract_agent')

    user_input = """
        2024年市场波动较大，全年整体市场收涨。此外24年随着时间阶段不同的市场表现出一定的风格分化，整体上市值的大小在2024年成为很多时间段决定超额收益的重要因子之一。回顾全年的经济数据，我们发现出口的韧性还是比较强劲的，欧美市场和新兴市场轮番有亮点体现，这不仅仅体现在一些行业的补库需求中，还有一些细分行业体现出终端需求渗透率的提升，这毫无疑问是更有持续性的长期方向。
    针对2025年我们保持一个积极的观点，一方面22年以来，国内的制造业产能扩张已经开始放缓，虽然这可能还需要一些时间来消化，但整体上算是一个好的开始，特别是目前亏损比较严重，资产负债表上负担比较重的行业有望先迎来出清。
    此外随着产业结构的变化，一些传统产业的供需结构也在出现变化，此前市场逐渐认知到铜铝的下游电力/新能源的需求占比提升能够在一定程度上对冲传统地产需求的下行，目前随着新能源特别是锂电需求的持续增长，这样的品种也在逐渐变多，不排除未来的2-3年可能有一些传统产业表现出意想不到的机会，这些机会有的在两三年前已经产生类似的逻辑，但由于届时新能源的需求毕竟绝对体量还不足够大，实际的供需上难以兑现，但随着时间的推移，可能未来的几年能够看到实际的兑现。
    """
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")
    print(f"input={pformat(user_input)}")

    the_date = '2024-12-31, 四季度末'

    rsp = agent.run(input=user_input, the_date=the_date, word_cnt=100, direction="", verbose=True)
    rsp = rsp.to_dict()
    review = rsp["output"]
    print(f"review={pformat(review)}")

    print("===")

# 多空打标
if __name__=="__main__1":
    AgentUniverse().start(config_path='../../../../config/config.toml')
    ls_label_agent = AgentManager().get_instance_obj('ls_label_agent')

    opinion_list = {
        '权益市场': '对于权益市场，基金经理表示：2025年银行为代表的高股息分红板块将迎来抢筹行情，这些板块涵盖了许多低估值行业，展现出较强的盈利能力和资本分配能力，增强了组合的防御性。',
        '固收市场': '对于固收市场，基金经理表示：2024年底中国国债收益率快速下降，增强了高分红低波动类债的属性，成为组合管理的重要补充。',
        '金融地产': '对于金融地产，基金经理表示：2025年银行板块因高股息分红而受到关注，展现出较强的盈利能力和资本分配能力。',
        'TMT': '对于TMT，基金经理表示：2025年生成式人工智能进入第二和第三投资阶段，推动数据中心和电气设备的需求变化，AI端侧技术多点开花，利好电子板块，AI眼镜和智能驾驶技术的普及将带来相关软硬件机会。',
        '消费': '对于消费，基金经理表示：2025年扩大内需政策将支持家用电器、汽车、手机等行业的发展，情绪消费如潮玩和美妆也将受益。',
        '制造': '对于制造，基金经理表示：2025年设备更新专项行动将利好汽车和电梯等制造行业，智能驾驶技术的普及也将带来相关制造业的机会。',
        '周期': '对于周期，基金经理表示：2025年周期拐点的资源品、锂电海缆储能等行业将迎来发展机遇。'
    }
    print(f"opinion list={pformat(opinion_list)}")

    rsp = ls_label_agent.run(opinion_list=opinion_list, verbose=True)
    rsp = rsp.to_dict()
    opinion_label = rsp["opinion_label"]
    print(f"opinion label={pformat(opinion_label)}")

    print("===")

# main
if __name__=="__main__1":
    from collections import OrderedDict
    AgentUniverse().start(config_path='../../../../config/config.toml')
    opinion_extract_agent = AgentManager().get_instance_obj('opinion_extract_agent')
    subject_extract_agent = AgentManager().get_instance_obj('subject_extract_agent')
    direction_extract_agent = AgentManager().get_instance_obj('direction_extract_agent')
    subject_match_agent = AgentManager().get_instance_obj('subject_match_agent')

    the_date = '2024-09-30, 三季度末'

    user_input = """
         展望四季度以及明年，美联储年内仍存在25至50个BP降息空间，海外经济存在软着陆可能；我国货币端仍存在操作空间，叠加近期关于鼓励长期资金入市，增持回购等利好方向政策层出不穷，以及四季度我国财政端同样开始发力，帮助地方政府化解债务，刺激消费，国内经济存在复苏可能，A股同样存在较大修复空间。本基金管理人一方面始终保持对于顺周期行业的关注，尤其是近期受益于国内政策端利好底部有望修复的钢铁产业链，建材等地产相关方向，以及我们始终看好同时受益于海内外降息背景下的有色、化工、医药等行业中的绩优股。另外在主线配置之外，本基金管理人也会新增对于新质生产力行业中绩优股的配置倾斜，在严控风险的同时去尽力获取超额收益。
    本基金管理人始终坚守长期主义，坚持追求风险收益比，在自上而下对行业进行精选和配置的基础上，充分发挥投资和研究团队两方面的优势，自下而上深入研究相关标的，精选具有估值优势的优质公司进行布局。团队投资体系的效果得到了充分的体现，未来仍将一如既往，遵循投资框架和逻辑，争取为投资者创造价值。
    """
    print(f"input={pformat(user_input)}")
    # user_input = input("你好，我是一个观点抽取智能助手, 请告诉我你的材料:")

    chain_result = OrderedDict()

    # 观点抽取
    rsp = opinion_extract_agent.run(input=user_input, the_date=the_date)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    chain_result["观点抽取"] = opinion_list
    print(f"opinion list={pformat(opinion_list)}")

    # # 主体抽取
    # rsp = subject_extract_agent.run(opinion_list=opinion_list)
    # rsp = rsp.to_dict()
    # opinion_list = rsp["opinion_list"]
    # chain_result["主体抽取"] = opinion_list
    # print(f"subject extracted opinion list={pformat(opinion_list)}")
    #
    # # 方向判断
    # rsp = direction_extract_agent.run(opinion_list=opinion_list)
    # rsp = rsp.to_dict()
    # opinion_list = rsp["opinion_list"]
    # chain_result["方向判断"] = opinion_list
    # print(f"direction extracted opinion list={pformat(opinion_list)}")

    # # 观点合并
    # opinion_list = merge_opinion(opinion_list, subject_field="主体", direction_field="方向")
    # chain_result["观点合并"] = opinion_list
    # print(f"merged opinion list={pformat(opinion_list)}")

    # 主体匹配
    subject_list = pd.read_excel("/Users/hst/Desktop/111指代词表及板块资产关联.xlsx", 1, index_col=None, header=0, engine="openpyxl")
    subject_list = subject_list["express_nick"].dropna().unique().tolist()
    rsp = subject_match_agent.run(subject_list=subject_list, opinion_list=opinion_list)
    rsp = rsp.to_dict()
    opinion_list = rsp["opinion_list"]
    chain_result["主体匹配"] = opinion_list
    print(f"subject matched opinion list={pformat(opinion_list)}")

    print("===")