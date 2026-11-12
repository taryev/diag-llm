# diag-llm

A hands-on project exploring LLM applications.

**Challenge:** Extracting structured diagnoses from unstructured clinical notes using Large Language Models.

**Approach:** there are many ways to reach this goal, and with the rapid growing of the LLM-tooling ecosystem, this proposal can become outdated quickly. That said, it is an approach that I designed without following/copying an existing project, I went with the flow and my documentation readings. This was an exciting weekend project.

The idea here is to use an LLM to extract diagnoses from free-text medical notes (for this particular case, discharge notes) into a structured output with [ICD-11](https://www.who.int/standards/classifications/classification-of-diseases) MMS coding. The choice of LLM is arbitrary (I needed something that would run easily on my laptop). Inferring diagnoses not explicitly stated in the medical note is out of scope.

**Results:** Since I am using a local, quantized LLM, results are not perfect. The most common error is that the model fails to call the tool (despite the system prompt, can be tweaked by code). Overall, the results are encouraging, and in most cases only the discharge diagnoses are extracted (not the past medical history or the ruled-out diagnoses).

## Design

### Stack

- Python + [uv](https://docs.astral.sh/uv/): environment
- [Streamlit](https://streamlit.io/) + SQLite: web app
- [Llama](https://llama.app): Local LLM inference and API
- [ICD API](https://icd.who.int/icdapi): REST API for ICD-11 coding *(API key needed)*
- [MIMIC-IV-Notes](https://www.physionet.org/content/mimic-iv-note/2.2/) + PostgreSQL: real-life deidentified medical notes database *(credentialing needed)*

My homelab does not have a dedicated GPU, so I run Llama on my laptop, which has an NVIDIA GeForce RTX 4050 Laptop GPU with 6 GB VRAM. This is enough to run a quantized version of [Gemma 4](https://huggingface.co/google/gemma-4-E4B-it). The MIMIC database runs in a Docker container on my homelab.

**Important:** do not use MIMIC-derived data if you plan to use a third-party LLM service provider as it may break [PhysioNet data usage agreement](https://physionet.org/news/post/llm-responsible-use/).

### How it works?

1. The LLM receives the system prompt and the user prompt (i.e., the medical note), no LLM history is sent (each note is processed independently).
2. The LLM *follows* the system prompt and attempts to identify established diagnoses.
3. The LLM calls a tool for each diagnosis it identifies.
    - The tool calls the ICD API.
    - The API returns a corresponding ICD code (or an error).
4. The LLM gathers the tool call results and generates JSON that follows a JSON schema.

## Installation

### Prerequisites

This project uses [uv](https://github.com/astral-sh/uv) and [Llama](https://llama.app/), follow their instructions to install them. Llama can be replaced by any inference tool/API compatible with the OpenAI API.

**Note:** To use real-world examples, this project uses MIMIC as a data source. The dataset is only available after completing the credentialing process on the PhysioNet website. Using MIMIC is optional: you can still access the LLM playground without connecting to a database.

### Clone the repository

```bash
git clone https://github.com/taryev/diag-llm.git
cd diag-llm
```

### Install Python dependencies

```bash
uv sync
```

### Setup secrets

Edit `secrets.toml` according to your environment.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

## Usage

Start Llama, feel free to try other models.

```bash
llama serve -hf ggml-org/gemma-4-e4b-it-GGUF:Q4_0
```

Start Streamlit with uv's virtual environment

```bash
uv run streamlit run app.py
```
