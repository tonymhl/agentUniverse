# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/11/30 16:20
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: schedule_agent.py
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject


class ScheduleAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['requirement']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        requirement = input_object.get_data('requirement')
        planner_input['requirement'] = requirement
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('schedule_agent')

    # requirement = "我想提取固收+近1年年化超额收益超过0.8，且近3个月正收益概率超过90%的产品"
    requirement = input("你好，我是一个量化分析智能助手, 请告诉我你的量化分析需求:")
    rsp = agent.run(requirement=requirement)
    rsp = rsp.to_dict()
    while (rsp["output"] == "非法需求"):
        requirement = input("您输入的并非有效的量化分析需求，请修改后重新输入:")
        rsp = agent.run(requirement=requirement)
        rsp = rsp.to_dict()
    print(f"requirement={requirement}, output=" + rsp["output"])

    print("===")