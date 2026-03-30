# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Emoji Story Generator is a Streamlit-based web application that uses HuggingFace's Inference Providers API with the meta-llama/Llama-3.1-8B-Instruct model to generate short stories from user-selected emojis. Users select up to 5 emojis from 8 categories (200+ emojis total), and the AI generates a 100-150 word family-friendly story incorporating those emojis.

## Development Commands

```bash
# Run the application
streamlit run app.py

# Run with auto-reload on file changes
streamlit run app.py --server.runOnSave true

# Run on custom port
streamlit run app.py --server.port 8502

# Syntax check
python -m py_compile app.py
```

## Environment Setup

Requires a `.env` file with:
```
HUGGINGFACE_API_TOKEN=your_token_here
```

## Architecture

The entire application is contained in `app.py` with these key components:

- **EMOJI_CATEGORIES**: Dictionary mapping category names (Chinese) to emoji lists
- **ENGLISH_CATEGORIES**: English translations of category names for UI display
- **query_huggingface()**: Calls HuggingFace Inference Providers API via `huggingface_hub.InferenceClient.chat_completion()`
- **generate_story_with_ai()**: Constructs prompt, calls API, cleans up generated story (removes section markers, fixes incomplete endings)
- **load_stories()/save_stories_to_file()**: JSON file persistence for stories
- **main()**: Streamlit UI with tabbed emoji categories, selection management, and story display

Data flow: User selects emojis -> Generate button triggers API call -> Response is cleaned and formatted -> Story saved to `stories_data.json` -> Displayed in UI with voting capability

## Key Implementation Details

- Maximum 5 emojis per story selection
- Stories persisted to `stories_data.json` with vote counts
- Streamlit session state manages `selected_emojis` and `stories`
- Story generation includes cleanup logic to remove AI section markers and fix incomplete sentences
- Generation parameters: max_tokens=250, temperature=0.7, top_p=0.9
- Includes `<think>` tag stripping for models with reasoning output
