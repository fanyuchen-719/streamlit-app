import streamlit as st
from PIL import Image
from google import genai
from google.genai import types
import time

# 💡 讀取金鑰池（自動抓取主要與備用金鑰）
api_keys = []
if "GEMINI_API_KEY" in st.secrets and st.secrets["GEMINI_API_KEY"]:
    api_keys.append(st.secrets["GEMINI_API_KEY"])
if "GEMINI_API_KEY_BACKUP" in st.secrets and st.secrets["GEMINI_API_KEY_BACKUP"]:
    api_keys.append(st.secrets["GEMINI_API_KEY_BACKUP"])

# 安全檢查：至少要有一把金鑰
if not api_keys:
    st.error("❌ 未在 Streamlit 後台設定任何 GEMINI_API_KEY")
    st.stop()

st.set_page_config(page_title="乾摩擦力 AI 聊天助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 AI 聊天解題助教 (多金鑰不斷電版)")

# 1. 初始化聊天記憶庫與上傳防刷新機制
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# 側邊欄控制面板
with st.sidebar:
    st.header("⚙️ 控制面板")
    st.info(f"🔑 目前已載入的金鑰數量：{len(api_keys)} 把")
    if st.button("🗑️ 清空歷史對話紀錄"):
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()

# 力學教授的靈魂人設
system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。\n"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。\n"
    "【極重要】如果使用者指出你的計算錯誤、公式列錯、或正負號有誤，請虛心檢查並在後續對話中給出修正後的正確解答。\n"
    "【計算規範】請務必多利用內建的『Python Code Execution』工具來計算任何三角函數、小數點運算或解聯立方程式，確保最終數值與課本解答完全一致。"
)

# 2. 畫出歷史對話訊息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image") is not None:
            st.image(msg["image"], caption="💡 本輪附帶的力學題目照片", width=400)
        st.markdown(msg["content"])

st.markdown("---")

# 3. 把上傳區黏在輸入框上方
uploaded_file = st.file_uploader(
    "📎 點擊或拖曳上傳本輪題目照片（選填，送出後會自動融入對話）：", 
    type=["jpg", "jpeg", "png"],
    key=f"friction_upload_{st.session_state.uploader_key}"
)

if uploaded_file:
    st.image(uploaded_file, caption="👀 準備送出的照片預覽", width=200)

# 4. 底部聊天輸入框
if user_input := st.chat_input("在這裡輸入題目，或是直接回覆：『你第三步算錯了，正負號應該是...』"):
    
    current_image = None
    if uploaded_file:
        current_image = Image.open(uploaded_file)
    
    with st.chat_message("user"):
        if current_image:
            st.image(current_image, caption="上傳的題目照片", width=400)
        st.markdown(user_input)
    
    # 存入 session_state 歷史紀錄
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input,
        "image": current_image
    })
    
    # ─── 5. 安全打包機制：避開 Pydantic ValidationError ───
    content_list = []
    if current_image:
        content_list.append(current_image)
        
    # 將歷史對話與圖片註記串成純文字 context 餵給模型
    history_context = "【以下是歷史對話紀錄與使用者的最新回覆】\n"
    for msg in st.session_state.messages:
        role_label = "使用者 (User)" if msg["role"] == "user" else "力學教授 (AI)"
        img_note = "（附帶了題目照片）" if msg.get("image") is not None else ""
        history_context += f"{role_label}: {img_note}{msg['content']}\n\n"
    
    content_list.append(history_context)
    
    # ─── 6. 智慧型自動重試 + 多金鑰無縫輪替防禦罩！ ───
    response_text = ""
    max_retries = 4
    warning_placeholder = st.empty()
    
    for attempt in range(max_retries):
        key_index = attempt % len(api_keys)
        current_key = api_keys[key_index]
        
        # 動態初始化當前嘗試的 Client
        current_client = genai.Client(api_key=current_key)
        
        with st.spinner(f"力學教授正在計算中... (嘗試第 {attempt + 1} 次，使用金鑰群組 {key_index + 1})"):
            try:
                response = current_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=content_list,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=[types.Tool(code_execution=types.ToolCodeExecution())]
                    )
                )
                response_text = response.text
                warning_placeholder.empty()
                break  # 成功拿到回應，直接跳出重試迴圈
                
            except Exception as e:
                error_msg = str(e)
                
                # 如果到最後一次嘗試都失敗了，才噴錯誤訊息
                if attempt == max_retries - 1:
                    warning_placeholder.empty()
                    st.error(f"❌ 所有備用金鑰皆嘗試失敗。請稍候重試。錯誤訊息：{error_msg}")
                    st.stop()
                
                # 🛑 狀況 A：踩到免費版每分鐘限制 (429 / RESOURCE_EXHAUSTED)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if len(api_keys) > 1:
                        warning_placeholder.warning(f"⚠️ 當前金鑰 {key_index + 1} 達到限制！正在無縫切換至下一把備用金鑰...")
                        time.sleep(2)  # 稍微緩衝 2 秒直接進下一個迴圈換 Key 挑戰
                    else:
                        wait_time = 35 if attempt == 0 else 55
                        warning_placeholder.warning(f"🛑 只有單把金鑰且觸發限制，將於 {wait_time} 秒後自動重試...")
                        time.sleep(wait_time)
                
                # ⏳ 狀況 B：伺服器大塞車 (503 / UNAVAILABLE)
                elif "503" in error_msg or "UNAVAILABLE" in error_msg:
                    wait_time = (attempt + 1) * 3
                    warning_placeholder.warning(f"⏳ Google 伺服器忙碌 (503)，將於 {wait_time} 秒後自動重新排隊...")
                    time.sleep(wait_time)
                
                # ❌ 狀況 C：其餘不可預期的連線錯誤（例如金鑰真的填錯 401）
                else:
                    warning_placeholder.empty()
                    st.error(f"❌ 遇到非預期連線錯誤：{error_msg}")
                    st.stop()
                        
    # 7. 顯示 AI 回應並存入記憶
    if response_text:
        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
    # 8. 更新 key 讓上傳欄位歸零，並刷新網頁
    st.session_state.uploader_key += 1
    st.rerun()