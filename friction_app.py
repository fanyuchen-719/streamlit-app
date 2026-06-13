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