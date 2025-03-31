from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.memory.memory import Memory
from agentuniverse.agent.template.openai_protocol_template import OpenAIProtocolTemplate
from agentuniverse.agent.template.react_agent_template import ReActAgentTemplate
from agentuniverse.llm.llm import LLM
from agentuniverse.prompt.prompt import Prompt


class ReActOpenAIAgentTemplate(OpenAIProtocolTemplate, ReActAgentTemplate):

    def customized_execute(self, input_object: InputObject, agent_input: dict, memory: Memory, llm: LLM, prompt: Prompt,
                           **kwargs) -> dict:
        return ReActAgentTemplate.customized_execute(self, input_object, agent_input, memory, llm, prompt, **kwargs)
