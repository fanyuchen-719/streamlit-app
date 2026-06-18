import streamlit as st
from PIL import Image
from google import genai  # 正確的新版管線

# 讀取金鑰
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("❌ 未在 Streamlit 後台設定 GEMINI_API_KEY")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="乾摩擦力 AI 助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 (Dry Friction) AI 解題助教")
st.markdown("本系統專注於解析靜力學中的**乾摩擦（Coulomb Friction）**問題。")

system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。"
)

tab1, tab2 = st.tabs(["📝 輸入文字題目", "📸 上傳題目照片"])
with tab1:
    question_text = st.text_area("請輸入乾摩擦力題目：", height=150)
with tab2:
    uploaded_file = st.file_uploader("上傳乾摩擦力題目照片：", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上傳的力學題目", width=400)

if st.button("🚀 開始乾摩擦力學分析"):
    content_list = [system_prompt]
    if uploaded_file:
        content_list.append(Image.open(uploaded_file))
    if question_text:
        content_list.append(f"題目內容：{question_text}")
    
    if len(content_list) <= 1:
        st.warning("⚠️ 請輸入題目文字或上傳圖片後再試！")
    else:
        with st.spinner("力學教授正在進行乾摩擦與平衡分析..."):
            try:
                response = client.models.generate_content(
                model='gemini-1.5-flash',  # 改回這個穩定的老將
                contents=content_list
                )
                st.success("✨ 乾摩擦分析完成！")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")