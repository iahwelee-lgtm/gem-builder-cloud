import streamlit as st
from supabase import create_client, Client
from google import genai
from datetime import datetime, timezone, timedelta
import json
import re


# =========================================================
# 1. 頁面設定
# =========================================================

st.set_page_config(
    page_title="GEM Builder Cloud",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 2. CSS：手機 / 電腦響應式
# =========================================================

st.markdown("""
<style>

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

.gem-card {
    border: 1px solid #dddddd;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
    background: #ffffff;
}

.chat-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 4px;
}

.chat-date {
    font-size: 12px;
    color: #777777;
}

.chat-sidebar-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 10px;
}

.small-text {
    color: #777777;
    font-size: 13px;
}

.stat-box {
    border: 1px solid #dddddd;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    background: #ffffff;
}

.stat-number {
    font-size: 28px;
    font-weight: 700;
}

.stat-label {
    font-size: 13px;
    color: #666666;
}

@media (max-width: 768px) {

    .main .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    button {
        width: 100% !important;
    }

    .stat-box {
        margin-bottom: 10px;
    }

}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. Secrets
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


# =========================================================
# 4. 初始化 Supabase / Gemini
# =========================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================================================
# 5. Gemini 模型
# =========================================================

MODEL_OPTIONS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]


# =========================================================
# 6. Session State
# =========================================================

if "selected_gem_id" not in st.session_state:
    st.session_state.selected_gem_id = None

if "selected_chat_id" not in st.session_state:
    st.session_state.selected_chat_id = None

if "chat_search" not in st.session_state:
    st.session_state.chat_search = ""

if "editing_chat_title" not in st.session_state:
    st.session_state.editing_chat_title = False

if "show_create_chat" not in st.session_state:
    st.session_state.show_create_chat = False


# =========================================================
# 7. GEM CRUD
# =========================================================

def get_gems():
    try:
        result = (
            supabase
            .table("gems")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        return result.data or []

    except Exception as e:
        st.error(f"讀取 GEM 失敗：{e}")
        return []


def get_gem(gem_id):
    try:
        result = (
            supabase
            .table("gems")
            .select("*")
            .eq("id", gem_id)
            .single()
            .execute()
        )

        return result.data

    except Exception:
        return None


def create_gem(name, role, workflow, greeting):
    try:
        result = (
            supabase
            .table("gems")
            .insert({
                "name": name,
                "role": role,
                "workflow": workflow,
                "greeting": greeting,
                "user_id": None
            })
            .execute()
        )

        return result.data

    except Exception as e:
        st.error(f"建立 GEM 失敗：{e}")
        return None


def update_gem(gem_id, name, role, workflow, greeting):
    try:
        result = (
            supabase
            .table("gems")
            .update({
                "name": name,
                "role": role,
                "workflow": workflow,
                "greeting": greeting
            })
            .eq("id", gem_id)
            .execute()
        )

        return result.data

    except Exception as e:
        st.error(f"更新 GEM 失敗：{e}")
        return None


def delete_gem(gem_id):
    try:
        (
            supabase
            .table("gems")
            .delete()
            .eq("id", gem_id)
            .execute()
        )

        return True

    except Exception as e:
        st.error(f"刪除 GEM 失敗：{e}")
        return False


# =========================================================
# 8. Knowledge Base
# =========================================================

def get_knowledge(gem_id):
    try:
        result = (
            supabase
            .table("gem_knowledge")
            .select("*")
            .eq("gem_id", gem_id)
            .order("id", desc=False)
            .execute()
        )

        return result.data or []

    except Exception as e:
        st.error(f"讀取 Knowledge 失敗：{e}")
        return []


def create_knowledge(gem_id, title, content):
    try:
        result = (
            supabase
            .table("gem_knowledge")
            .insert({
                "gem_id": gem_id,
                "title": title,
                "content": content
            })
            .execute()
        )

        return result.data

    except Exception as e:
        st.error(f"建立 Knowledge 失敗：{e}")
        return None


def update_knowledge(knowledge_id, title, content):
    try:
        result = (
            supabase
            .table("gem_knowledge")
            .update({
                "title": title,
                "content": content
            })
            .eq("id", knowledge_id)
            .execute()
        )

        return result.data

    except Exception as e:
        st.error(f"更新 Knowledge 失敗：{e}")
        return None


def delete_knowledge(knowledge_id):
    try:
        (
            supabase
            .table("gem_knowledge")
            .delete()
            .eq("id", knowledge_id)
            .execute()
        )

        return True

    except Exception as e:
        st.error(f"刪除 Knowledge 失敗：{e}")
        return False


# =========================================================
# 9. Chat Sessions
# =========================================================

def get_chat_sessions(gem_id):
    try:
        result = (
            supabase
            .table("gem_chat_sessions")
            .select("*")
            .eq("gem_id", gem_id)
            .order("updated_at", desc=True)
            .execute()
        )

        return result.data or []

    except Exception as e:
        st.error(f"讀取聊天紀錄失敗：{e}")
        return []


def create_chat_session(gem_id, title="新對話"):
    try:
        result = (
            supabase
            .table("gem_chat_sessions")
            .insert({
                "gem_id": gem_id,
                "title": title
            })
            .execute()
        )

        if result.data:
            return result.data[0]

        return None

    except Exception as e:
        st.error(f"建立聊天失敗：{e}")
        return None


def update_chat_title(chat_id, title):
    try:
        result = (
            supabase
            .table("gem_chat_sessions")
            .update({
                "title": title,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", chat_id)
            .execute()
        )

        return result.data

    except Exception as e:
        st.error(f"修改聊天名稱失敗：{e}")
        return None


def touch_chat_session(chat_id):
    try:
        (
            supabase
            .table("gem_chat_sessions")
            .update({
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", chat_id)
            .execute()
        )

    except Exception:
        pass


def delete_chat_session(chat_id):
    try:

        (
            supabase
            .table("gem_chat_messages")
            .delete()
            .eq("chat_id", chat_id)
            .execute()
        )

        (
            supabase
            .table("gem_chat_sessions")
            .delete()
            .eq("id", chat_id)
            .execute()
        )

        return True

    except Exception as e:
        st.error(f"刪除聊天失敗：{e}")
        return False


def clear_chat_messages(chat_id):
    try:
        (
            supabase
            .table("gem_chat_messages")
            .delete()
            .eq("chat_id", chat_id)
            .execute()
        )

        touch_chat_session(chat_id)

        return True

    except Exception as e:
        st.error(f"清除聊天失敗：{e}")
        return False


# =========================================================
# 10. Chat Messages
# =========================================================

def get_chat_messages(chat_id):
    try:
        result = (
            supabase
            .table("gem_chat_messages")
            .select("*")
            .eq("chat_id", chat_id)
            .order("id", desc=False)
            .execute()
        )

        return result.data or []

    except Exception as e:
        st.error(f"讀取聊天內容失敗：{e}")
        return []


def create_chat_message(chat_id, role, content):
    try:
        result = (
            supabase
            .table("gem_chat_messages")
            .insert({
                "chat_id": chat_id,
                "role": role,
                "content": content
            })
            .execute()
        )

        touch_chat_session(chat_id)

        return result.data

    except Exception as e:
        st.error(f"保存聊天訊息失敗：{e}")
        return None


# =========================================================
# 11. Gemini 基礎功能
# =========================================================

def ask_gemini(prompt, model):
    try:

        response = gemini_client.models.generate_content(
            model=model,
            contents=prompt
        )

        return response.text

    except Exception as e:

        error_text = str(e)

        if "429" in error_text:
            return (
                "⚠️ Gemini 目前達到 API 使用額度限制。\n\n"
                "請稍後再試，或到左側切換其他 Gemini 模型。"
            )

        return f"⚠️ Gemini 發生錯誤：{error_text}"


# =========================================================
# 12. 建立聊天 Prompt
# =========================================================

def build_chat_prompt(gem, knowledge_list, messages):

    role = gem.get("role", "")
    workflow = gem.get("workflow", "")
    greeting = gem.get("greeting", "")

    prompt = f"""
你現在是一個 GEM Builder Cloud 中的專業 GEM。

【GEM 名稱】
{gem.get("name", "")}

【Role】
{role}

【Workflow & Rules】
{workflow}

【Greeting】
{greeting}

"""

    if knowledge_list:

        prompt += """
【Knowledge 知識庫】
"""

        for item in knowledge_list:

            prompt += f"""
### {item.get("title", "")}

{item.get("content", "")}

"""

    prompt += """
【對話規則】

1. 你必須遵守以上 Role。
2. 你必須遵守 Workflow & Rules。
3. 優先使用 Knowledge 中提供的資訊。
4. 如果 Knowledge 沒有相關資料，不要假裝知道。
5. 回答要自然、清楚、有幫助。
6. 要記住本次聊天前面的內容。
7. 不要每一次都重新介紹自己。
8. 使用繁體中文回答。

【目前對話】
"""

    for message in messages:

        role_name = message.get("role", "")

        if role_name == "user":
            role_name = "使用者"

        elif role_name == "assistant":
            role_name = "GEM"

        prompt += f"""
{role_name}：
{message.get("content", "")}

"""

    return prompt


# =========================================================
# 13. 自動產生聊天名稱
# =========================================================

def generate_chat_title(message):

    text = message.strip()

    if not text:
        return "新對話"

    text = re.sub(r"\s+", " ", text)

    if len(text) > 25:
        text = text[:25] + "..."

    return text


# =========================================================
# 14. 日期分類
# =========================================================

def parse_datetime(value):

    if not value:
        return None

    try:

        value = value.replace("Z", "+00:00")

        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:
        return None


def chat_date_group(value):

    dt = parse_datetime(value)

    if dt is None:
        return "其他"

    now = datetime.now(timezone.utc)

    today = now.date()
    yesterday = today - timedelta(days=1)

    if dt.date() == today:
        return "今天"

    if dt.date() == yesterday:
        return "昨天"

    if dt.date() >= today - timedelta(days=7):
        return "最近 7 天"

    return "更早"


# =========================================================
# 15. 聊天紀錄搜尋
# =========================================================

def filter_chat_sessions(sessions, keyword):

    if not keyword:
        return sessions

    keyword = keyword.lower().strip()

    result = []

    for chat in sessions:

        title = str(chat.get("title", "")).lower()

        if keyword in title:
            result.append(chat)

    return result


# =========================================================
# 16. 聊天紀錄中心
# =========================================================

def show_chat_history_center(gem):

    gem_id = gem.get("id")

    st.markdown("## 💬 聊天紀錄中心")

    st.caption(
        f"目前 GEM：{gem.get('name', '未命名 GEM')}"
    )

    sessions = get_chat_sessions(gem_id)

    # -----------------------------------------------------
    # 頂部操作列
    # -----------------------------------------------------

    col1, col2 = st.columns([3, 1])

    with col1:

        search_keyword = st.text_input(
            "🔎 搜尋聊天",
            value=st.session_state.chat_search,
            placeholder="輸入聊天名稱搜尋...",
            key=f"chat_search_{gem_id}"
        )

        st.session_state.chat_search = search_keyword

    with col2:

        st.write("")

        if st.button(
            "➕ 新增聊天",
            use_container_width=True,
            key=f"new_chat_top_{gem_id}"
        ):

            new_chat = create_chat_session(
                gem_id,
                "新對話"
            )

            if new_chat:

                st.session_state.selected_chat_id = new_chat["id"]

                st.session_state.editing_chat_title = False

                st.rerun()

    # -----------------------------------------------------
    # 過濾
    # -----------------------------------------------------

    sessions = filter_chat_sessions(
        sessions,
        st.session_state.chat_search
    )

    if not sessions:

        st.info(
            "目前沒有符合條件的聊天紀錄。"
        )

        if not st.session_state.chat_search:

            if st.button(
                "💬 開始第一個對話",
                use_container_width=True,
                key=f"first_chat_{gem_id}"
            ):

                new_chat = create_chat_session(
                    gem_id,
                    "新對話"
                )

                if new_chat:

                    st.session_state.selected_chat_id = new_chat["id"]

                    st.rerun()

        return

    # -----------------------------------------------------
    # 如果沒有選擇聊天，自動選最新
    # -----------------------------------------------------

    chat_ids = [
        chat.get("id")
        for chat in sessions
    ]

    if (
        st.session_state.selected_chat_id is None
        or
        st.session_state.selected_chat_id not in chat_ids
    ):

        st.session_state.selected_chat_id = chat_ids[0]

    # -----------------------------------------------------
    # 左右欄
    # -----------------------------------------------------

    left_col, right_col = st.columns(
        [1, 2.7],
        gap="large"
    )

    # =====================================================
    # 左側：聊天紀錄列表
    # =====================================================

    with left_col:

        st.markdown(
            '<div class="chat-sidebar-title">🗂️ 我的聊天</div>',
            unsafe_allow_html=True
        )

        groups = {
            "今天": [],
            "昨天": [],
            "最近 7 天": [],
            "更早": [],
            "其他": []
        }

        for chat in sessions:

            group = chat_date_group(
                chat.get("updated_at")
            )

            groups.setdefault(group, []).append(chat)

        for group_name in [
            "今天",
            "昨天",
            "最近 7 天",
            "更早",
            "其他"
        ]:

            group_chats = groups.get(group_name, [])

            if not group_chats:
                continue

            st.markdown(
                f"**{group_name}**"
            )

            for chat in group_chats:

                chat_id = chat.get("id")

                title = chat.get(
                    "title",
                    "新對話"
                )

                if not title:
                    title = "新對話"

                # Streamlit button 不能真正呈現 active CSS，
                # 所以使用不同文字提示目前選取項目。

                if chat_id == st.session_state.selected_chat_id:

                    button_label = f"🔵 {title}"

                else:

                    button_label = f"💬 {title}"

                if st.button(
                    button_label,
                    key=f"chat_select_{chat_id}",
                    use_container_width=True
                ):

                    st.session_state.selected_chat_id = chat_id

                    st.session_state.editing_chat_title = False

                    st.rerun()

    # =====================================================
    # 右側：目前聊天
    # =====================================================

    with right_col:

        selected_chat = None

        for chat in sessions:

            if chat.get("id") == st.session_state.selected_chat_id:

                selected_chat = chat

                break

        if selected_chat is None:

            st.info("請選擇一個聊天。")
            return

        chat_id = selected_chat.get("id")

        title = selected_chat.get(
            "title",
            "新對話"
        )

        # -------------------------------------------------
        # 聊天標題
        # -------------------------------------------------

        header_col1, header_col2, header_col3 = st.columns(
            [5, 1, 1]
        )

        with header_col1:

            if st.session_state.editing_chat_title:

                new_title = st.text_input(
                    "聊天名稱",
                    value=title,
                    key=f"title_input_{chat_id}"
                )

                save_col, cancel_col = st.columns(2)

                with save_col:

                    if st.button(
                        "💾 儲存名稱",
                        use_container_width=True,
                        key=f"save_title_{chat_id}"
                    ):

                        clean_title = new_title.strip()

                        if not clean_title:
                            clean_title = "新對話"

                        update_chat_title(
                            chat_id,
                            clean_title
                        )

                        st.session_state.editing_chat_title = False

                        st.rerun()

                with cancel_col:

                    if st.button(
                        "取消",
                        use_container_width=True,
                        key=f"cancel_title_{chat_id}"
                    ):

                        st.session_state.editing_chat_title = False

                        st.rerun()

            else:

                st.markdown(
                    f"### 💬 {title}"
                )

        with header_col2:

            if not st.session_state.editing_chat_title:

                if st.button(
                    "📝",
                    help="修改聊天名稱",
                    use_container_width=True,
                    key=f"edit_title_{chat_id}"
                ):

                    st.session_state.editing_chat_title = True

                    st.rerun()

        with header_col3:

            if st.button(
                "🗑️",
                help="刪除這個聊天",
                use_container_width=True,
                key=f"delete_chat_{chat_id}"
            ):

                st.session_state[f"confirm_delete_{chat_id}"] = True

        # -------------------------------------------------
        # 刪除確認
        # -------------------------------------------------

        if st.session_state.get(
            f"confirm_delete_{chat_id}",
            False
        ):

            st.warning(
                "確定要刪除這個聊天嗎？刪除後聊天內容也會一起刪除。"
            )

            confirm_col1, confirm_col2 = st.columns(2)

            with confirm_col1:

                if st.button(
                    "確定刪除",
                    use_container_width=True,
                    key=f"confirm_yes_{chat_id}"
                ):

                    delete_chat_session(chat_id)

                    st.session_state.selected_chat_id = None

                    st.session_state[
                        f"confirm_delete_{chat_id}"
                    ] = False

                    st.rerun()

            with confirm_col2:

                if st.button(
                    "取消",
                    use_container_width=True,
                    key=f"confirm_no_{chat_id}"
                ):

                    st.session_state[
                        f"confirm_delete_{chat_id}"
                    ] = False

                    st.rerun()

        # -------------------------------------------------
        # 聊天內容
        # -------------------------------------------------

        messages = get_chat_messages(chat_id)

        if not messages:

            st.info(
                "👋 這是一個新的聊天。\n\n"
                "在下面輸入你的第一個問題開始對話。"
            )

        else:

            for message in messages:

                role = message.get("role")
                content = message.get("content", "")

                if role == "user":

                    with st.chat_message("user"):

                        st.write(content)

                else:

                    with st.chat_message("assistant"):

                        st.write(content)

        # -------------------------------------------------
        # 底部操作
        # -------------------------------------------------

        st.divider()

        action_col1, action_col2 = st.columns(2)

        with action_col1:

            if st.button(
                "🧹 清除目前聊天內容",
                use_container_width=True,
                key=f"clear_chat_{chat_id}"
            ):

                st.session_state[
                    f"confirm_clear_{chat_id}"
                ] = True

        with action_col2:

            st.caption(
                f"共 {len(messages)} 則訊息"
            )

        # -------------------------------------------------
        # 清除確認
        # -------------------------------------------------

        if st.session_state.get(
            f"confirm_clear_{chat_id}",
            False
        ):

            st.warning(
                "確定要清除這個聊天的所有訊息嗎？"
            )

            clear_col1, clear_col2 = st.columns(2)

            with clear_col1:

                if st.button(
                    "確定清除",
                    use_container_width=True,
                    key=f"clear_yes_{chat_id}"
                ):

                    clear_chat_messages(chat_id)

                    st.session_state[
                        f"confirm_clear_{chat_id}"
                    ] = False

                    st.rerun()

            with clear_col2:

                if st.button(
                    "取消",
                    use_container_width=True,
                    key=f"clear_no_{chat_id}"
                ):

                    st.session_state[
                        f"confirm_clear_{chat_id}"
                    ] = False

                    st.rerun()

        # -------------------------------------------------
        # Chat Input
        # -------------------------------------------------

        model = st.session_state.get(
            "selected_model",
            MODEL_OPTIONS[6]
        )

        user_message = st.chat_input(
            "輸入訊息...",
            key=f"chat_input_{chat_id}"
        )

        if user_message:

            user_message = user_message.strip()

            if not user_message:
                st.stop()

            # ---------------------------------------------
            # 儲存 User
            # ---------------------------------------------

            create_chat_message(
                chat_id,
                "user",
                user_message
            )

            # ---------------------------------------------
            # 第一句話自動命名聊天
            # ---------------------------------------------

            if title == "新對話":

                auto_title = generate_chat_title(
                    user_message
                )

                update_chat_title(
                    chat_id,
                    auto_title
                )

            # ---------------------------------------------
            # 重新讀取完整對話
            # ---------------------------------------------

            current_messages = get_chat_messages(
                chat_id
            )

            knowledge_list = get_knowledge(
                gem_id
            )

            prompt = build_chat_prompt(
                gem,
                knowledge_list,
                current_messages
            )

            # ---------------------------------------------
            # Gemini 回覆
            # ---------------------------------------------

            with st.spinner(
                f"{model} 正在思考..."
            ):

                answer = ask_gemini(
                    prompt,
                    model
                )

            # ---------------------------------------------
            # 保存 AI
            # ---------------------------------------------

            create_chat_message(
                chat_id,
                "assistant",
                answer
            )

            touch_chat_session(
                chat_id
            )

            st.rerun()


# =========================================================
# 17. GEM 詳細頁
# =========================================================

def show_gem_detail(gem):

    if not gem:
        return

    st.markdown(
        f"## 💎 {gem.get('name', '未命名 GEM')}"
    )

    tabs = st.tabs([
        "📋 內容",
        "✏️ 編輯",
        "📚 Knowledge",
        "✨ AI 優化",
        "💬 對話"
    ])

    # =====================================================
    # 內容
    # =====================================================

    with tabs[0]:

        st.subheader("Role")

        st.write(
            gem.get("role", "")
        )

        st.subheader("Workflow & Rules")

        st.write(
            gem.get("workflow", "")
        )

        st.subheader("Greeting")

        st.write(
            gem.get("greeting", "")
        )

    # =====================================================
    # 編輯
    # =====================================================

    with tabs[1]:

        name = st.text_input(
            "GEM 名稱",
            value=gem.get("name", ""),
            key=f"edit_name_{gem['id']}"
        )

        role = st.text_area(
            "Role",
            value=gem.get("role", ""),
            height=200,
            key=f"edit_role_{gem['id']}"
        )

        workflow = st.text_area(
            "Workflow & Rules",
            value=gem.get("workflow", ""),
            height=250,
            key=f"edit_workflow_{gem['id']}"
        )

        greeting = st.text_area(
            "Greeting",
            value=gem.get("greeting", ""),
            height=150,
            key=f"edit_greeting_{gem['id']}"
        )

        if st.button(
            "💾 儲存 GEM",
            use_container_width=True,
            key=f"save_gem_{gem['id']}"
        ):

            update_gem(
                gem["id"],
                name,
                role,
                workflow,
                greeting
            )

            st.success("GEM 已更新！")

            st.rerun()

    # =====================================================
    # Knowledge
    # =====================================================

    with tabs[2]:

        knowledge_list = get_knowledge(
            gem["id"]
        )

        st.subheader(
            f"📚 Knowledge（{len(knowledge_list)} 筆）"
        )

        with st.expander(
            "➕ 新增 Knowledge",
            expanded=False
        ):

            new_title = st.text_input(
                "標題",
                key=f"new_k_title_{gem['id']}"
            )

            new_content = st.text_area(
                "內容",
                height=250,
                key=f"new_k_content_{gem['id']}"
            )

            if st.button(
                "新增 Knowledge",
                use_container_width=True,
                key=f"add_k_{gem['id']}"
            ):

                if not new_title.strip():

                    st.warning("請輸入 Knowledge 標題。")

                elif not new_content.strip():

                    st.warning("請輸入 Knowledge 內容。")

                else:

                    create_knowledge(
                        gem["id"],
                        new_title,
                        new_content
                    )

                    st.success(
                        "Knowledge 已新增！"
                    )

                    st.rerun()

        for item in knowledge_list:

            with st.expander(
                f"📄 {item.get('title', '未命名')}"
            ):

                title_value = st.text_input(
                    "標題",
                    value=item.get("title", ""),
                    key=f"k_title_{item['id']}"
                )

                content_value = st.text_area(
                    "內容",
                    value=item.get("content", ""),
                    height=250,
                    key=f"k_content_{item['id']}"
                )

                col1, col2 = st.columns(2)

                with col1:

                    if st.button(
                        "💾 儲存",
                        use_container_width=True,
                        key=f"save_k_{item['id']}"
                    ):

                        update_knowledge(
                            item["id"],
                            title_value,
                            content_value
                        )

                        st.success(
                            "Knowledge 已更新！"
                        )

                        st.rerun()

                with col2:

                    if st.button(
                        "🗑️ 刪除",
                        use_container_width=True,
                        key=f"delete_k_{item['id']}"
                    ):

                        delete_knowledge(
                            item["id"]
                        )

                        st.success(
                            "Knowledge 已刪除！"
                        )

                        st.rerun()

    # =====================================================
    # AI 優化
    # =====================================================

    with tabs[3]:

        st.subheader(
            "✨ GEM Prompt AI 優化器"
        )

        st.write(
            "使用 Gemini 協助改善目前 GEM 的 Role、Workflow 與 Greeting。"
        )

        optimizer_model = st.selectbox(
            "選擇 Gemini 模型",
            MODEL_OPTIONS,
            index=6,
            key=f"optimizer_model_{gem['id']}"
        )

        if st.button(
            "✨ 開始 AI 優化",
            use_container_width=True,
            key=f"optimize_{gem['id']}"
        ):

            optimize_prompt = f"""
請幫我優化以下 GEM。

【GEM 名稱】
{gem.get("name", "")}

【Role】
{gem.get("role", "")}

【Workflow & Rules】
{gem.get("workflow", "")}

【Greeting】
{gem.get("greeting", "")}

請輸出：

【優化後 Role】

【優化後 Workflow & Rules】

【優化後 Greeting】

要求：
1. 保留原本核心目的
2. 讓指令更清楚
3. 提升 AI 執行穩定性
4. 使用繁體中文
5. 不要加入不必要的內容
"""

            with st.spinner("AI 優化中..."):

                result = ask_gemini(
                    optimize_prompt,
                    optimizer_model
                )

            st.text_area(
                "AI 優化結果",
                value=result,
                height=500
            )

    # =====================================================
    # 對話
    # =====================================================

    with tabs[4]:

        show_chat_history_center(
            gem
        )


# =========================================================
# 18. Sidebar
# =========================================================

with st.sidebar:

    st.title("☁️ GEM Builder Cloud")

    st.caption(
        "Day 22-D｜完整聊天紀錄中心"
    )

    st.divider()

    st.subheader("🤖 Gemini 模型")

    selected_model = st.selectbox(
        "選擇模型",
        MODEL_OPTIONS,
        index=6
    )

    st.session_state.selected_model = selected_model

    st.divider()

    st.subheader("🧭 功能")

    if st.button(
        "🏠 回到首頁",
        use_container_width=True
    ):

        st.session_state.selected_gem_id = None

        st.session_state.selected_chat_id = None

        st.rerun()


# =========================================================
# 19. 首頁
# =========================================================

st.title("☁️ GEM Builder Cloud")

st.caption(
    "你的 GEM 建立、Knowledge 與 AI 對話管理中心"
)


# =========================================================
# 20. 讀取 GEM
# =========================================================

gems = get_gems()


# =========================================================
# 21. 首頁統計
# =========================================================

total_gems = len(gems)

total_knowledge = 0

total_chats = 0

for gem in gems:

    knowledge = get_knowledge(
        gem["id"]
    )

    chats = get_chat_sessions(
        gem["id"]
    )

    total_knowledge += len(knowledge)

    total_chats += len(chats)


col1, col2, col3 = st.columns(3)

with col1:

    st.markdown(
        f"""
        <div class="stat-box">
            <div class="stat-number">{total_gems}</div>
            <div class="stat-label">GEM</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:

    st.markdown(
        f"""
        <div class="stat-box">
            <div class="stat-number">{total_knowledge}</div>
            <div class="stat-label">Knowledge</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:

    st.markdown(
        f"""
        <div class="stat-box">
            <div class="stat-number">{total_chats}</div>
            <div class="stat-label">聊天紀錄</div>
        </div>
        """,
        unsafe_allow_html=True
    )


st.divider()


# =========================================================
# 22. 建立 GEM
# =========================================================

with st.expander(
    "➕ 建立新的 GEM",
    expanded=False
):

    new_name = st.text_input(
        "GEM 名稱",
        placeholder="例如：職涯諮詢助手"
    )

    new_role = st.text_area(
        "Role",
        placeholder="請輸入這個 GEM 的角色...",
        height=180
    )

    new_workflow = st.text_area(
        "Workflow & Rules",
        placeholder="請輸入工作流程與規則...",
        height=220
    )

    new_greeting = st.text_area(
        "Greeting",
        placeholder="請輸入開場白...",
        height=150
    )

    if st.button(
        "🚀 建立 GEM",
        use_container_width=True
    ):

        if not new_name.strip():

            st.warning(
                "請先輸入 GEM 名稱。"
            )

        else:

            result = create_gem(
                new_name,
                new_role,
                new_workflow,
                new_greeting
            )

            if result:

                st.success(
                    "GEM 建立成功！"
                )

                st.rerun()


# =========================================================
# 23. GEM 搜尋
# =========================================================

st.subheader("💎 我的 GEM")

gem_search = st.text_input(
    "🔎 搜尋 GEM",
    placeholder="輸入 GEM 名稱..."
)

filtered_gems = []

for gem in gems:

    if (
        not gem_search.strip()
        or
        gem_search.lower() in gem.get(
            "name",
            ""
        ).lower()
    ):

        filtered_gems.append(gem)


# =========================================================
# 24. GEM 列表
# =========================================================

if not filtered_gems:

    st.info(
        "目前沒有找到 GEM。"
    )

else:

    for gem in filtered_gems:

        with st.container():

            st.markdown(
                f"""
                <div class="gem-card">
                    <div class="chat-title">
                        💎 {gem.get("name", "未命名 GEM")}
                    </div>
                    <div class="small-text">
                        ID：{gem.get("id")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "👁️ 開啟 GEM",
                    use_container_width=True,
                    key=f"open_{gem['id']}"
                ):

                    st.session_state.selected_gem_id = gem["id"]

                    st.session_state.selected_chat_id = None

                    st.rerun()

            with col2:

                if st.button(
                    "💬 直接聊天",
                    use_container_width=True,
                    key=f"chat_{gem['id']}"
                ):

                    st.session_state.selected_gem_id = gem["id"]

                    sessions = get_chat_sessions(
                        gem["id"]
                    )

                    if sessions:

                        st.session_state.selected_chat_id = sessions[0]["id"]

                    else:

                        new_chat = create_chat_session(
                            gem["id"],
                            "新對話"
                        )

                        if new_chat:

                            st.session_state.selected_chat_id = new_chat["id"]

                    st.rerun()

            with col3:

                if st.button(
                    "🗑️ 刪除 GEM",
                    use_container_width=True,
                    key=f"delete_gem_{gem['id']}"
                ):

                    st.session_state[
                        f"confirm_gem_delete_{gem['id']}"
                    ] = True

            if st.session_state.get(
                f"confirm_gem_delete_{gem['id']}",
                False
            ):

                st.warning(
                    f"確定要刪除「{gem.get('name')}」嗎？"
                )

                confirm1, confirm2 = st.columns(2)

                with confirm1:

                    if st.button(
                        "確定刪除",
                        use_container_width=True,
                        key=f"yes_gem_delete_{gem['id']}"
                    ):

                        delete_gem(
                            gem["id"]
                        )

                        st.session_state.selected_gem_id = None

                        st.success(
                            "GEM 已刪除！"
                        )

                        st.rerun()

                with confirm2:

                    if st.button(
                        "取消",
                        use_container_width=True,
                        key=f"no_gem_delete_{gem['id']}"
                    ):

                        st.session_state[
                            f"confirm_gem_delete_{gem['id']}"
                        ] = False

                        st.rerun()


# =========================================================
# 25. GEM 詳細頁
# =========================================================

if st.session_state.selected_gem_id:

    selected_gem = get_gem(
        st.session_state.selected_gem_id
    )

    if selected_gem:

        st.divider()

        show_gem_detail(
            selected_gem
        )

    else:

        st.warning(
            "找不到這個 GEM。"
        )

        st.session_state.selected_gem_id = None