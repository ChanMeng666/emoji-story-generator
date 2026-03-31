import streamlit as st
import sqlite3
import uuid
import json
import os
import re
import base64
from datetime import datetime, timezone
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# 加载环境变量
load_dotenv()

# ============================================================
# Configuration
# ============================================================
# SQLite lives locally (FUSE mounts like /data don't support SQLite locking).
# Persistent backup is kept as JSON in /data for survival across restarts.
BACKUP_DIR = "/data" if os.path.exists("/data") else None
BACKUP_PATH = os.path.join(BACKUP_DIR, "stories_backup.json") if BACKUP_DIR else None
DB_PATH = "stories.db"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
STORIES_PER_PAGE = 8

# ============================================================
# Custom CSS
# ============================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Global */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit header/footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Custom header */
.app-header {
    text-align: center;
    padding: 1.5rem 0 1rem 0;
}
.app-header img {
    height: 80px;
    margin-bottom: 0.5rem;
}
.app-header h1 {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #F8BC1C, #667eea, #f093fb);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
}
.app-header p {
    color: #888;
    font-size: 1rem;
    margin-top: 0.3rem;
}

/* Emoji picker tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Emoji buttons */
div[data-testid="stHorizontalBlock"] > div > div[data-testid="stButton"] > button {
    font-size: 1.6rem;
    padding: 6px 4px;
    border-radius: 10px;
    border: 2px solid transparent;
    background: transparent;
    transition: all 0.2s ease;
    min-height: 48px;
    width: 100%;
}
div[data-testid="stHorizontalBlock"] > div > div[data-testid="stButton"] > button:hover {
    background: rgba(102, 126, 234, 0.12);
    border-color: rgba(102, 126, 234, 0.4);
    transform: scale(1.15);
}

/* Selected emoji tray */
.emoji-tray {
    background: linear-gradient(135deg, rgba(248,188,28,0.1), rgba(102,126,234,0.1));
    border: 1px solid rgba(248,188,28,0.3);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin: 1rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}
.emoji-tray .emoji-chip {
    font-size: 2rem;
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 4px 10px;
    display: inline-block;
    transition: transform 0.2s;
}
.emoji-tray .emoji-chip:hover {
    transform: scale(1.2);
}
.emoji-tray .counter {
    font-size: 0.85rem;
    color: #888;
    font-weight: 600;
    margin-left: auto;
    background: rgba(102,126,234,0.15);
    padding: 4px 12px;
    border-radius: 20px;
}

/* Generate button */
.generate-btn > div > button {
    background: linear-gradient(135deg, #F8BC1C, #f09819) !important;
    color: #000 !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(248,188,28,0.3) !important;
}
.generate-btn > div > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(248,188,28,0.5) !important;
}

/* Clear button */
.clear-btn > div > button {
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
    color: #888 !important;
    font-weight: 500 !important;
}

