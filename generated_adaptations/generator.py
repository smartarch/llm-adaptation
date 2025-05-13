import argparse
from pathlib import Path
import re
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)  # take environment variables from .env


def parse_arguments():
    parser = argparse.ArgumentParser(description="Command-line arguments for the generator.")
    parser.add_argument("--folder", type=str, required=True, help="Path to the folder.")
    parser.add_argument("--retries_test", type=int, default=3, help="Number of retries for failing unit tests.")
    parser.add_argument("--retries_simulation", type=int, default=1, help="Number of retries for simulation results.")
    return parser.parse_args()


def load_system_prompt():
    system_prompt_path = Path("generated_adaptations/prompts/system.md")
    if not system_prompt_path.is_file():
        print(f"Error: System prompt file '{system_prompt_path}' does not exist.")
        exit(1)
    with system_prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


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


def main():
    args = parse_arguments()
    folder = Path(args.folder)

    messages, last = load_messages(folder)
    print(f"Loaded {last} messages from {folder}.")
    if len(messages) < 2 or last % 2 == 0:
        print(f"Error: Prompt is missing in {folder}.")
        return

    llm = ChatOpenAI(model="gpt-4o-mini")
    query_llm(folder, messages, last, llm)


if __name__ == "__main__":
    main()
