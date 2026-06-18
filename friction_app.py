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

# 1. 初始化聊天記憶庫與上傳防刷新機制
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# 側邊欄只留控制按鈕，畫面變超乾淨
with st.sidebar:
    st.header("⚙️ 控制面板")
    if st.button("🗑️ 清空歷史對話紀錄"):
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()

# 力學教授的靈魂人設
system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。\n"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。\n"
    "【極重要】如果使用者指出你的計算錯誤、公式列錯、或正負號有誤，請虛心檢查並在後續對話中給出修正後的正確解答。"
)

# 2. 畫出歷史對話訊息（如果是使用者傳的，照片會直接顯示在對話框裡！）
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], caption="💡 本輪附帶的力學題目照片", width=400)
        st.markdown(msg["content"])

st.markdown("---")

# 3. 【Gemini 核心體驗】把上傳區黏在輸入框上方
# 用動態 key 來控制，只要送出訊息，這個上傳欄位就會被強制重置清空！
uploaded_file = st.file_uploader(
    "📎 點擊或拖曳上傳本輪題目照片（選填，送出後會自動融入對話）：", 
    type=["jpg", "jpeg", "png"],
    key=f"friction_upload_{st.session_state.uploader_key}"
)

# 如果有選取照片，在下方貼心顯示一塊小小的「預覽圖」
if uploaded_file:
    st.image(uploaded_file, caption="👀 準備送出的照片預覽", width=200)

# 4. 底部聊天輸入框
if user_input := st.chat_input("在這裡輸入題目，或是直接回覆：『你第三步算錯了，正負號應該是...』"):
    
    # 讀取當前附加的照片
    current_image = None
    if uploaded_file:
        current_image = Image.open(uploaded_file)
    
    # 畫出並存入使用者的對話（文字 + 照片大合體）
    with st.chat_message("user"):
        if current_image:
            st.image(current_image, caption="上傳的題目照片", width=400)
        st.markdown(user_input)
    
    # 將當前對話存入 session_state 歷史紀錄
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input,
        "image": current_image,
        "has_image": current_image is not None
    })
    
    # 5. 打包要送給 Gemini 的資料
    content_list = [system_prompt]
    if current_image:
        content_list.append(current_image)
        
    # 串接文字歷史紀錄，讓 AI 記住前面的對話脈絡（並提示哪一輪有照片）
    history_context = "【以下是歷史對話紀錄與使用者的最新回覆】\n"
    for msg in st.session_state.messages:
        role_label = "使用者 (User)" if msg["role"] == "user" else "力學教授 (AI)"
        img_note = "（附帶了題目照片）" if msg.get("has_image") else ""
        history_context += f"{role_label}: {img_note}{msg['content']}\n\n"
    
    content_list.append(history_context)
    
    # 6. 自動重試 503 倒數機制（完整保留！）
    response_text = ""
    max_retries = 4
    warning_placeholder = st.empty()
    
    for attempt in range(max_retries):
        with st.spinner(f"力學教授正在分析與計算中... (嘗試第 {attempt + 1} 次)"):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=content_list
                )
                response_text = response.text
                warning_placeholder.empty()
                break
            except Exception as e:
                error_msg = str(e)
                if "503" in error_msg and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    warning_placeholder.warning(f"⏳ Google 2.5 伺服器大塞車 (503)，將於 {wait_time} 秒後自動重試排隊...")
                    time.sleep(wait_time)
                else:
                    warning_placeholder.empty()
                    st.error(f"連線失敗：{error_msg}")
                    st.stop()
                    
    # 7. 顯示 AI 回應並存入記憶
    if response_text:
        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
    # 8. 【魔法時刻】成功拿回答案後，更新 key 讓上傳欄位歸零，並刷新網頁
    st.session_state.uploader_key += 1
    st.rerun()