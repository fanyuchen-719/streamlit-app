import streamlit as st
import google.generativeai as genai
import re
import PIL.Image

# --- 初始化 ---
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 1
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 讀取金鑰 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ 未偵測到 API 金鑰。請檢查 Streamlit Secrets 設定。")
    st.stop()

# --- 模型設定 ---
try:
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction="你是一位精通工程力學的教授。請針對題目進行受力分析與求解。"
    )
except Exception as e:
    st.error(f"模型初始化失敗: {e}")

# --- UI 介面 ---
st.title("靜力學：乾摩擦力 AI 助教")

# 顯示歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

uploaded_file = st.file_uploader("上傳題目照片:", type=["jpg", "png", "jpeg"], key=f"up_{st.session_state.uploader_key}")
user_input = st.text_input("輸入題目內容...")

if st.button("開始計算") or user_input:
    content_list = [user_input] if user_input else []
    if uploaded_file:
        content_list.append(PIL.Image.open(uploaded_file))
        
    # 紀錄使用者的問題
    st.session_state.messages.append({"role": "user", "content": user_input or "（上傳圖片）"})
        
    with st.spinner("計算中..."):
        try:
            response = model.generate_content(content_list)
            # 清洗結果
            clean_text = re.sub(r'```.*?```', '', response.text, flags=re.DOTALL).strip()
            
            # 存入並顯示回應
            st.session_state.messages.append({"role": "assistant", "content": clean_text})
            
            st.session_state.uploader_key += 1
            st.rerun()
        except Exception as e:
            st.error(f"計算失敗: {e}")