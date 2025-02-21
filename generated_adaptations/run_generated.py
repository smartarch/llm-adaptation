import subprocess
import os
import sys
from pathlib import Path


def run(configs, repeats=10, start=1):
    print(configs)
    avg_damage = 0
    for repeat in range(repeats):
        print(f"  Run #{repeat + start}/{repeats + start - 1}")

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


# FARM

farm_configs = ["farm/configs/default.yaml", "generated_adaptations/configs/generated.yaml", "farm/configs/config_no_battery.yaml"]
farm_variants = [f"{llm}_{variant}_1" for llm in ("4o", "o3") for variant in ("default", "sd1", "step-by-step", "strategy")]
# farm_variants = ["4o_default_1"]

# prepare configuration files
for variant in farm_variants:
    variant_path = Path(f"generated_adaptations/configs/farm/{variant}.yaml")
    if not variant_path.exists():
        variant_path.write_text(f"""name: {variant}
log_dir.append: /{variant}
adaptation_name: generated_adaptations.farm.{variant}.TODO
adaptation_params:
  adapt_every: 10""")

# for variant in farm_variants:
#     configs = farm_configs + [f"generated_adaptations/configs/farm/{variant}.yaml"]
#     run(configs, repeats=2)
