import argparse
import json
import os
import re
import subprocess
from pathlib import Path
import sys
import textwrap

from dotenv import find_dotenv, load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from adaptations.llm import LLMTokenUsage
from generated_adaptations.generator_utils import adaptation_config, simulation_configs

load_dotenv(find_dotenv(), override=True)  # take environment variables from .env


def parse_arguments():
    parser = argparse.ArgumentParser(description="Command-line arguments for the generator.")
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder.")
    parser.add_argument("--retries_test", type=int, default=3, help="Number of retries for failing unit tests.")
    parser.add_argument("--retries_simulation", type=int, default=1, help="Number of retries for simulation results.")
    return parser.parse_args()


### LLM querying


def load_system_prompt():
    system_prompt_path = Path("generated_adaptations/prompts/system.md")
    return system_prompt_path.read_text(encoding="utf-8")


def load_messages(folder: Path):
    files = sorted(folder.glob("*.md"))

    messages: list[BaseMessage] = [SystemMessage(content=load_system_prompt())]

    for number, file in enumerate(files, start=1):
        content = file.read_text(encoding="utf-8")
        if number % 2 == 1:
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))

    return messages


def query_llm(folder, messages, llm):
    next_num = len(messages)
    next_llm_file = folder / f"{next_num}_llm.md"
    if next_llm_file.is_file():
        print(f"LLM response file '{next_llm_file}' already exists. Refusing to overwrite.")
        return

    print(f"Querying LLM with prompt {len(messages) - 1}.")
    response = llm.invoke(messages)
    messages.append(AIMessage(content=response.content))

    next_llm_file.write_text(response.content, encoding="utf-8")
    print(f"LLM response saved to '{next_llm_file}'.")

    code_block = extract_code_block(response.content)
    if not code_block:
        raise ValueError("No code block found in the LLM response.")
    
    code_file = folder / f"code_{next_num // 2}.py"
    code_file.write_text(code_block, encoding="utf-8")
    print(f"Code block saved to '{code_file}'.")

    LLMTokenUsage(response).print()

    return code_file


def extract_code_block(response_text):
    # This regex looks for content between triple backticks, possibly with a language specifier.
    pattern = r"```(?:\w*\n)?(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return None


### Unit tests


def test_code(folder, code_file):
    example = folder.parent.stem
    adaptation_name = folder.stem + "/" + code_file.stem
    cmd = [
        "pytest", "generated_adaptations/tests", "-q", "--tb=no", "-rA",
        f"--example={example}", f"--adaptation_name={adaptation_name}"
    ]
    print("Running tests:", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()
    env['COLUMNS'] = '160'
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    print(f"Test exit code: {result.returncode}")
    return result.returncode, result.stdout + result.stderr


def append_test_report(folder, test_report, messages):
    prompt_template = PromptTemplate.from_file("generated_adaptations/prompts/test.md", encoding="utf-8")
    test_prompt = prompt_template.format(test_report=test_report)
    (folder / f"{len(messages)}_test.md").write_text(test_prompt, encoding="utf-8")
    messages.append(HumanMessage(content=test_prompt))


### Simulation running


def prepare_config(folder, code_file):
    example = folder.parent.stem
    adaptation_name = folder.stem + "/" + code_file.stem
    return adaptation_config(adaptation_name, example)


def run_simulation(folder, code_file, repeats=2, start=1):
    print(f"Running simulation for {folder} with code file {code_file}.")

    configs = simulation_configs(example=folder.parent.stem)
    extra_config = '--extra_config=' + json.dumps(prepare_config(folder, code_file))

    damages = []
    for repeat in range(repeats):
        print(f"  Run #{repeat + start}/{repeats + start - 1}")

        run_args = [sys.executable, "main.py", *configs, extra_config, "-s", str(repeat + start), "-e", str(repeat + start)]

        # disable TF errors, set python path
        env = os.environ.copy()
        env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()

        result = subprocess.run(run_args, capture_output=True, env=env, check=False)
        stdout = result.stdout.decode("utf-8")
        stderr = result.stderr.decode("utf-8")

        if stderr:
            stderr_lines = stderr.splitlines()
            stderr = '\n'.join(stderr_lines[-3:])
            print(f"    StdErr: {len(stderr_lines)} lines")
            print(textwrap.indent(stderr, "    "))

        try:
            damage = stdout.partition("damage: ")[2].partition("\n")[0]
            print(f"    Damage: {damage}")
            damages.append(int(damage))
        except ValueError:
            pass

    if len(damages) > 0:
        avg_damage = sum(damages) / len(damages)
        print(f"Average damage: {avg_damage:.1f}")
    else:
        avg_damage = None
    if repeats != len(damages):
        print(f"Errors: {repeats - len(damages)}")
    print()

    return avg_damage


### Main


def main():
    args = parse_arguments()
    folder = Path(args.folder)

    messages = load_messages(folder)
    print(f"Loaded {len(messages)} messages from {folder}.")
    if len(messages) < 2 or len(messages) % 2 != 0:
        print(f"Error: Prompt is missing in {folder}.")
        return

    llm = ChatOpenAI(model="gpt-4o-mini")

    existing_tests = len(list(folder.glob("*_test.md")))
    code_file = max(folder.glob("code_*.py"))
    for _ in range(existing_tests, args.retries_test):
        code_file = query_llm(folder, messages, llm)
        result, test_report = test_code(folder, code_file)
        if result == 0:
            break
        append_test_report(folder, test_report, messages)

    run_simulation(folder, code_file)

    # TODO: use the simulation results to improve the code


if __name__ == "__main__":
    main()
