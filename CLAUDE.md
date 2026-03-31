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

On HuggingFace Spaces, enable **Persistent Storage** in Space settings to make the `/data` directory available for SQLite database persistence.

## Architecture

The entire application is contained in `app.py` with these key sections:

### Configuration & CSS
- **CUSTOM_CSS**: Full custom CSS theme injected via `st.markdown()` with `unsafe_allow_html=True`
- **EMOJI_CATEGORIES / ENGLISH_CATEGORIES**: 8 categories with 238+ emojis, Chinese internal names with English display labels (include category icons)

### Database Layer (SQLite)
- **get_db()**: Cached database connection with WAL mode, creates tables on first run
- **add_story()**: Inserts story with emojis, timestamp, and session_id
- **get_stories()**: Paginated query with sort (popular/newest/oldest) and search support
- **get_vote_counts() / get_user_votes()**: Vote aggregation by type and per-user tracking
- **toggle_vote()**: Adds or removes a vote (like/love/star) with UNIQUE constraint deduplication
- **delete_story()**: Session-scoped deletion (only creator can delete)

Database path: `/data/stories.db` on HF Spaces, `./stories.db` locally.

Schema:
- `stories` table: id, story, emojis, created_at, session_id
- `votes` table: id, story_id, session_id, vote_type, created_at (UNIQUE on story_id + session_id + vote_type)

### AI Story Generation
- **query_huggingface()**: Calls HuggingFace Inference Providers API via `huggingface_hub.InferenceClient.chat_completion()`
- **generate_story_with_ai()**: Constructs prompt, calls API, cleans up generated story (removes section markers, `<think>` tags, fixes incomplete endings)
- Generation parameters: max_tokens=250, temperature=0.7, top_p=0.9

### UI Helpers
- **render_header()**: Custom header with base64-embedded SVG logo from `public/`
- **render_emoji_tray()**: Visual chip-based display of selected emojis with counter
- **render_story_card()**: Card layout with story text, metadata, 3 reaction types, copy/share, and delete (creator only)
- **relative_time()**: Converts timestamps to human-readable relative time

### Main Application Flow
1. Session ID generated per browser session (UUID) for vote tracking and story ownership
2. Tabbed emoji picker → selected emoji tray → generate button
3. Stories section with sort dropdown + search input
4. Paginated story cards (8 per page) with reaction buttons
5. Copy-to-clipboard and session-scoped delete functionality

Data flow: User selects emojis → Generate button → HF API call → Response cleaned → Saved to SQLite → Displayed as styled card with reactions

## Key Implementation Details

- Maximum 5 emojis per story selection
- SQLite with WAL mode for concurrent access safety
- Session-based vote deduplication (UUID per browser session, UNIQUE constraint in DB)
- Three reaction types: like, love, star (toggleable)
- Pagination: 8 stories per page with Previous/Next navigation
- Search filters stories by content or emojis
- Sort options: Most Popular, Newest First, Oldest First
- Story creators can delete their own stories (session_id match)
- Custom CSS provides professional UI with gradient theme, card layout, hover effects
- Logo embedded as base64 SVG from `public/emoji-story-generator-logo.svg`
- No additional dependencies beyond standard library (`sqlite3`, `uuid`, `datetime`, `base64`)
