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
from typing import Literal

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


FARM_GOOD_DAMAGE = 60  # damage threshold for a good adaptation in the farm example
DRAGON_GOOD_STEPS = 15  # average steps threshold for a good adaptation in the dragon example


def parse_arguments(cmdline_args=None):
    parser = argparse.ArgumentParser(description="Command-line arguments for the generator.")
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder. The path should contain `{example}/{variant}/{folder}`")
    parser.add_argument("--max_iterations", type=int, default=10, help="")
    parser.add_argument("--mode", choices=["system", "all", "result", "stats"], required=True, help="Mode of feedback to the LLM.\n"
        "system=feedback from system unit tests\n"
        "all=feedback from system + user constraints unit tests\n"
        "results=feedback from simulation results\n"
        "stats=feedback from simulation statistics (e.g., winrate, average damage, etc)")
    parser.add_argument("--simulation_runs", type=int, default=3, help="Number of runs of simulation for evaluation.")
    parser.add_argument("--llm", type=str, default="gpt-4.1-mini-2025-04-14", help="LLM to use.")
    if cmdline_args is None:
        return parser.parse_args()
    else:
        return parser.parse_args(cmdline_args)


def get_example_variant(folder):
    example = folder.parent.parent.stem
    variant = folder.parent.stem
    return example, variant


### LLM querying


def load_system_prompt():
    system_prompt_path = Path("generated_adaptations/prompts/system.md")
    return system_prompt_path.read_text(encoding="utf-8")


