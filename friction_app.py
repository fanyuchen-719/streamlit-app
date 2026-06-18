import streamlit as st
from PIL import Image
import google.generativeai as genai

# --- 1. 從 Streamlit Secrets 安全讀取 API Key ---
# 這樣程式碼裡就完全沒有外流風險了！
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("❌ 未在 Streamlit 後台設定 GEMINI_API_KEY")
    st.stop()

# 初始化 Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. 網頁介面設計 ---
st.set_page_config(page_title="乾摩擦力 AI 助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 (Dry Friction) AI 解題助教")
st.markdown("本系統專注於解析靜力學中的**乾摩擦（Coulomb Friction）**問題。支援臨界滑動、滑動與翻倒判斷、斜面及梯子等經典題型。")

# 專業的乾摩擦力 System Prompt
system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。"
    "請針對使用者提供的題目或圖片，嚴格依照以下步驟進行專業拆解：\n\n"
    "1. 物理參數列舉：找出物體重量 (W)、外力 (P)、靜摩擦係數 (μs) 或動摩擦係數 (μk) 等已知量。\n"
    "2. 乾摩擦狀態假設與分析：\n"
    "   - 繪製自由體圖 (FBD) 概念：說明正向力 (N) 的作用點位置、摩擦力 (f) 如何抵抗相對運動趨勢。\n"
    "   - 臨界狀態檢查：計算最大靜摩擦力 f_max = μs * N。\n"
    "3. 平衡方程式建立：列出 ΣFx = 0, ΣFy = 0 以及某點的力矩平衡 ΣM = 0。\n"
    "4. 狀態判斷與計算：詳細計算並判斷物體目前是『處於靜止平衡』、『即將發生滑動 (Impending Motion)』、『已開始滑動』或『先發生翻倒 (Tipping)』。\n"
    "5. 最終結論：明確給出所求的未知力、摩擦力大小或臨界角度。"
)

# 介面分頁
tab1, tab2 = st.tabs(["📝 輸入文字題目", "📸 上傳題目照片"])

with tab1:
    question_text = st.text_area("請輸入乾摩擦力題目：", height=150, placeholder="例如：一個重100N的物體置於傾角30度的斜面上，靜摩擦係數為0.3...")

with tab2:
    uploaded_file = st.file_uploader("上傳乾摩擦力題目照片：", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="已上傳的力學題目", width=400)

# --- 3. 解題邏輯 ---
if st.button("🚀 開始乾摩擦力學分析"):
    content = [system_prompt]
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        content.append(img)
        
    if question_text:
        content.append(f"題目內容：{question_text}")
    
    if len(content) <= 1:
        st.warning("⚠️ 請輸入題目文字或上傳圖片後再試！")
    else:
        with st.spinner("力學教授正在進行乾摩擦與平衡分析..."):
            try:
                response = model.generate_content(content)
                st.success("✨ 乾摩擦分析完成！")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{str(e)}")