/* Story card */
.story-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
    position: relative;
}
.story-card:hover {
    border-color: rgba(248,188,28,0.3);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.story-card .story-rank {
    position: absolute;
    top: -8px;
    left: 16px;
    background: linear-gradient(135deg, #F8BC1C, #f09819);
    color: #000;
    font-weight: 700;
    font-size: 0.75rem;
    padding: 2px 10px;
    border-radius: 10px;
}
.story-card .story-text {
    font-size: 0.95rem;
    line-height: 1.7;
    margin: 0.5rem 0;
}
.story-card .story-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 0.8rem;
    flex-wrap: wrap;
}
.story-card .story-meta .meta-item {
    font-size: 0.78rem;
    color: #888;
    display: flex;
    align-items: center;
    gap: 4px;
}
.story-card .story-emojis {
    font-size: 1.1rem;
    letter-spacing: 2px;
}

/* Reaction buttons */
.reaction-row {
    display: flex;
    gap: 8px;
    margin-top: 0.6rem;
}
.reaction-btn > div > button {
    border-radius: 20px !important;
    padding: 4px 12px !important;
    font-size: 0.85rem !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    background: rgba(255,255,255,0.03) !important;
    transition: all 0.2s ease !important;
}
.reaction-btn > div > button:hover {
    background: rgba(102,126,234,0.15) !important;
    border-color: rgba(102,126,234,0.4) !important;
}
.reaction-btn-active > div > button {
    border-color: rgba(248,188,28,0.5) !important;
    background: rgba(248,188,28,0.1) !important;
}

/* Section headers */
.section-header {
    font-size: 1.3rem;
    font-weight: 700;
    margin: 1.5rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Sort/filter bar */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 1rem;
}

/* Search input */
div[data-testid="stTextInput"] input {
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
    padding: 8px 16px;
}

/* Pagination */
.pagination {
    text-align: center;
    margin-top: 1rem;
    color: #888;
    font-size: 0.85rem;
}

/* Delete button */
.delete-btn > div > button {
    background: transparent !important;
    border: 1px solid rgba(255,80,80,0.3) !important;
    border-radius: 8px !important;
    color: #ff5050 !important;
    font-size: 0.8rem !important;
    padding: 2px 10px !important;
}
.delete-btn > div > button:hover {
    background: rgba(255,80,80,0.1) !important;
}

/* Share button */
.share-btn > div > button {
    background: transparent !important;
    border: 1px solid rgba(102,126,234,0.3) !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    padding: 2px 10px !important;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #888;
}
.empty-state .emoji-large {
    font-size: 3rem;
    margin-bottom: 0.5rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .app-header h1 { font-size: 1.6rem; }
    .story-card { padding: 1rem; }
    .emoji-tray .emoji-chip { font-size: 1.5rem; }
}

/* Light theme adjustments */
@media (prefers-color-scheme: light) {
    .story-card {
        background: rgba(0,0,0,0.02);
        border-color: rgba(0,0,0,0.08);
    }
    .story-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
}
</style>
"""

# ============================================================
# Emoji Categories
# ============================================================
EMOJI_CATEGORIES = {
    "表情与情绪": [
        "😀", "😃", "😄", "😁", "😅", "😂", "🤣", "😊", "😇", "🙂", "😉", "😌",
        "😍", "🥰", "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜", "🤪", "🤨",
        "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁"
    ],
    "动物": [
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮",
        "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗"
    ],
    "植物": [
        "🌸", "💮", "🌹", "🌺", "🌻", "🌼", "🌷", "🌱", "🌲", "🌳", "🌴", "🌵",
        "🌾", "🌿", "☘️", "🍀", "🍁", "🍂", "🍃", "🪴", "🎋", "🎍"
    ],
    "食物": [
        "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑",
        "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑", "🥦", "🥬", "🥒", "🌶️", "🫑",
        "🥕", "🧄", "🧅", "🥔", "🍠", "🥐", "🥯", "🍞", "🥖", "🥨", "🧀", "🥚",
        "🍳", "🥓", "🥩", "🍗", "🍖", "🦴", "🌭", "🍔", "🍟", "🍕", "🫓", "🥪"
    ],
    "活动与运动": [
        "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱", "🪀", "🏓",
        "🏸", "🏒", "🏑", "🥍", "🏏", "🪃", "🥅", "⛳", "🪁", "🏹", "🎣", "🤿"
    ],
    "交通工具": [
        "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🛻", "🚚",
        "🚛", "🚜", "🛵", "🏍️", "🚲", "🛴", "🚔", "🚍", "🚘", "🚖", "✈️", "🚀"
    ],
    "地点与建筑": [
        "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦", "🏨", "🏩", "🏪", "🏫", "🏬",
        "🏭", "🏯", "🏰", "💒", "🗼", "🗽", "⛪", "🕌", "🕍", "⛩️", "🕋", "⛲"
    ],
    "物品与符号": [
        "📱", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "📷", "📸", "📹", "🎥", "📽️",
        "📺", "📻", "🎙️", "🎚️", "🎛️", "🧭", "⏱️", "⏲️", "⏰", "🕰️", "📡", "🔋",
        "📚", "📖", "🏆", "🎮", "🎲", "🎭", "🎨", "🎪", "🎟️", "🎫", "🎗️", "🏷️"
    ]
}

ENGLISH_CATEGORIES = {
    "😊 Faces & Emotions": "表情与情绪",
    "🐾 Animals": "动物",
    "🌿 Plants": "植物",
    "🍔 Food": "食物",
    "⚽ Activities & Sports": "活动与运动",
    "🚗 Transportation": "交通工具",
    "🏠 Places & Buildings": "地点与建筑",
    "📱 Objects & Symbols": "物品与符号"
}

# ============================================================
# Database Layer
# ============================================================

@st.cache_resource
def get_db():
    """Initialize and return a persistent database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story TEXT NOT NULL,
            emojis TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id INTEGER REFERENCES stories(id) ON DELETE CASCADE,
            session_id TEXT NOT NULL,
            vote_type TEXT NOT NULL DEFAULT 'like',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(story_id, session_id, vote_type)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_story ON votes(story_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stories_created ON stories(created_at)")
    conn.commit()

    # Restore data from persistent backup (survives container restarts)
    _restore_from_backup(conn)

    return conn


def _backup_to_json():
    """Save all stories and votes to a JSON file in /data for persistence."""
    if not BACKUP_PATH:
        return
    try:
        conn = get_db()
        stories = conn.execute(
            "SELECT id, story, emojis, created_at, session_id FROM stories"
        ).fetchall()
        votes = conn.execute(
            "SELECT story_id, session_id, vote_type FROM votes"
        ).fetchall()
        data = {
            "stories": [
                {"id": r[0], "story": r[1], "emojis": r[2], "created_at": r[3], "session_id": r[4]}
                for r in stories
            ],
            "votes": [
                {"story_id": r[0], "session_id": r[1], "vote_type": r[2]}
                for r in votes
            ]
        }
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _restore_from_backup(conn):
    """Restore stories and votes from the persistent JSON backup."""
    # First try persistent backup
    source = BACKUP_PATH
    # Fallback to legacy stories_data.json
    if not source or not os.path.exists(source):
        legacy = os.path.join(os.path.dirname(__file__), "stories_data.json")
        if os.path.exists(legacy):
            source = legacy
        else:
            return

    count = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    if count > 0:
        return

    try:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle new backup format
        if isinstance(data, dict) and "stories" in data:
            for item in data["stories"]:
                conn.execute(
                    "INSERT INTO stories (id, story, emojis, created_at, session_id) VALUES (?, ?, ?, ?, ?)",
                    (item["id"], item["story"], item["emojis"], item.get("created_at"), item.get("session_id"))
                )
            for vote in data.get("votes", []):
                conn.execute(
                    "INSERT OR IGNORE INTO votes (story_id, session_id, vote_type) VALUES (?, ?, ?)",
                    (vote["story_id"], vote["session_id"], vote["vote_type"])
                )
        # Handle legacy format (list of {story, votes})
        elif isinstance(data, list):
            for item in data:
                story_text = item.get("story", "")
                votes = item.get("votes", 0)
                emojis = ""
                match = re.search(r'\(Emojis used:\s*(.+?)\)', story_text)
                if match:
                    emojis = match.group(1).strip()
                cursor = conn.execute(
                    "INSERT INTO stories (story, emojis, session_id) VALUES (?, ?, ?)",
                    (story_text, emojis, "migrated")
                )
                story_id = cursor.lastrowid
                for i in range(votes):
                    conn.execute(
                        "INSERT OR IGNORE INTO votes (story_id, session_id, vote_type) VALUES (?, ?, ?)",
                        (story_id, f"legacy_vote_{i}", "like")
                    )
        conn.commit()
    except Exception:
        pass


def add_story(story_text, emojis, session_id):
    """Insert a new story and return its ID."""
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO stories (story, emojis, session_id) VALUES (?, ?, ?)",
        (story_text, emojis, session_id)
    )
    conn.commit()
    _backup_to_json()
    return cursor.lastrowid


def get_stories(sort_by="popular", search_query="", page=1):
    """Fetch stories with vote counts, sorted and paginated."""
    conn = get_db()
    offset = (page - 1) * STORIES_PER_PAGE

    order_clause = {
        "popular": "vote_count DESC, s.created_at DESC",
        "newest": "s.created_at DESC",
        "oldest": "s.created_at ASC"
    }.get(sort_by, "vote_count DESC, s.created_at DESC")

    where_clause = ""
    params = []
    if search_query:
        where_clause = "WHERE s.story LIKE ? OR s.emojis LIKE ?"
        params = [f"%{search_query}%", f"%{search_query}%"]

    query = f"""
        SELECT s.id, s.story, s.emojis, s.created_at, s.session_id,
               COALESCE(v.vote_count, 0) as vote_count
        FROM stories s
        LEFT JOIN (
            SELECT story_id, COUNT(*) as vote_count
            FROM votes
            GROUP BY story_id
        ) v ON s.id = v.story_id
        {where_clause}
        ORDER BY {order_clause}
        LIMIT ? OFFSET ?
    """
    params.extend([STORIES_PER_PAGE, offset])
    rows = conn.execute(query, params).fetchall()

    # Get total count
    count_query = f"SELECT COUNT(*) FROM stories s {where_clause}"
    count_params = params[:-2] if search_query else []
    total = conn.execute(count_query, count_params).fetchone()[0]

    return rows, total


def get_vote_counts(story_id):
    """Get vote counts by type for a story."""
    conn = get_db()
    rows = conn.execute(
        "SELECT vote_type, COUNT(*) FROM votes WHERE story_id = ? GROUP BY vote_type",
        (story_id,)
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def get_user_votes(story_id, session_id):
    """Get vote types the current user has cast on a story."""
    conn = get_db()
    rows = conn.execute(
        "SELECT vote_type FROM votes WHERE story_id = ? AND session_id = ?",
        (story_id, session_id)
    ).fetchall()
    return {row[0] for row in rows}


def toggle_vote(story_id, session_id, vote_type="like"):
    """Toggle a vote. Returns True if added, False if removed."""
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM votes WHERE story_id = ? AND session_id = ? AND vote_type = ?",
        (story_id, session_id, vote_type)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM votes WHERE id = ?", (existing[0],))
        conn.commit()
        _backup_to_json()
        return False
    else:
        conn.execute(
            "INSERT INTO votes (story_id, session_id, vote_type) VALUES (?, ?, ?)",
            (story_id, session_id, vote_type)
        )
        conn.commit()
        _backup_to_json()
        return True


def delete_story(story_id, session_id):
    """Delete a story only if the session_id matches the creator."""
    conn = get_db()
    conn.execute(
        "DELETE FROM stories WHERE id = ? AND session_id = ?",
        (story_id, session_id)
    )
    conn.commit()
    _backup_to_json()


# ============================================================
# AI Story Generation
# ============================================================

def query_huggingface(prompt_text):
    """调用Hugging Face Inference Providers API"""
    try:
        client = InferenceClient(token=HUGGINGFACE_API_TOKEN)
        response = client.chat_completion(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=250,
            temperature=0.7,
            top_p=0.9,
        )
        return response
    except Exception as e:
        st.error(f"API request error: {str(e)}")
        return None


def generate_story_with_ai(emojis):
    """Generate story using AI"""
    emoji_text = ' '.join(emojis)
    prompt = f"""Create a short story (100-150 words) using these emojis: {emoji_text}

Instructions:
1. Write a coherent story that naturally incorporates the given emojis
2. The story must be suitable for all ages and have a clear structure:
   - Beginning: Introduce the main character and setting
   - Middle: Present a small challenge or interesting situation
   - End: Resolve the situation with a satisfying conclusion
3. Important rules:
   - Write as one continuous narrative without any section markers
   - Do not use labels like 'Story event:' or 'Story resolution:'
   - Ensure the story has a proper ending (no cliffhangers)
   - Keep sentences complete (no trailing thoughts)
   - Maintain a consistent tone throughout
4. Example flow (do not copy this exactly):
   "Character encounters situation → faces challenge → resolves it → learns or achieves something"

Begin the story with:
Once upon a sunny day,"""

    try:
        with st.spinner('✨ Crafting your story...'):
            response = query_huggingface(prompt)

            if response and response.choices and len(response.choices) > 0:
                story = response.choices[0].message.content.strip()

                # Remove <think>...</think> reasoning blocks if present
                story = re.sub(r'<think>.*?</think>', '', story, flags=re.DOTALL).strip()

                if not story:
                    st.error("Failed to generate story. Please try again.")
                    return None

                # 清理所有可能的章节标记和故事标签
                markers_to_remove = [
                    'Story event:', 'Story resolution:', 'Story middle:',
                    'Story end:', 'Story summary:', 'Story continuation:',
                    'Story ending:', 'Story begins:', 'Story continues:',
                    'Story concludes:', 'Beginning:', 'Middle:', 'End:',
                    'Continuation:', 'Ending:', 'Event:', 'Resolution:',
                    'Finally:', 'In conclusion:', 'The end:', 'Summary:',
                    'Next:', 'Then:', 'After that:', 'Eventually:'
                ]

                for marker in markers_to_remove:
                    story = story.replace(marker, '')

                # 清理多余的空行和空格
                story = '\n'.join(line for line in story.split('\n') if line.strip())
                story = ' '.join(story.split())

                # 检查并修复不完整的结尾
                incomplete_endings = ('and', 'but', 'or', 'so', 'while', 'as', 'then', 'when', '...')
                while story and (story.endswith(incomplete_endings) or story.rstrip()[-1] not in '.!?'):
                    story = story.rsplit(' ', 1)[0].rstrip()
                    if not story:
                        break

                # 确保故事有适当的结尾标点
                if story and story[-1] not in '.!?':
                    story += '.'

                final_story = f"Once upon a sunny day, {story}"
                return final_story

            st.error("Failed to generate story. Please try again.")
            return None

    except Exception as e:
        st.error(f"Error generating story: {str(e)}")
        return None


# ============================================================
# UI Helpers
# ============================================================

def get_logo_b64():
    """Load and base64-encode the SVG logo."""
    logo_path = os.path.join(os.path.dirname(__file__), "public", "emoji-story-generator-logo.svg")
    if os.path.exists(logo_path):
        with open(logo_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        return base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    return None


def relative_time(dt_str):
    """Convert a datetime string to relative time display."""
    try:
        created = datetime.fromisoformat(dt_str)
        now = datetime.now()
        diff = now - created
        seconds = int(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = seconds // 60
            return f"{mins}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        elif seconds < 604800:
            days = seconds // 86400
            return f"{days}d ago"
        else:
            return created.strftime("%b %d, %Y")
    except Exception:
        return ""


def render_header():
    """Render the custom app header with logo."""
    logo_b64 = get_logo_b64()
    logo_html = ""
    if logo_b64:
        logo_html = f'<img src="data:image/svg+xml;base64,{logo_b64}" alt="Logo">'

    st.markdown(f"""
        <div class="app-header">
            {logo_html}
            <h1>Emoji Story Generator</h1>
            <p>Select emojis, and AI will craft a unique story just for you</p>
        </div>
    """, unsafe_allow_html=True)


def render_emoji_tray(selected_emojis):
    """Render the selected emoji display tray."""
    if not selected_emojis:
        return

    chips = "".join(f'<span class="emoji-chip">{e}</span>' for e in selected_emojis)
    counter = f'<span class="counter">{len(selected_emojis)} / 5</span>'

    st.markdown(f"""
        <div class="emoji-tray">
            {chips}
            {counter}
        </div>
    """, unsafe_allow_html=True)


def render_story_card(story_row, rank, session_id):
    """Render a single story card with reactions."""
    story_id, story_text, emojis, created_at, creator_session, vote_count = story_row

    # Get detailed vote counts and user's votes
    vote_counts = get_vote_counts(story_id)
    user_votes = get_user_votes(story_id, session_id)

    like_count = vote_counts.get("like", 0)
    love_count = vote_counts.get("love", 0)
    star_count = vote_counts.get("star", 0)

    time_str = relative_time(created_at) if created_at else ""
    is_creator = (creator_session == session_id)

    # Card HTML
    st.markdown(f"""
        <div class="story-card">
            <span class="story-rank">#{rank}</span>
            <div class="story-emojis">{emojis}</div>
            <div class="story-text">{story_text}</div>
            <div class="story-meta">
                <span class="meta-item">🕐 {time_str}</span>
                <span class="meta-item">💬 {vote_count} reactions</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Reaction buttons row
    reaction_cols = st.columns([1, 1, 1, 1, 2])

    with reaction_cols[0]:
        like_label = f"👍 {like_count}" if like_count else "👍"
        css_class = "reaction-btn-active" if "like" in user_votes else "reaction-btn"
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(like_label, key=f"like_{story_id}"):
            toggle_vote(story_id, session_id, "like")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with reaction_cols[1]:
        love_label = f"❤️ {love_count}" if love_count else "❤️"
        css_class = "reaction-btn-active" if "love" in user_votes else "reaction-btn"
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(love_label, key=f"love_{story_id}"):
            toggle_vote(story_id, session_id, "love")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with reaction_cols[2]:
        star_label = f"⭐ {star_count}" if star_count else "⭐"
        css_class = "reaction-btn-active" if "star" in user_votes else "reaction-btn"
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(star_label, key=f"star_{story_id}"):
            toggle_vote(story_id, session_id, "star")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with reaction_cols[3]:
        st.markdown('<div class="share-btn">', unsafe_allow_html=True)
        if st.button("📋 Copy", key=f"share_{story_id}"):
            st.session_state[f"copied_{story_id}"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Show copy text if requested
    if st.session_state.get(f"copied_{story_id}"):
        st.code(f"{story_text}\n\n(Emojis: {emojis})", language=None)
        del st.session_state[f"copied_{story_id}"]

    with reaction_cols[4]:
        if is_creator:
            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
            if st.button("🗑️ Delete", key=f"del_{story_id}"):
                delete_story(story_id, session_id)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# Main Application
# ============================================================

def main():
    st.set_page_config(
        page_title="Emoji Story Generator",
        page_icon="📚",
        layout="centered"
    )

    # Inject custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # Initialize database
    get_db()

    # Session ID for vote tracking and ownership
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if 'selected_emojis' not in st.session_state:
        st.session_state.selected_emojis = []

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    session_id = st.session_state.session_id

    # Header
    render_header()

    # ── Emoji Selection ──────────────────────────────────
    tabs = st.tabs(list(ENGLISH_CATEGORIES.keys()))

    for tab, (eng_name, cn_name) in zip(tabs, ENGLISH_CATEGORIES.items()):
        with tab:
            emojis = EMOJI_CATEGORIES[cn_name]
            cols = st.columns(8)
            for i, emoji in enumerate(emojis):
                if cols[i % 8].button(emoji, key=f"{eng_name}_{emoji}"):
                    if emoji not in st.session_state.selected_emojis:
                        if len(st.session_state.selected_emojis) < 5:
                            st.session_state.selected_emojis.append(emoji)
                            st.rerun()
                        else:
                            st.warning("Maximum 5 emojis allowed!")

    # ── Selected Emoji Tray ──────────────────────────────
    render_emoji_tray(st.session_state.selected_emojis)

    if st.session_state.selected_emojis:
        col1, col2, col3 = st.columns([1, 1, 3])

        # Remove last emoji
        with col1:
            st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
            if st.button("↩ Undo", key="undo_btn"):
                st.session_state.selected_emojis.pop()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
            if st.button("✕ Clear All", key="clear_btn"):
                st.session_state.selected_emojis = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="generate-btn">', unsafe_allow_html=True)
            if st.button("✨ Generate Story", key="generate_btn"):
                emoji_text = ' '.join(st.session_state.selected_emojis)
                story = generate_story_with_ai(st.session_state.selected_emojis)
                if story:
                    add_story(story, emoji_text, session_id)
                    st.success("Story created!")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="empty-state">
                <div class="emoji-large">👆</div>
                <p>Select up to 5 emojis from the categories above to generate a story</p>
            </div>
        """, unsafe_allow_html=True)

    # ── Stories Section ──────────────────────────────────
    st.markdown('<div class="section-header">📖 Stories</div>', unsafe_allow_html=True)

    # Sort and search controls
    ctrl_col1, ctrl_col2 = st.columns([1, 2])
    with ctrl_col1:
        sort_option = st.selectbox(
            "Sort by",
            ["Most Popular", "Newest First", "Oldest First"],
            label_visibility="collapsed"
        )
    with ctrl_col2:
        search_query = st.text_input(
            "Search stories...",
            placeholder="🔍 Search stories or emojis...",
            label_visibility="collapsed"
        )

    sort_map = {
        "Most Popular": "popular",
        "Newest First": "newest",
        "Oldest First": "oldest"
    }
    sort_key = sort_map.get(sort_option, "popular")

    # Reset page on search/sort change
    state_key = f"{sort_key}_{search_query}"
    if st.session_state.get("_filter_state") != state_key:
        st.session_state.current_page = 1
        st.session_state["_filter_state"] = state_key

    # Fetch stories
    stories, total = get_stories(
        sort_by=sort_key,
        search_query=search_query,
        page=st.session_state.current_page
    )

    if stories:
        total_pages = max(1, (total + STORIES_PER_PAGE - 1) // STORIES_PER_PAGE)
        base_rank = (st.session_state.current_page - 1) * STORIES_PER_PAGE

        for idx, story_row in enumerate(stories):
            render_story_card(story_row, base_rank + idx + 1, session_id)

        # Pagination
        if total_pages > 1:
            st.markdown(f'<div class="pagination">Page {st.session_state.current_page} of {total_pages} · {total} stories total</div>', unsafe_allow_html=True)
            pg_col1, pg_col2, pg_col3 = st.columns([1, 1, 3])
            with pg_col1:
                if st.session_state.current_page > 1:
                    if st.button("← Previous", key="prev_page"):
                        st.session_state.current_page -= 1
                        st.rerun()
            with pg_col2:
                if st.session_state.current_page < total_pages:
                    if st.button("Next →", key="next_page"):
                        st.session_state.current_page += 1
                        st.rerun()
    else:
        st.markdown("""
            <div class="empty-state">
                <div class="emoji-large">📝</div>
                <p>No stories yet. Select some emojis and generate the first one!</p>
            </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
