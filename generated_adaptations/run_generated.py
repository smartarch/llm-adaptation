import subprocess
import os
import sys
from pathlib import Path


def run(name, repeats=10, start=1):
    print(name)
    avg_damage = 0
    for repeat in range(repeats):
        print(f"  Run #{repeat + start}/{repeats + start - 1}")

        configs = ["farm/configs/default.yaml", "generated_adaptations/configs/generated.yaml",
                   "farm/configs/config_no_battery.yaml", f"generated_adaptations/configs/{name}.yaml"]

        run_args = [sys.executable, "main.py", *configs, "-s", str(repeat + start), "-e", str(repeat + start)]
        # if repeat % 10 == 0:
        #     run.append("--animation")

        # disable TF errors
        env = dict(os.environ, TF_CPP_MIN_LOG_LEVEL="3")

        result = subprocess.run(run_args, capture_output=True, env=env)
        stdout = result.stdout.decode("utf-8")
        stderr = result.stderr.decode("utf-8")

        damage = stdout.partition("damage: ")[2].partition("\n")[0]
        print(f"    Damage: {damage}")

        if stderr:
            print(stderr)

        avg_damage += int(damage)

    avg_damage /= repeats
    print(f"Average damage: {avg_damage}")


# change working directory to project root
workdir = Path(__file__).parent.parent
os.chdir(workdir)


# name = "gpt4o_1"
name = "o3_1"
run(name, repeats=2)