def load_messages(folder: Path) -> dict[str, BaseMessage]:
    files = sorted(folder.glob("*.md"))

    messages: dict[str, BaseMessage] = {
        "00_system": SystemMessage(content=load_system_prompt())
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
    LLMTokenUsage(response, response_time=end_time - start_time).print()

    messages[llm_response_file] = AIMessage(content=response.content)

    (folder / f"{llm_response_file}.md").write_text(response.content, encoding="utf-8")
    print(f"LLM response saved to '{llm_response_file}.md'.")

    code_block = extract_code_block(response.content)
    if not code_block:
        print("No code block found in the LLM response.")
        return None

    code_file = folder / f"code_{llm_response_file.removesuffix('_llm')}.py"
    code_file.write_text(code_block, encoding="utf-8")
    print(f"Code block saved to '{code_file}'.")

    return code_file


def extract_code_block(response_text):
    # This regex looks for content between triple backticks, possibly with a language specifier.
    pattern = r"```(?:\w*\n)?(.*?)```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    if matches:
        return matches[-1].strip()  # there should only be one code block, but if there are multiple, return the last one
    return None


def load_llm(args):
    llm_kwargs = {}
    if "," in args.llm:
        llm_name = args.llm.split(",")[0]
        for arg in args.llm.split(",")[1:]:
            key, value = arg.split("=", 1)
            llm_kwargs[key] = value
    else:
        llm_name = args.llm
    llm = ChatOpenAI(model=llm_name, **llm_kwargs)
    return llm


### Feedback to the LLM


def gather_feedback(args, folder, messages, iteration, code_file):
    if not code_file:
        (folder / "results" / f"code_{iteration * 2:02d}_missing.txt").write_text("No code block found in the LLM response.", encoding="utf-8")
        append_missing_code_block(messages, folder, f"{iteration * 2 + 1:02d}_missing_code")
        return

    # run the tests and the simulation with the generated code
    test_result_system, test_report_system = test_code(folder, code_file, "system")
    test_result_all, test_report_all = test_code(folder, code_file, "all")
    results = run_simulation(folder, code_file, args.simulation_runs)

    if verdict(folder, results):
        return True

    # provide feedback to the LLM
    if args.mode == "system":
        if test_result_system == pytest.ExitCode.OK:
            test_report_file = f"{iteration * 2 + 1:02d}_test"
            append_simulation_report(results, messages, folder, test_report_file, "testpass")
        else:
            simulation_report_file = f"{iteration + 1:02d}_pass"
            append_test_report(test_report_system, messages, folder, simulation_report_file)
    elif args.mode == "all":
        if test_result_all == pytest.ExitCode.OK:
            test_report_file = f"{iteration * 2 + 1:02d}_test"
            append_simulation_report(results, messages, folder, test_report_file, "testpass")
        else:
            simulation_report_file = f"{iteration + 1:02d}_pass"
            append_test_report(test_report_all, messages, folder, simulation_report_file)
    elif args.mode in ["result", "stats"]:
        simulation_report_file = f"{iteration + 1:02d}_{args.mode}"
        append_simulation_report(results, messages, folder, simulation_report_file, args.mode)
    else:
        raise ValueError(f"Unrecognized mode: {args.mode}")


def verdict(folder, results):
    example, _ = get_example_variant(folder)

    if example == "farm":
        damage = results["damage"]
        return damage <= FARM_GOOD_DAMAGE
    elif example == "dragon":
        steps = results["steps"]
        if steps is None:
            return False
        return steps <= DRAGON_GOOD_STEPS
    else:
        raise ValueError(f"Unrecognized example: {example}")


### Unit tests


def test_code(folder, code_file, tests: Literal["system", "all"]):
    example, variant = get_example_variant(folder)
    adaptation_name = folder.stem + "/" + code_file.stem
    cmd = [
        "pytest", "generated_adaptations/tests", "-q", "--tb=short", "-rfExX", "--show-capture=no", "--color=no",
        f"--example={example}", f"--adaptation_name={adaptation_name}", f"--variant={variant}", f"--tests={tests}"
    ]
    print(f"Running tests ({tests}):", " ".join(cmd))
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()
    # env['COLUMNS'] = '160'  # make output wider to avoid truncation of pytest short summary
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    print(f"Test exit code: {result.returncode}")
    (folder / "results" / f"{code_file.stem}_test_{tests}_{'pass' if result.returncode == 0 else 'fail'}.txt")\
        .write_text(str(result.returncode) + "\n" + result.stdout + result.stderr, encoding="utf-8")
    if result.returncode not in [pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED]:
        raise RuntimeError(f"Error in running tests:\n{result.stderr}")
    return result.returncode, result.stdout + result.stderr


def append_test_report(test_report, messages, folder, test_report_file):
    prompt_template = PromptTemplate.from_file("generated_adaptations/prompts/test.md", encoding="utf-8")
    test_prompt = prompt_template.format(test_report=test_report)
    (folder / f"{test_report_file}.md").write_text(test_prompt, encoding="utf-8")
    messages[test_report_file] = HumanMessage(content=test_prompt)


def append_missing_code_block(messages, folder, test_report_file):
    prompt_template = PromptTemplate.from_file("generated_adaptations/prompts/missing_code.md", encoding="utf-8")
    test_prompt = prompt_template.format()
    (folder / f"{test_report_file}.md").write_text(test_prompt, encoding="utf-8")
    messages[test_report_file] = HumanMessage(content=test_prompt)


### Simulation running


def prepare_config(folder, code_file):
    example, variant = get_example_variant(folder)
    adaptation_name = folder.stem + "/" + code_file.stem
    return adaptation_config(adaptation_name, example, variant)


def run_simulation(folder, code_file, repeats=3, start=1):
    print(f"Running simulation for '{code_file}'.")
    example, variant = get_example_variant(folder)

    configs = simulation_configs(example=example, constraints=variant == "constraints")
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
                plot_file = log_file.replace(".ansi", ".png")
                shutil.copy(plot_file, folder / "results" / f"{code_file.stem}_plot.png")
        except (ValueError, FileNotFoundError):
            pass

    if example == "farm":
        return analyze_farm_simulation_results(log_files, folder, code_file)
    elif example == "dragon":
        return analyze_dragon_simulation_results(log_files, folder, code_file)
    else:
        raise ValueError(f"Unrecognized example: {example}")


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

    result = results.mean().to_dict()
    (folder / "results" / f"{code_file.stem}_simulation_result.json").write_text(json.dumps(result), encoding="utf-8")

    print(f"Average damage: {result['damage']:.1f}")
    return result


def analyze_dragon_simulation_results(log_files, folder, code_file):
    results = pd.DataFrame(columns=["win", "steps", "warriors", "farmers", "farming", "attacking", "spawned_farmers", "spawned_warriors"])

    for log_file in log_files:
        try:
            csv_file = log_file.replace(".ansi", ".csv")
            csv_data = pd.read_csv(csv_file, encoding="utf-8")

            results.loc[len(results)] = [any(csv_data.dragon_hp <= 0), csv_data.step.max(),
                                         csv_data.warriors_village.iloc[-1] + csv_data.warriors_cave.iloc[-1],
                                         csv_data.farmers_village.iloc[-1] + csv_data.farmers_cave.iloc[-1],
                                         csv_data.FARMING.mean(), csv_data.ATTACKING.mean(),
                                         csv_data.spawned_farmers.sum(), csv_data.spawned_warriors.sum()]
        except (FileNotFoundError, ValueError):
            pass

    result = results[["warriors", "farmers", "farming", "attacking", "spawned_farmers", "spawned_warriors"]].mean().to_dict()
    result["games_played"] = len(log_files)
    result["wins"] = int(results["win"].sum())
    result["losses"] = len(log_files) - result["wins"]
    result["winrate"] = result["wins"] / len(log_files)
    result["steps"] = results[results["win"]].steps.mean() if len(results[results["win"]]) > 0 else None

    (folder / "results" / f"{code_file.stem}_simulation_result.json").write_text(json.dumps(result), encoding="utf-8")

    print(f"Winrate: {result['winrate']:.1f}, avg. steps: {result['steps']}")
    return result


def append_simulation_report(results, messages, folder, report_file, mode):
    example, _ = get_example_variant(folder)
    if example == "farm":
        prompt_template = PromptTemplate.from_file(f"generated_adaptations/prompts/farm_{mode}.md", encoding="utf-8")
        simulation_prompt = prompt_template.format(**results)
    elif example == "dragon":
        prompt_template = PromptTemplate.from_file(f"generated_adaptations/prompts/dragon_{mode}.md", encoding="utf-8")
        if results["steps"] is None:
            results["steps"] = "N/A"
        else:
            results["steps"] = f"{results['steps']:.1f}"
        simulation_prompt = prompt_template.format(**results)
    else:
        raise ValueError(f"Unrecognized example: {example}")
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
    if "01_user" not in messages:
        print(f"Error: Prompt is missing in {folder}. Create a prompt file named '01_user.md' in the folder.")
        return
    if len(messages) > 2:
        print(f"Error: experiment in {folder} was already ran. Aborting.")
        return

    llm = load_llm(args)

    for iteration in range(1, args.max_iterations + 1):
        # query LLM for code generation
        llm_response_file = f"{iteration * 2:02d}_llm"
        code_file = query_llm(llm, messages, folder, llm_response_file)

        if gather_feedback(args, folder, messages, iteration, code_file):
            print(f"The generated code produces a good result (iteration: {iteration}). Stopping further iterations.")
            break
    else:
        print(f"Reached the maximum number of iterations ({args.max_iterations}). Stopping.")


if __name__ == "__main__":
    main()
