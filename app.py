import streamlit as st
import random
import json
import os
import re
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# 加载环境变量
load_dotenv()

# 定义分类表情列表
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

# 定义数据文件路径
DATA_FILE = "stories_data.json"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"

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
        with st.spinner('Creating story...'):
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
                
                # 移除所有标记
                for marker in markers_to_remove:
                    story = story.replace(marker, '')
                
                # 清理多余的空行和空格
                story = '\n'.join(line for line in story.split('\n') if line.strip())
                story = ' '.join(story.split())
                
                # 检查并修复不完整的结尾
                incomplete_endings = ('and', 'but', 'or', 'so', 'while', 'as', 'then', 'when', '...')
                while story.endswith(incomplete_endings) or story.rstrip()[-1] not in '.!?':
                    story = story.rsplit(' ', 1)[0].rstrip()
                    if not story:
                        break
                
                # 确保故事有适当的结尾标点
                if story and story[-1] not in '.!?':
                    story += '.'
                
                final_story = f"Once upon a sunny day, {story}\n\n(Emojis used: {emoji_text})"
                return final_story
            
            st.error("Failed to generate story. Please try again.")
            return None
            
    except Exception as e:
        st.error(f"Error generating story: {str(e)}")
        return None

def load_stories():
    """从文件加载故事数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return []
    return []

def save_stories_to_file(stories):
    """保存故事数据到文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

# 初始化或加载故事数据
if 'stories' not in st.session_state:
    st.session_state.stories = load_stories()

def save_story(story):
    """保存新故事并更新文件"""
    st.session_state.stories.append({"story": story, "votes": 0})
    save_stories_to_file(st.session_state.stories)

def update_votes():
    """更新文件中的投票数据"""
    save_stories_to_file(st.session_state.stories)

def main():
    st.set_page_config(page_title="Emoji Story Generator", page_icon="📚")
    st.title("Emoji Story Generator")
    
    # Initialize session state for selected emojis
    if 'selected_emojis' not in st.session_state:
        st.session_state.selected_emojis = []
    
    # Create tab layout
    ENGLISH_CATEGORIES = {
        "Faces & Emotions": EMOJI_CATEGORIES["表情与情绪"],
        "Animals": EMOJI_CATEGORIES["动物"],
        "Plants": EMOJI_CATEGORIES["植物"],
        "Food": EMOJI_CATEGORIES["食物"],
        "Activities & Sports": EMOJI_CATEGORIES["活动与运动"],
        "Transportation": EMOJI_CATEGORIES["交通工具"],
        "Places & Buildings": EMOJI_CATEGORIES["地点与建筑"],
        "Objects & Symbols": EMOJI_CATEGORIES["物品与符号"]
    }
    
    tabs = st.tabs(list(ENGLISH_CATEGORIES.keys()))
    
    # Display emojis in each tab
    for tab, (category, emojis) in zip(tabs, ENGLISH_CATEGORIES.items()):
        with tab:
            st.write(f"Select {category}:")
            cols = st.columns(8)
            for i, emoji in enumerate(emojis):
                if cols[i % 8].button(emoji, key=f"{category}_{emoji}"):
                    if emoji not in st.session_state.selected_emojis:
                        if len(st.session_state.selected_emojis) < 5:
                            st.session_state.selected_emojis.append(emoji)
                        else:
                            st.warning("Maximum 5 emojis allowed!")
    
    # Display selected emojis
    if st.session_state.selected_emojis:
        st.write("---")
        st.write("Selected emojis:", " ".join(st.session_state.selected_emojis))
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Clear Selection"):
                st.session_state.selected_emojis = []
                st.rerun()
        
        with col2:
            if st.button("Generate Story"):
                story = generate_story_with_ai(st.session_state.selected_emojis)
                if story:
                    save_story(story)
                    st.write("Generated Story:")
                    st.write(story)
                    st.success("Story saved!")
    else:
        st.write("Please select at least one emoji.")
    
    # Display saved stories
    if st.session_state.stories:
        st.markdown("---")
        st.header("Generated Stories")
        
        sorted_stories = sorted(st.session_state.stories, 
                              key=lambda x: x['votes'], 
                              reverse=True)
        
        for idx, story_data in enumerate(sorted_stories):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{idx + 1}. {story_data['story']} (Likes: {story_data['votes']})")
            with col2:
                if st.button(f"👍", key=f"vote_{idx}"):
                    story_data['votes'] += 1
                    update_votes()
                    st.success("Liked!")
                    st.rerun()

if __name__ == "__main__":
    main()
