import streamlit as st
from PIL import Image
import google.generativeai as genai

# --- 1. 設定 API Key (改從 Streamlit 雲端 Secrets 安全讀取) ---
try:
    # 這裡會讀取我們等一下在 Streamlit 後台設定的密碼
    API_KEY = st.secrets["gcp_api_key"]
except KeyError:
    st.error("❌ 未偵測到 GCP API Key。請確保已在 Streamlit 後台設定 Secrets：`gcp_api_key = '你的金鑰'`")
    st.stop()

# 初始化 Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. 網頁介面設計 ---
st.set_page_config(page_title="靜力學 AI 助教", layout="wide")
st.title("🤖 ⚙️ 靜力學摩擦力 AI 解題助教")
st.markdown("請輸入題目文字或上傳題目照片，AI 將協助您進行專業的受力分析。")

# 設定 prompt，確保 AI 的專業回答格式符合力學要求
system_prompt = (
    "你是一位資重的工程力學教授。請針對使用者提供的靜力學題目，"
    "按照以下步驟進行嚴謹的分析：\n"
    "1. 已知條件：列出所有物理參數。\n"
    "2. 受力分析：描述自由體圖 (FBD) 中的力（重力、正向力、摩擦力等）。\n"
    "3. 平衡方程式：列出 $\\Sigma F_x=0$ 與 $\\Sigma F_y=0$ 的方程式。\n"
    "4. 詳細計算過程。\n"
    "5. 最終答案與結論。"
)

# 介面分頁：可以輸入文字或直接丟圖片
tab1, tab2 = st.tabs(["📝 文字題目", "📸 圖片題目"])

with tab1:
    question_text = st.text_area("請輸入力學題目：", height=150)

with tab2:
    uploaded_file = st.file_uploader("上傳題目照片：", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上傳題目", width=400)

# --- 3. 解題邏輯 ---
if st.button("🚀 開始分析解題"):
    content = [system_prompt]
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        content.append(img)
        
    if question_text:
        content.append(f"題目內容：{question_text}")
    
    if len(content) <= 1:
        st.warning("⚠️ 請輸入題目文字或上傳圖片後再試！")
    else:
        with st.spinner("教授正在分析題目中..."):
            try:
                response = model.generate_content(content)
                st.success("✨ 解題完成！")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")
st.divider() # 加一條分隔線讓畫面更漂亮
st.subheader("💬 覺得哪裡怪怪的？直接糾正或提問！")

# 1. 初始化對話紀錄 (讓網頁能記住你們聊過什麼)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. 將過去的對話顯示在畫面上
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 3. 建立底部的文字輸入框
if user_input := st.chat_input("跟 AI 說：『你第 4 步算錯了，法向力應該是...』 或 『為什麼 fA 向上？』"):
    
    # 顯示使用者的訊息並存入紀錄
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 讓 AI 思考並回應
    with st.chat_message("assistant"):
        # 我們把使用者的問題，包裝成一個帶有上下文的提示詞給 AI
        context_prompt = f"針對你剛剛解的那題靜力學題目，使用者提出疑問或糾正：『{user_input}』。請重新檢查你的計算，如果使用者說得對，請承認錯誤並給出正確算式；如果是使用者誤解，請溫柔地解釋給他聽。"
        
        # 呼叫模型產生回應
        response = model.generate_content(context_prompt)
        st.markdown(response.text)
        
    # 將 AI 的回應也存入紀錄
    st.session_state.messages.append({"role": "assistant", "content": response.text})