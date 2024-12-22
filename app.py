import streamlit as st
import random
import json
import os
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

# 定义表情列表
EMOJI_LIST = ["😀", "😎", "🌞", "🌈", "🐶", "🏠", "🚀", "📚", "🎉", "🍕", "🎸", "🏆"]

# 定义数据文件路径
DATA_FILE = "stories_data.json"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"

def query_huggingface(payload):
    """调用Hugging Face API"""
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 调整payload格式为Zephyr模型的要求
    simplified_payload = {
        "inputs": payload["inputs"],
        "parameters": {
            "max_new_tokens": 250,
            "temperature": 0.7,
            "top_p": 0.9,
            "do_sample": True,
            "return_full_text": False
        }
    }
    
    try:
        st.write("Calling API...")
        response = requests.post(API_URL, headers=headers, json=simplified_payload, timeout=60)
        
        if response.status_code != 200:
            st.error(f"API call failed, status code: {response.status_code}")
            st.write(f"Error message: {response.text}")
            return None
            
        result = response.json()
        st.write("API response:", result)
        return result
            
    except Exception as e:
        st.error(f"API request error: {str(e)}")
        return None

def generate_story_with_ai(emojis):
    """Generate story using AI"""
    emoji_text = ' '.join(emojis)
    prompt = f"""Create a fun and engaging short story using these emojis: {emoji_text}

Instructions:
1. Create a story that naturally incorporates all the given emojis
2. The story should be fun and suitable for all ages
3. Include a clear beginning, middle, and end
4. Keep it concise (around 100-150 words)
5. Make it creative and engaging

Story beginning:
Once upon a sunny day,"""
    
    try:
        with st.spinner('Creating story...'):
            response = query_huggingface({"inputs": prompt})
            
            if response and isinstance(response, list) and len(response) > 0:
                # Get generated text
                story = response[0].get('generated_text', '').strip()
                
                # Clean up story text
                story = story.replace(prompt, '').strip()
                
                # Check if story is empty
                if not story:
                    st.error("Generated story is empty, please try again")
                    return None
                
                # Format final story
                final_story = f"Once upon a sunny day, {story}\n\n(Emojis used: {emoji_text})"
                return final_story
            
            st.error("Failed to generate story, please try again")
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
            st.error(f"加载数据时出错: {str(e)}")
            return []
    return []

def save_stories_to_file(stories):
    """保存故事数据到文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"保存数据时出错: {str(e)}")

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
    
    # Add emoji selector
    selected_emojis = st.multiselect("Choose emojis for your story", EMOJI_LIST)
    
    if selected_emojis:
        st.write("Selected emojis:", " ".join(selected_emojis))
        
        # Add generate story button
        if st.button("Generate Story"):
            story = generate_story_with_ai(selected_emojis)
            if story:  # Only save if story generation was successful
                save_story(story)
                st.write("Generated Story:")
                st.write(story)
                st.success("Story saved!")
            
        # Display saved stories
        if st.session_state.stories:
            st.header("Generated Stories")
            
            # Sort stories by votes
            sorted_stories = sorted(st.session_state.stories, 
                                 key=lambda x: x['votes'], 
                                 reverse=True)
            
            # Use columns for layout
            for idx, story_data in enumerate(sorted_stories):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{idx + 1}. {story_data['story']} (Likes: {story_data['votes']})")
                with col2:
                    if st.button(f"👍", key=f"vote_{idx}"):
                        story_data['votes'] += 1
                        update_votes()
                        st.success(f"Liked!")
                        st.experimental_rerun()
    else:
        st.write("Please select at least one emoji.")

if __name__ == "__main__":
    main()
