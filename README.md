# 📜 Text as Data Module

<!-- EDIT with your badge link -->
[![Notebook check](https://github.com/espm-157/text-template/actions/workflows/main.yml/badge.svg)](https://github.com/espm-157/text-template/actions/workflows/main.yml)

## Team Members

🦸
🦹

## 🎓 Learning Objectives

📜 Treating text as data: from documents to paragraphs to tables  
🔤 Regular expressions, and why a pattern that runs can still be wrong  
🏷️ Classifiers that return probabilities, and checking them against your own labels  
🧭 Embeddings and search by meaning, in DuckDB  
💬 Retrieval-augmented generation, with every claim traced to a source  
🧱 Structured extraction with schemas  
🔍 Judging when a model is wrong, and which tool to reach for  
🦉 Become familiar with how climate change enters U.S. endangered species law  

## 📖 Content Overview

[💻 Assignment template](esa.ipynb)  
[💯 Assignment rubric](rubric.md)  

When the U.S. government lists a species under the Endangered Species Act, it publishes its
reasoning in the Federal Register. [Delach et al. (2019)](https://doi.org/10.1038/s41558-019-0620-8)
read the official documents for all 459 endangered animals by hand and found climate change named
as a threat for 64% of them, but management actions planned for only 18%.

In this module we read thirty years of final listing rules with code and ask whether, and how often,
the government says climate change is a reason a species needs protection. We then compare our
answer with Delach et al.'s published per-species data.

The notebook gives the background, the data, and working connections to a language model, an
embedding model, and a decision model. It does not give step-by-step instructions. Deciding what the
question means in practice, guiding your coding agent, and judging when its tools are wrong is the
work of this module.

## What to hand in

- `esa.ipynb`, run from top to bottom.
- `prompts/`: your conversations with your coding agent, exported as files.
- An updated README.

## Data sources

- Federal Register API (no key needed) — <https://www.federalregister.gov/developers/documentation/api/v1>
- Delach et al. 2019 data — <https://doi.org/10.17605/OSF.IO/R9UCA>

## Models

- `deepseek-v4-flash` (language model) and `qwen3-embedding` (embeddings), served by the
  [National Research Platform](https://nrp.ai/documentation/userdocs/ai/llm-managed/)
- [Laya](https://huggingface.co/convaiinnovations/laya), an open-weights decision model,
  hosted for this course at <https://laya.carlboettiger.info>

The notebook reads your `NRP_TOKEN` and `LAYA_API_KEY` from the environment. Never put
these in the notebook or commit them.

## Setup

Environment setup, GitHub authentication, and language model configuration are covered on
the [course website](https://espm-157.carlboettiger.info/).

GitHub Actions runs a lightweight check on every push (the notebook is valid, every code cell
parses, and no credentials are committed). It does not run the notebook or call any model.

## Links

[🌐 Course Website](https://espm-157.carlboettiger.info/)
