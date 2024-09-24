from typing import TYPE_CHECKING

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from base_classes.llm_template import LLMTemplate
from helpers import print_prompt, print_response

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


def create_llm(model="gpt-4o-mini-2024-07-18"):
    print("LLM model:", model, "\n")
    llm = ChatOpenAI(model=model, max_tokens=None)
    return llm


def invoke_template(llm: BaseChatModel, template: LLMTemplate, simulation: "SmartFarmSimulation"):
    prompt = template.create_prompt(simulation)
    print_prompt(prompt)
    response = llm.invoke(prompt)
    print_response(response.content)
    return template.process_response(response.content, simulation)
