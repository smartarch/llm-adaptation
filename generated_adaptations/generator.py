import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
import sys
import textwrap
import time

import numpy as np
import pandas as pd
import pytest
from dotenv import find_dotenv, load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from adaptations.llm import LLMTokenUsage
from generated_adaptations.generator_utils import adaptation_config, simulation_configs
from utils import Logger

load_dotenv(find_dotenv(), override=True)  # take environment variables from .env


def parse_arguments(cmdline_args=None):
    parser = argparse.ArgumentParser(description="Command-line arguments for the generator.")
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder.")
    parser.add_argument("--retries_test", type=int, default=3, help="Number of retries for failing unit tests.")
    parser.add_argument("--retries_simulation", type=int, default=2, help="Number of retries for simulation results.")
    parser.add_argument("--llm", type=str, default="gpt-4.1-mini-2025-04-14", help="LLM to use.")
    if cmdline_args is None:
        return parser.parse_args()
    else:
        return parser.parse_args(cmdline_args)


### LLM querying


def load_system_prompt():
    system_prompt_path = Path("generated_adaptations/prompts/system.md")
    return system_prompt_path.read_text(encoding="utf-8")


def load_messages(folder: Path) -> dict[str, BaseMessage]:
    files = sorted(folder.glob("*.md"))

    messages: dict[str, BaseMessage] = {
        "00-system": SystemMessage(content=load_system_prompt())
    }

    for file in files:
        content = file.read_text(encoding="utf-8")
        if "llm" in file.stem:
            messages[file.stem] = AIMessage(content=content)
        else:
            messages[file.stem] = HumanMessage(content=content)

    return messages


