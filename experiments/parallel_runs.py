"""Running the vibe-coding experiments (generator.py) in parallel.

Each experiment runs in its own process (`subprocess.run`), and threads only wait for the processes, so Python's GIL
does not limit the parallelism. The number of experiments running at the same time is limited globally
(`max_parallel`) and per LLM (`max_per_llm`, `default_per_llm`) to avoid throttling of the LLM APIs.
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
    llm_name: str  # key used for limiting the parallel runs with the same LLM
    folder: Path  # folder of the experiment (the prompt is copied there as 01_user.md)
    prompt: Path | str  # initial prompt
    cmd: list[str]  # command running the generator


def generator_job(results_folder: Path, variant: str, mode: str, prompt_name: str, prompt: str, llm_name: str, llm: str, repeat: int) -> Job:
    """Job running the generator for one experiment (folder `{results_folder}/{variant}_{prompt_name}/{llm_name}_{repeat:02d}`)."""
    folder = results_folder / f"{variant}_{prompt_name}" / f"{llm_name}_{repeat:02d}"
    cmd = [sys.executable, "generated_adaptations/generator.py", f"--folder={folder}", f"--llm={llm}", f"--mode={mode}"]
    return Job(f"{variant}_{prompt_name}/{llm_name}_{repeat:02d}", llm_name, folder, prompt, cmd)


def interleave_by_llm(jobs: list[Job]) -> list[Job]:
    """Reorder the jobs round-robin across the LLMs, so that jobs waiting for the same LLM block as few workers as possible."""
    by_llm: dict[str, list[Job]] = {}
    for job in jobs:
        by_llm.setdefault(job.llm_name, []).append(job)
    return [job for group in itertools.zip_longest(*by_llm.values()) for job in group if job is not None]


def run_experiments(jobs: list[Job], max_parallel: int = 4, max_per_llm: dict[str, int] | None = None, default_per_llm: int = 1,
                    show_output: bool = True) -> dict[str, subprocess.CompletedProcess]:
    """Run the jobs in parallel; at most `max_parallel` at a time and at most `max_per_llm[llm]` (or `default_per_llm`) per LLM.

    The output of each job is printed when the job finishes. Returns the completed processes by job label.
    """
    max_per_llm = max_per_llm or {}
    llm_limits = {job.llm_name: threading.Semaphore(max_per_llm.get(job.llm_name, default_per_llm)) for job in jobs}
    print_lock = threading.Lock()
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + os.pathsep + os.getcwd()

    jobs = interleave_by_llm(jobs)
    start_time = datetime.now()
    finished = 0
    results: dict[str, subprocess.CompletedProcess] = {}

    def log(message: str):
        with print_lock:
            print(message, flush=True)

    def run(job: Job):
        nonlocal finished
        with llm_limits[job.llm_name]:
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
            if show_output:
                print(result.stdout)
                print(result.stderr)
            results[job.label] = result
        return result

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        for future in [executor.submit(run, job) for job in jobs]:
            future.result()  # propagate exceptions
    return results
