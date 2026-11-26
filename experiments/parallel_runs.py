"""Running the vibe-coding experiments (generator.py) in parallel.

Each experiment runs in its own process (`subprocess.run`), and threads only wait for the processes, so Python's GIL
does not limit the parallelism. The number of experiments running at the same time is limited globally
(`max_parallel`) and per LLM provider (`max_per_provider`, e.g. "e-infra" or "openai") to avoid throttling of the LLM APIs
(e.g., the e-infra API key allows only 4 parallel requests for all its models together).
"""
import itertools
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Job:
    label: str  # e.g. "all_both/haiku55_01"
    provider: str  # LLM provider (e.g. "e-infra"), used for limiting the parallel runs with the same provider
    folder: Path  # folder of the experiment (the prompt is copied there as 01_user.md)
    prompt: Path | str  # initial prompt
    cmd: list[str]  # command running the generator


def generator_job(results_folder: Path, variant: str, mode: str, prompt_name: str, prompt: str, llm_name: str, llm: str, repeat: int) -> Job:
    """Job running the generator for one experiment (folder `{results_folder}/{variant}_{prompt_name}/{llm_name}_{repeat:02d}`)."""
    folder = results_folder / f"{variant}_{prompt_name}" / f"{llm_name}_{repeat:02d}"
    cmd = [sys.executable, "generated_adaptations/generator.py", f"--folder={folder}", f"--llm={llm}", f"--mode={mode}"]
    return Job(f"{variant}_{prompt_name}/{llm_name}_{repeat:02d}", llm.split(":", 1)[0], folder, prompt, cmd)


def interleave_by_provider(jobs: list[Job]) -> list[Job]:
    """Reorder the jobs round-robin across the providers, so that jobs waiting for the same provider block as few workers as possible."""
    by_provider: dict[str, list[Job]] = {}
    for job in jobs:
        by_provider.setdefault(job.provider, []).append(job)
    return [job for group in itertools.zip_longest(*by_provider.values()) for job in group if job is not None]


def run_experiments(jobs: list[Job], max_parallel: int = 4, max_per_provider: int = 4,
                    show_output: bool = True, output_lines: int = 5) -> dict[str, subprocess.CompletedProcess]:
    """Run the jobs in parallel; at most `max_parallel` at a time and at most `max_per_provider` with the same LLM provider.

    The last `output_lines` lines of the stdout and stderr of each job are printed when the job finishes. Returns the completed processes by job label.
    """
    provider_limits = {job.provider: threading.Semaphore(max_per_provider) for job in jobs}
    print_lock = threading.Lock()
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()

    jobs = interleave_by_provider(jobs)
    start_time = datetime.now()
    finished = 0
    results: dict[str, subprocess.CompletedProcess] = {}

    def log(message: str):
        with print_lock:
            print(message, flush=True)

    def run(job: Job):
        nonlocal finished
        with provider_limits[job.provider]:
            job.folder.mkdir(parents=True, exist_ok=True)
            shutil.copy(job.prompt, job.folder / "01_user.md")
            log(f"[{datetime.now():%H:%M:%S}] started  {job.label}")
            result = subprocess.run(job.cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        with print_lock:
            finished += 1
            elapsed = datetime.now() - start_time
            remaining = elapsed / finished * (len(jobs) - finished)
            print(f"[{datetime.now():%H:%M:%S}] finished {job.label} (exit code {result.returncode}), "
                  f"{finished}/{len(jobs)} done, elapsed: {elapsed}, remaining: {remaining}", flush=True)
            if show_output:  # only the end of the output (the whole log is in the results folder of the experiment)
                print("\n".join(result.stdout.splitlines()[-output_lines:]))
                print("\n".join(result.stderr.splitlines()[-output_lines:]))
            results[job.label] = result
        return result

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        for future in [executor.submit(run, job) for job in jobs]:
            future.result()  # propagate exceptions
    return results
