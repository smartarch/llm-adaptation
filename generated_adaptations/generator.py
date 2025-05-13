import argparse
import os
import re
import subprocess
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from langchain.prompts import PromptTemplate, load_prompt
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv(), override=True)  # take environment variables from .env


def parse_arguments():
    parser = argparse.ArgumentParser(description="Command-line arguments for the generator.")
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder.")
    parser.add_argument("--retries_test", type=int, default=3, help="Number of retries for failing unit tests.")
    parser.add_argument("--retries_simulation", type=int, default=1, help="Number of retries for simulation results.")
    return parser.parse_args()


def load_system_prompt():
    system_prompt_path = Path("generated_adaptations/prompts/system.md")
    return system_prompt_path.read_text(encoding="utf-8")


def load_test_prompt_template():
    return PromptTemplate.from_file("generated_adaptations/prompts/test.md", encoding="utf-8")


def load_messages(folder: Path):
    files = sorted(folder.glob("*.md"))

    messages: list[BaseMessage] = [SystemMessage(content=load_system_prompt())]
    number = 0

    for number, file in enumerate(files, start=1):
        content = file.read_text(encoding="utf-8")
        if number % 2 == 1:
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))

    return messages, number


def query_llm(folder, messages, last, llm):
    next_num = last + 1
    next_llm_file = folder / f"{next_num}_llm.md"
    if next_llm_file.is_file():
        print(f"LLM response file '{next_llm_file}' already exists. Refusing to overwrite.")
        return

    response = llm.invoke(messages).content

    next_llm_file.write_text(response, encoding="utf-8")
    print(f"LLM response saved to '{next_llm_file}'.")

    code_block = extract_code_block(response)
    if code_block:
        code_file = folder / f"code_{next_num // 2}.py"
        code_file.write_text(code_block, encoding="utf-8")
        print(f"Code block saved to '{code_file}'.")
    else:
        print("No code block found in the LLM response.")


def extract_code_block(response_text):
    # This regex looks for content between triple backticks, possibly with a language specifier.
    pattern = r"```(?:\w*\n)?(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return None


def test_code(folder, code_file):
    example = folder.parent.stem
    adaptation_name = folder.stem + "/" + code_file.stem
    cmd = [
        "pytest", "generated_adaptations/tests", "-q", "--tb=no",
        f"--example={example}", f"--adaptation_name={adaptation_name}"
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()
    env['COLUMNS'] = '160'
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    return result.returncode, result.stdout + result.stderr


def main():
    args = parse_arguments()
    folder = Path(args.folder)

    messages, last = load_messages(folder)
    print(f"Loaded {last} messages from {folder}.")
    if len(messages) < 2 or last % 2 == 0:
        print(f"Error: Prompt is missing in {folder}.")
        return

    # llm = ChatOpenAI(model="gpt-4o-mini")
    # query_llm(folder, messages, last, llm)

    # TODO: generalize (replace numbers with variables), run in a loop with max args.retries_test iterations
    result, test_report = test_code(folder, folder / "code_1.py")
    print(f"Test exit code: {result}")

    test_prompt = load_test_prompt_template().format(test_report=test_report)
    (folder / f"{3}_test.md").write_text(test_prompt, encoding="utf-8")


if __name__ == "__main__":
    main()