def query_llm(llm, messages, folder, llm_response_file):
    print(f"Querying LLM with prompt {list(messages)[-1]}.")
    start_time = time.time()
    response = llm.invoke(list(messages.values()))
    end_time = time.time()
    messages[llm_response_file] = AIMessage(content=response.content)

    (folder / f"{llm_response_file}.md").write_text(response.content, encoding="utf-8")
    print(f"LLM response saved to '{llm_response_file}.md'.")

    code_block = extract_code_block(response.content)
    if not code_block:
        raise ValueError("No code block found in the LLM response.")

    code_file = folder / f"code_{llm_response_file.removesuffix('_llm')}.py"
    code_file.write_text(code_block, encoding="utf-8")
    print(f"Code block saved to '{code_file}'.")

    LLMTokenUsage(response, response_time=end_time - start_time).print()

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
        "pytest", "generated_adaptations/tests", "-q", "--tb=short", "-rA", "--show-capture=no", "--color=no",
        f"--example={example}", f"--adaptation_name={adaptation_name}"
    ]
    print("Running tests:", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()
    # env['COLUMNS'] = '160'  # make output wider to avoid truncation of pytest short summary
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    print(f"Test exit code: {result.returncode}")
    (folder / "results" / f"{code_file.stem}_test_{'pass' if result.returncode == 0 else 'fail'}.txt")\
        .write_text(str(result.returncode) + "\n" + result.stdout + result.stderr, encoding="utf-8")
    if result.returncode not in [pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED]:
        raise RuntimeError(f"Error in running tests:\n{result.stderr}")
    return result.returncode, result.stdout + result.stderr


def append_test_report(test_report, messages, folder, test_report_file):
    prompt_template = PromptTemplate.from_file("generated_adaptations/prompts/test.md", encoding="utf-8")
    test_prompt = prompt_template.format(test_report=test_report)
    (folder / f"{test_report_file}.md").write_text(test_prompt, encoding="utf-8")
    messages[test_report_file] = HumanMessage(content=test_prompt)


### Simulation running


def prepare_config(folder, code_file):
    example = folder.parent.stem
    adaptation_name = folder.stem + "/" + code_file.stem
    return adaptation_config(adaptation_name, example)


def run_simulation(folder, code_file, repeats=3, start=1):
    print(f"Running simulation for '{code_file}'.")

    configs = simulation_configs(example=folder.parent.stem)
    extra_config = '--extra_config=' + json.dumps(prepare_config(folder, code_file))

    log_files = []
    for repeat in range(repeats):
        print(f"  Run #{repeat + start}/{repeats + start - 1}", end=': ')

        run_args = [sys.executable, "main.py", *configs, extra_config, "-s", str(repeat + start), "-e", str(repeat + start)]
        print(" ".join(["python"] + run_args[1:]))

        # set the Python path
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
            log_file = stdout.partition("log_file_path: ")[2].partition("\n")[0].strip()
            log_files.append(log_file)
            if repeat == 0:
                # TODO: this works only for farm
                plot_file = log_file.replace(".ansi", ".png")
                shutil.copy(plot_file, folder / "results" / f"{code_file.stem}_plot.png")
        except ValueError:
            pass

    return analyze_farm_simulation_results(log_files, folder, code_file)


def analyze_farm_simulation_results(log_files, folder, code_file):
    results = pd.DataFrame(columns=["damage", "protecting", "moving", "coverage"])

    for log_file in log_files:
        try:
            log = Path(log_file).read_text(encoding="utf-8")
            damage = log.partition("damage: ")[2].partition("\n")[0]

            csv_file = log_file.replace(".ansi", ".csv")
            csv_data = pd.read_csv(csv_file, encoding="utf-8")

            def coverage_of_most_threatened(row):
                most_threatened = np.argmax([row[f"Field_{f}_threat_level"] for f in range(1, 5)]) + 1
                return row[f"Field_{most_threatened}_protecting_drones"] / (row[f"Field_{most_threatened}_protecting_drones"] + row[f"Field_{most_threatened}_drones_for_full_protection"])

            most_threatened_coverage = csv_data.apply(coverage_of_most_threatened, axis=1)

            results.loc[len(results)] = [int(damage), csv_data["PROTECTING"].mean(), csv_data["MOVING_TO_FIELD"].mean(), most_threatened_coverage.mean()]
        except (FileNotFoundError, ValueError):
            pass

    (folder / "results" / f"{code_file.stem}_simulation_result.txt").write_text(
        f"Average damage: {results['damage'].mean():.1f}\n"
        f"Protecting: {results['protecting'].mean():.1f}\n"
        f"Moving: {results['moving'].mean():.1f}\n"
        f"Coverage of most threatened field: {results['coverage'].mean():.1f}\n"
        , encoding="utf-8")

    print(f"Average damage: {results['damage'].mean():.1f}")
    return results.mean().to_dict()


def append_simulation_report(results, messages, folder, report_file):
    prompt_template = PromptTemplate.from_file("generated_adaptations/prompts/simulation.md", encoding="utf-8")  # TODO: this is a template for farm
    verdict = "is a good result. Good job!" if results["damage"] < 60 else "is not a good result and needs improvement."
    simulation_prompt = prompt_template.format(**results, verdict=verdict)
    (folder / f"{report_file}.md").write_text(simulation_prompt, encoding="utf-8")
    messages[report_file] = HumanMessage(content=simulation_prompt)


### Main


def main(cmdline_args=None):
    args = parse_arguments(cmdline_args)
    folder = Path(args.folder)
    (folder / "results").mkdir(parents=True, exist_ok=True)
    sys.stdout = Logger(folder / "results" / "log.ansi")

    messages = load_messages(folder)
    print(f"Loaded {len(messages)} messages from {folder}.")
    if "01_01_user" not in messages:
        print(f"Error: Prompt is missing in {folder}. Create a prompt file named '01_01_user.md' in the folder.")
        return
    if len(messages) > 2:
        print(f"Error: experiment in {folder} was already ran. Aborting.")
        # TODO: the message-existence checks below do not work correctly. For now, we just prohibit running the experiment again (or continuing). This can be removed if the checks are fixed (including correctly handling passing tests, etc.).
        return

    llm = ChatOpenAI(model=args.llm)

    for iteration in range(1, args.retries_simulation + 2):
        for test in range(1, args.retries_test + 2):
            # query LLM for code generation
            llm_response_file = f"{iteration:02d}_{test * 2:02d}_llm"
            if llm_response_file in messages:
                print(f"LLM response file '{llm_response_file}' already exists. Skipping LLM query.")
                continue
            code_file = query_llm(llm, messages, folder, llm_response_file)

            # run unit tests on the generated code
            test_report_file = f"{iteration:02d}_{test * 2 + 1:02d}_test"
            if test_report_file in messages:
                print(f"Test report file '{test_report_file}' already exists. Skipping tests.")
                continue
            result, test_report = test_code(folder, code_file)
            results = run_simulation(folder, code_file)

            if result == 0:
                break
            append_test_report(test_report, messages, folder, test_report_file)
        else:
            print(f"Tests failed {args.retries_test + 1} times. Exiting.")
            return

        simulation_report_file = f"{iteration + 1:02d}_01_simulation"
        if simulation_report_file in messages:
            print(f"Simulation report file '{simulation_report_file}' already exists. Skipping simulation.")
            continue
        append_simulation_report(results, messages, folder, simulation_report_file)


if __name__ == "__main__":
    main()
