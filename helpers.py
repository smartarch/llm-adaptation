from colorama import Fore, Style


def print_prompt(prompt):
    print(Fore.MAGENTA, end="")
    print("PROMPT:")
    print(prompt)
    print(Style.RESET_ALL)


def print_response(response):
    print(Fore.CYAN, end="")
    print("RESPONSE:")
    print(response)
    print(Style.RESET_ALL)
