import streamlit as st
import google.generativeai as genai
import re

# 這裡保留你原本設定金鑰與初始化
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 1

# --- 讀取金鑰與設定模型 ---
# 提示：請確保你在 Streamlit Secrets 裡配置的 API 金鑰是來自「建立新專案」而非舊的預設項目
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("未偵測到 GEMINI_API_KEY，請檢查 Streamlit Secrets 設定。")

system_prompt = """你是一位精通工程力學（Statics / Dynamics）的教授。
請針對使用者上傳的力學題目圖片或文本，進行精確的受力分析、列出平衡方程式並求解。
"""

try:
    # 💡 這裡已將原先每日限流 20 次的 2.5-flash，修正為每日 1500 次免費額度的 1.5-flash
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',  
        system_instruction=system_prompt,
        tools=['code_execution']
    )
except Exception as e:
    st.error(f"模型初始化失敗: {e}")

# --- 頁面 UI 結構 ---
st.title("力學題目解題助手")

uploaded_file = st.file_uploader(
    "點擊或拖曳上傳本題目的照片（選填）：", 
    type=["jpg", "png", "jpeg"], 
    key=f"uploader_{st.session_state.uploader_key}"
)

user_input = st.text_input("在這裡輸入題目，或是直接回覆修正意見...", key="user_question")

# --- 歷史對話紀錄處理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 觸發計算邏輯 ---
if st.button("開始計算") or user_input:
    if not user_input and not uploaded_file:
        st.warning("請輸入文字題目或上傳圖片。")
    else:
        # 處理使用者輸入內容
        content_list = []
        if user_input:
            content_list.append(user_input)
        if uploaded_file:
            # 這裡讀取圖片檔案
            import PIL.Image
            image = PIL.Image.open(uploaded_file)
            content_list.append(image)
            
        st.session_state.messages.append({"role": "user", "content": user_input if user_input else "視訊/圖片輸入"})
        with st.chat_message("user"):
            if user_input:
                st.markdown(user_input)
            if uploaded_file:
                st.image(image, caption="上傳的題目照片")

        # 呼叫 API 進行生成
        with st.spinner("力學教授正在計算中..."):
            try:
                # 這裡帶入歷史紀錄與當前輸入
                response = model.generate_content(content_list)
                response_text = response.text
            except Exception as e:
                st.error(f"API 呼叫失敗，錯誤訊息：{e}")
                response_text = None

        # --- 處理回應與清除快取（對應你截圖中的第 121-137 行） ---
        if response_text:
            # 💡 這裡保留你原本使用正規表達式拔掉 Markdown 程式碼區塊的邏輯
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
            
            # 觸發強制重新整理以更新上傳組件
            st.session_state.uploader_key += 1
            st.rerun()