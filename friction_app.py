import streamlit as st
from PIL import Image
import google.generativeai as genai  # ✨ 使用最穩定的經典庫，全面避開 401 與 Pydantic 錯誤
import time

# 💡 讀取金鑰池
api_keys = []
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_keys.append(st.secrets["GEMINI_API_KEY"])
if "GEMINI_API_KEY_BACKUP" in st.secrets and st.secrets["GEMINI_API_KEY_BACKUP"]:
    api_keys.append(st.secrets["GEMINI_API_KEY_BACKUP"])

if not api_keys:
    st.error("❌ 未在 Streamlit 後台設定任何 GEMINI_API_KEY")
    st.stop()

st.set_page_config(page_title="乾摩擦力 AI 聊天助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 AI 聊天解題助教 (經典穩定版)")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

with st.sidebar:
    st.header("⚙️ 控制面板")
    st.info(f"🔑 目前已載入的金鑰數量：{len(api_keys)} 把")
    if st.button("🗑️ 清空歷史對話紀錄"):
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()

system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。\n"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。\n"
    "【極重要】如果使用者指出你的計算錯誤、公式列错、或正負號有誤，請虛心檢查並在後續對話中給出修正後的正確解答。\n"
    "【計算規範】請務必多利用內建的『Python Code Execution』工具來計算任何三角函數、小數點運算或解聯立方程式，確保最終數值與課本解答完全一致。\n"
    "【⚠️絕對隱藏規範】你在後台調用 Python 工具計算時，請默默執行就好。絕對、千萬『不要』在最終的聊天回覆中用任何代碼塊（例如 ```python）把你的 Python 原始碼或 print() 的計算結果重複貼出來！請將程式碼完全隱藏，使用者只需要看到你精美乾淨的力學分析步驟與最終答案。"
)

# 顯示歷史對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image") is not None:
            st.image(msg["image"], caption="💡 本輪附帶的力學題目照片", width=400)
        st.markdown(msg["content"])

st.markdown("---")

uploaded_file = st.file_uploader(
    "📎 點擊或拖曳上傳本輪題目照片（選填）：", 
    type=["jpg", "jpeg", "png"],
    key=f"friction_upload_{st.session_state.uploader_key}"
)

if uploaded_file:
    st.image(uploaded_file, caption="👀 準備送出的照片預覽", width=200)

if user_input := st.chat_input("在這裡輸入題目，或是直接回覆修正意見..."):
    
    current_image = None
    if uploaded_file:
        current_image = Image.open(uploaded_file)
    
    with st.chat_message("user"):
        if current_image:
            st.image(current_image, caption="上傳的題目照片", width=400)
        st.markdown(user_input)
    
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input,
        "image": current_image
    })
    
    # ─── 經典版安全打包：純列表格式，絕對不噴 Pydantic 錯誤 ───
    content_list = []
    if current_image:
        content_list.append(current_image)
        
    history_context = "【以下是歷史對話紀錄與使用者的最新回覆】\n"
    for msg in st.session_state.messages:
        role_label = "使用者 (User)" if msg["role"] == "user" else "力學教授 (AI)"
        img_note = "（附帶了題目照片）" if msg.get("image") is not None else ""
        history_context += f"{role_label}: {img_note}{msg['content']}\n\n"
    
    content_list.append(history_context)
    
    response_text = ""
    max_retries = len(api_keys)
    warning_placeholder = st.empty()
    
    # 🔄 進入金鑰輪詢迴圈
    for attempt in range(max_retries):
        current_key = api_keys[attempt]
        
        with st.spinner(f"力學教授正在計算中... (使用金鑰 {attempt + 1}/{len(api_keys)})"):
            try:
                # 經典版配置與呼叫方式
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    system_instruction=system_prompt,
                    tools=['code_execution']
                )
                
                response = model.generate_content(content_list)
                response_text = response.text
                
                if response_text:
                    warning_placeholder.empty()
                    break  # 🎯 成功拿到答案，直接殺出迴圈！
                    
            except Exception as e:
                error_msg = str(e)
                if attempt == max_retries - 1:
                    warning_placeholder.empty()
                    st.error(f"❌ 所有金鑰皆嘗試失敗。請確認是否已更換為『新專案』金鑰。錯誤訊息：{error_msg}")
                    st.stop()
                else:
                    # ⚠️ 發生異常時僅噴出黃色警告，不中斷，等待 1.5 秒後讓迴圈自動換下一把
                    warning_placeholder.warning(f"⚠️ 金鑰 {attempt + 1} 異常，正在切換至下一把... (錯誤: {error_msg})")
                    time.sleep(1.5)

    # ─── 💡 核心修正：跳出迴圈後（代表成功拿到內容），才進行畫面渲染 ───
    if response_text:
        import re
        # 1. 挖掉帶有 ```python ... ``` 的區塊
        clean_text = re.sub(r'```python.*?```', '', response_text, flags=re.DOTALL)
        # 2. 保險起見，連單純的 ``` ... ``` 區塊也一起挖掉
        clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
        # 3. 修剪掉前後多餘的換行
        clean_text = clean_text.strip()
        
        # 顯示乾淨的力學分析結果
        with st.chat_message("assistant"):
            st.markdown(clean_text)
        st.session_state.messages.append({"role": "assistant", "content": clean_text})
        
        st.session_state.uploader_key += 1
        st.rerun()