# !/usr/bin/env python3
# -*- coding:utf-8 -*-

# @Time    : 2024/12/17 11:37
# @Author  : maidong
# @Email   : hushuntai.hst@antgroup.com
# @FileName: free_answer_agent.py
from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject


class FreeAnswerAgent(Agent):
    def input_keys(self) -> list[str]:
        return ['input']

    def output_keys(self) -> list[str]:
        return ['output']

    def parse_input(self, input_object: InputObject, planner_input: dict) -> dict:
        planner_input['input'] = input_object.get_data('input')
        return planner_input

    def parse_result(self, planner_result: dict) -> dict:
        return planner_result


if __name__ == '__main__':
    from agentuniverse.base.agentuniverse import AgentUniverse
    from agentuniverse.agent.agent_manager import AgentManager

    AgentUniverse().start(config_path='../../../../config/config.toml')
    agent = AgentManager().get_instance_obj('free_answer_agent')

    user_input = input("你好，说点什么吧:")
    rsp = agent.run(input=user_input)
    rsp = rsp.to_dict()
    print(f"input={user_input}, output=" + rsp["output"])

    print("===")