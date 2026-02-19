# Vibe-Coding: Feedback-Based Automated Verification with No Human Code Inspection, a Feasibility Study

This is an accompanying material to the paper *Vibe-Coding: Feedback-Based Automated Verification with No Human Code Inspection, a Feasibility Study* submitted to VibeX'26.

## Contents

* [`experiments`](./experiments) -- experiments (Jupyter notebooks) ran to produce results in the paper
* [`generated_adaptations/dragon`](./generated_adaptations/dragon), [`generated_adaptations/farm`](./generated_adaptations/farm) -- the raw results (logs) of the experiments
* [DSL](./DSL) -- the domain-specific languages for architecture specification (note that here, we use a YAML syntax instead of the syntax described in paper to simplify parsing) and functional constraints logic (FCL)
  * [`constraint_examples.md`](./DSL/constraint_examples.md) -- examples of FCL constraints
  * [`constraints`](./DSL/constraints) -- implementation of FCL parsing and evaluation
  * [`dragon.yaml`](./DSL/dragon.yaml), [`drones.yaml`](./DSL/drones.yaml) (farm) -- architecture specifications for the two use cases
  * [`dragon_constraints.yaml`](./DSL/dragon_constraints.yaml), [`drones_constraints.yaml`](./DSL/drones_constraints.yaml) (farm) -- functional constraints for the two use cases
  * Jinja [`templates`](./DSL/templates) for prompt generation
* [`generated_adaptations`](./generated_adaptations) -- implementation of the vibe-coding and constraint verification tools
  * [`generator.py`](./generated_adaptations/generator.py) -- the main script for vibe coding (this is used in the Jupyter notebooks in `experiments`)
  * [`tests`](./generated_adaptations/tests) -- implementation of constraints verification as unit tests (inside the tests, the adaptation loop is executed with the generated AM)
  * [`prompts`](./generated_adaptations/prompts) -- prompt templates used when vibe coding (for feedback to the LLM)
  * [`prompts_user`](./generated_adaptations/prompts_user) -- initial prompts for vibe coding (these are automatically generated from the architecture specification DSL files)
  * [`old`](./generated_adaptations/old) -- results of initial experiments (aligning the functional constraints with goals of the system, etc.), not used in the paper
* common implementation
  * [base classes](./base_classes) -- base classes for components, simulation, adaptation (ensemble assignment strategy)
  * [main.py](./main.py) -- the main entry point for running the simulation
* use cases -- implementation of the simulation, hand-coded adaptation strategies, configuration files
  * [Smart Farm](./farm)
  * [Dragon Hunt](./dragon)
* this repository also contains other files used for different experiments with LLMs (please ignore them for the purpose of this paper)
  * [`configs`](./configs) -- for configuration of other experiments
  * [`adaptations`](./adaptations) -- for implementation of other adaptation strategies (e.g., using LLM for direct ensemble resolution)

## Notes to naming

The terms used in the paper and in the code (and naming of folders and files this repository) may differ:

| Paper term              | Code term                                |
|-------------------------|------------------------------------------|
| Dragon Hunt             | dragon                                   |
| Smart Farm              | farm, drones                             |
| functional constraints  | functional constraints, user constraints |
| generic constraints     | system constraints                       |
| adaptation manager      | adaptation, adaptation strategy          |
| initial state           | situation                                |

The naming of folders in results is listed in the respective use case README files.

## Installation

1. (Optional): create virtual environment: `python3 -m venv .venv` and activate it: `source .venv/bin/activate`
2. install requirements: `pip install -r requirements.txt`

To use OpenAI (paid API):

* create API key: <https://platform.openai.com/api-keys>
* rename `.env.example` to `.env` and save the API key there

To use Google AI (free or paid API):

* create API key: <https://aistudio.google.com/app/u/1/apikey>
* rename `.env.example` to `.env` and save the API key there

To use Anthropic (paid API):

* create API key: <https://console.anthropic.com>
* rename `.env.example` to `.env` and save the API key there

## Run

See [experiments](./experiments) for experiment setup, running, and result analysis.

Internally, it uses the vibe coding tool implemented in [`generated_adaptations/generator.py`](generated_adaptations/generator.py) and [`main.py`](main.py) for running simulations of the use cases.
