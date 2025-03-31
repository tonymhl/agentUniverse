from agentuniverse.agent.input_object import InputObject
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.template.openai_protocol_template import OpenAIProtocolTemplate
from agentuniverse.agent.template.reviewing_agent_template import ReviewingAgentTemplate


class ReviewingOpenAIAgentTemplate(OpenAIProtocolTemplate, ReviewingAgentTemplate):
    def parse_openai_protocol_output(self, output_object: OutputObject) -> OutputObject:
        return output_object

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        self.add_output_stream(input_object.get_data('output_stream', None), '## Reviewing \n\n')
        return super().parse_input(input_object, agent_input)