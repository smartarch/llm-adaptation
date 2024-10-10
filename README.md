# llm-adaptation

## Installation

1. (Optional): create virtual environment: `python3 -m venv .venv` and activate it: `source .venv/bin/activate`
2. install requirements: `pip install -r requirements.txt`

To use OpenAI (paid API):

* create API key: <https://platform.openai.com/api-keys>
* rename `.env.example` to `.env` and save the API key there

## Run

The simulation is run via the `main.py` file. It is necessary to specify the configuration with command line arguments. The first argument should be `configs/config.yaml` (configuration of the smart farm scenario), the second argument should be the configuration of the adaptation (e.g., `configs/fake.yaml` for a random adaptation used for debugging).

```bash
python main.py configs/config.yaml configs/fake.yaml 
```
