import streamlit as st
from PIL import Image
from google import genai
import time

# 讀取金鑰
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("❌ 未在 Streamlit 後台設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="乾摩擦力 AI 聊天助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 AI 聊天解題助教")

# 1. 初始化聊天記憶庫
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. 側邊欄：處理圖片上傳與清空功能
with st.sidebar:
    st.header("📸 題目照片上傳")
    uploaded_file = st.file_uploader("上傳乾摩擦力題目照片（選填）：", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上傳的力學題目", use_container_width=True)
    
    st.markdown("---")
    if st.button("🗑️ 清空歷史對話紀錄"):
        st.session_state.messages = []
        st.rerun()

# 力學教授的靈魂人設
system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。\n"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。\n"
    "【極重要】如果使用者指出你的計算錯誤、公式列錯、或正負號有誤，請虛心檢查並在後續對話中給出修正後的正確解答。"
)

# 3. 畫出歷史對話訊息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 底部聊天輸入框
if user_input := st.chat_input("在這裡輸入題目，或是直接回覆：『你第三步算錯了，正負號應該是...』"):
    
    # 畫出並存入使用者的話
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 5. 打包要送給 Gemini 的對話包
    content_list = [system_prompt]
    if uploaded_file:
        content_list.append(Image.open(uploaded_file))
        
    # 串接歷史紀錄，讓 AI 有前後文記憶
    history_context = "【以下是歷史對話紀錄與使用者的最新回覆】\n"
    for msg in st.session_state.messages:
        role_label = "使用者 (User)" if msg["role"] == "user" else "力學教授 (AI)"
        history_context += f"{role_label}: {msg['content']}\n\n"
    
    content_list.append(history_context)
    
    # 6. 【核心】帶有視覺倒數提示的 503 自動重試機制
    response_text = ""
    max_retries = 4
    warning_placeholder = st.empty()  # 用來動態顯示/清除黃色警告框
    
    for attempt in range(max_retries):
        with st.spinner(f"力學教授正在分析與計算中... (嘗試第 {attempt + 1} 次)"):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=content_list
                )
                response_text = response.text
                warning_placeholder.empty()  # 成功拿到答案後，立刻拔掉警告框
                break
                
            except Exception as e:
                error_msg = str(e)
                # 抓到 503 塞車錯誤，且還沒超過重試上限
                if "503" in error_msg and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 每次塞車就等久一點 (2秒、4秒、6秒...)
                    warning_placeholder.warning(f"⏳ Google 2.5 伺服器大塞車 (503)，將於 {wait_time} 秒後自動重試排隊...")
                    time.sleep(wait_time)
                else:
                    # 其他硬體或權限錯誤，直接吐出紅字並中斷
                    warning_placeholder.empty()
                    st.error(f"連線失敗：{error_msg}")
                    st.stop()
                    
    # 7. 顯示 AI 修正後的回答並存入記憶
    if response_text:
        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})