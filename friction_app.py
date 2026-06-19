import streamlit as st
from PIL import Image
from google import genai
from google.genai import types  # 💡 新增：導入新版 API 的型態元件，用來開啟計算機工具
import time

# 讀取金鑰
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("❌ 未在 Streamlit 後台設定 GEMINI_API_KEY")
    st.stop()

# 初始化全新 Google GenAI Client
client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="乾摩擦力 AI 聊天助教", layout="wide")
st.title("🤖 ⚙️ 靜力學：乾摩擦力 AI 聊天解題助教 (專業計算防護版)")

# 1. 初始化聊天記憶庫與上傳防刷新機制
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# 側邊欄控制面板
with st.sidebar:
    st.header("⚙️ 控制面板")
    if st.button("🗑️ 清空歷史對話紀錄"):
        st.session_state.messages = []
        st.session_state.uploader_key += 1
        st.rerun()

# 力學教授的靈魂人設（加入引導 AI 使用計算機的指令）
system_prompt = (
    "你是一位精通工程力學的教授，現在要專門解決『乾摩擦力 (Dry Friction)』的靜力學題目。\n"
    "請嚴格依照：1.物理參數、2.狀態假設、3.平衡方程式、4.狀態判斷(滑動或翻倒)、5.最終結論 進行拆解。\n"
    "【極重要】如果使用者指出你的計算錯誤、公式列錯、或正負號有誤，請虛心檢查並在後續對話中給出修正後的正確解答。\n"
    "【計算規範】請務必多利用內建的『Python Code Execution』工具來計算任何三角函數、小數點運算或解聯立方程式，確保最終數值與課本解答完全一致。"
)

# 2. 畫出歷史對話訊息（如果是使用者傳的，照片會直接顯示在對話框裡！）
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "image" in msg and msg["image"] is not None:
            st.image(msg["image"], caption="💡 本輪附帶的力學題目照片", width=400)
        st.markdown(msg["content"])

st.markdown("---")

# 3. 【Gemini 核心體驗】把上傳區黏在輸入框上方
uploaded_file = st.file_uploader(
    "📎 點擊或拖曳上傳本輪題目照片（選填，送出後會自動融入對話）：", 
    type=["jpg", "jpeg", "png"],
    key=f"friction_upload_{st.session_state.uploader_key}"
)

# 如果有選取照片，在下方貼心顯示一塊小小的「預覽圖」
if uploaded_file:
    st.image(uploaded_file, caption="👀 準備送出的照片預覽", width=200)

# 4. 底部聊天輸入框
if user_input := st.chat_input("在這裡輸入題目，或是直接回覆：『你傷到拉力 P 了，摩擦力方向列錯了吧...』"):
    
    # 讀取當前附加的照片
    current_image = None
    if uploaded_file:
        current_image = Image.open(uploaded_file)
    
    # 畫出並存入使用者的對話（文字 + 照片大合體）
    with st.chat_message("user"):
        if current_image:
            st.image(current_image, caption="上傳的題目照片", width=400)
        st.markdown(user_input)
    
    # 将当前对话存入 session_state 历史纪录
    st.session_state.messages.append({
        "role": "user", 
        "content": user_input,
        "image": current_image,
        "has_image": current_image is not None
    })
    
    # 5. 打包要送給 Gemini 的資料
    content_list = []
    if current_image:
        content_list.append(current_image)
        
    # 串接文字歷史紀錄，讓 AI 記住前面的對話脈絡（並提示哪一輪有照片）
    history_context = "【以下是歷史對話紀錄與使用者的最新回覆】\n"
    for msg in st.session_state.messages:
        role_label = "使用者 (User)" if msg["role"] == "user" else "力學教授 (AI)"
        img_note = "（附帶了題目照片）" if msg.get("has_image") else ""
        history_context += f"{role_label}: {img_note}{msg['content']}\n\n"
    
    content_list.append(history_context)
    
    # 6. 智慧型自動重試機制（分流防禦 503 大塞車 與 429 深度冷卻！）
    response_text = ""
    max_retries = 4
    warning_placeholder = st.empty()
    
    for attempt in range(max_retries):
        with st.spinner(f"力學教授正在分析與計算中... (嘗試第 {attempt + 1} 次)"):
            try:
                # 呼叫新版官方 SDK 語法
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=content_list,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        tools=[types.Tool(code_execution=types.ToolCodeExecution())]
                    )
                )
                response_text = response.text
                warning_placeholder.empty()
                break
            except Exception as e:
                error_msg = str(e)
                
                # 如果已經是最後一次嘗試都失敗了，直接噴出錯誤並停住
                if attempt == max_retries - 1:
                    warning_placeholder.empty()
                    st.error(f"❌ 嘗試連線 {max_retries} 次後依然失敗。請稍候重試。錯誤訊息：{error_msg}")
                    st.stop()
                
                # 🛑 狀況 A：踩到免費版每分鐘 20 次限制 (429 RESOURCE_EXHAUSTED)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    # 第一次失敗先忍 35 秒，第二次之後如果還被卡，直接拉長到 55 秒徹底熬過罰站期
                    wait_time = 35 if attempt == 0 else 55
                    warning_placeholder.warning(f"🛑 觸發免費版頻率限制 (429)！為了繞過封鎖，將於 {wait_time} 秒後自動重試，請勿重新整理網頁...")
                    time.sleep(wait_time)
                
                # ⏳ 狀況 B：伺服器大塞車 (503 UNAVAILABLE)
                elif "503" in error_msg or "UNAVAILABLE" in error_msg:
                    wait_time = (attempt + 1) * 4  # 漸進等待：4秒、8秒、12秒
                    warning_placeholder.warning(f"⏳ Google 伺服器忙碌中 (503)，將於 {wait_time} 秒後自動重新排隊...")
                    time.sleep(wait_time)
                
                # ⚠️ 狀況 C：其他突發嚴重錯誤
                else:
                    warning_placeholder.empty()
                    st.error(f"❌ 遇到非預期連線錯誤：{error_msg}")
                    st.stop()
                        
    # 7. 顯示 AI 回應並存入記憶
    if response_text:
        with st.chat_message("assistant"):
            st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        
    # 8. 【魔法時刻】成功拿回答案後，更新 key 讓上傳欄位歸零，並刷新網頁
    st.session_state.uploader_key += 1
    st.rerun()