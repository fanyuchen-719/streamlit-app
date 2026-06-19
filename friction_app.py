import streamlit as st
import google.generativeai as genai
import re
import PIL.Image

# --- 初始化設定 ---
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 1
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 讀取金鑰 ---
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ 未偵測到 API 金鑰。請檢查 Streamlit Secrets 設定。")
    st.stop()

# --- 模型設定 (移除 code_execution 以防 403) ---
system_prompt = """你是一位精通工程力學的教授。
請針對使用者上傳的題目進行受力分析、列出平衡方程式並求解。
步驟：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷、5.最終結論。"""

try:
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',  # 確保每日額度充足
        system_instruction=system_prompt
    )
except Exception as e:
    st.error(f"模型初始化失敗: {e}")

# --- UI 介面 ---
st.title("🤖 ⚙️ 靜力學：乾摩擦力 AI 助教")

uploaded_file = st.file_uploader(
    "📎 上傳題目照片 (選填)：", 
    type=["jpg", "png", "jpeg"], 
    key=f"uploader_{st.session_state.uploader_key}"
)

user_input = st.text_input("在這裡輸入題目內容...")

# 顯示對話紀錄
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- API 呼叫邏輯 ---
if st.button("開始計算") or user_input:
    if not user_input and not uploaded_file:
        st.warning("請輸入問題或上傳圖片。")
    else:
        # 準備資料
        content_list = []
        if user_input:
            content_list.append(user_input)
        if uploaded_file:
            image = PIL.Image.open(uploaded_file)
            content_list.append(image)
            
        # 顯示使用者輸入
        st.session_state.messages.append({"role": "user", "content": user_input or "（圖片輸入）"})
        with st.chat_message("user"):
            if user_input: st.markdown(user_input)
            if uploaded_file: st.image(image, caption="題目照片")

        # 呼叫 API
        with st.spinner("力學教授計算中..."):
            try:
                response = model.generate_content(content_list)
                response_text = response.text
                
                # 清洗與顯示結果
                clean_text = re.sub(r'```.*?```', '', response_text, flags=re.DOTALL).strip()
                with st.chat_message("assistant"):
                    st.markdown(clean_text)
                st.session_state.messages.append({"role": "assistant", "content": clean_text})
                
                # 重新整理介面
                st.session_state.uploader_key += 1
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 計算失敗：{e}")