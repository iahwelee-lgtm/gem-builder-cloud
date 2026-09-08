import streamlit as st
import json
import html
from datetime import datetime
from google import genai
from supabase import create_client


# =========================================================
# GEM Builder Cloud 2.0
# Day 24-A
# 專業版 Dashboard ＋ GEM Card
#
# 基礎版本：
# GitHub Day 23-E
#
# 本版本重點：
# 1. 專業 Dashboard
# 2. GEM 卡片
# 3. 快速操作區
# 4. 最近 GEM
# 5. 保留 Gemini 自動模型偵測
# 6. 保留 Supabase
# 7. 保留所有既有功能
# =========================================================


# =========================================================
# 1. Streamlit 基本設定
# =========================================================

st.set_page_config(
    page_title="GEM Builder Cloud",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# 2. CSS
# =========================================================

st.markdown(
    """
    <style>

    /* =====================================================
       全站
       ===================================================== */

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
        max-width: 1400px;
    }


    /* =====================================================
       標題
       ===================================================== */

    h1 {
        font-size: 2.2rem !important;
        font-weight: 750 !important;
    }

    h2 {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
    }

    h3 {
        font-size: 1.3rem !important;
        font-weight: 700 !important;
    }


    /* =====================================================
       按鈕
       ===================================================== */

    .stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-weight: 600;
    }

    .stDownloadButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-weight: 600;
    }


    /* =====================================================
       輸入框
       ===================================================== */

    textarea,
    input {
        font-size: 16px !important;
    }


    /* =====================================================
       Selectbox
       ===================================================== */

    [data-baseweb="select"] {
        font-size: 16px !important;
    }

    [data-baseweb="select"] * {
        color: inherit;
    }

    [data-baseweb="popover"] {
        z-index: 999999 !important;
    }


    /* =====================================================
       模型狀態
       ===================================================== */

    .model-status {
        padding: 13px 17px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 20px;
        font-size: 15px;
        font-weight: 600;
    }


    /* =====================================================
       Dashboard Hero
       ===================================================== */

    .dashboard-hero {
        padding: 30px;
        border-radius: 20px;
        border: 1px solid rgba(128,128,128,0.22);
        margin-bottom: 25px;
    }

    .dashboard-hero-title {
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .dashboard-hero-subtitle {
        font-size: 16px;
        opacity: 0.75;
        line-height: 1.7;
    }


    /* =====================================================
       Dashboard Section
       ===================================================== */

    .dashboard-section-title {
        font-size: 20px;
        font-weight: 750;
        margin-top: 10px;
        margin-bottom: 15px;
    }


    /* =====================================================
       Dashboard Stats
       ===================================================== */

    .stat-card {
        padding: 20px;
        border-radius: 16px;
        border: 1px solid rgba(128,128,128,0.22);
        min-height: 125px;
    }

    .stat-icon {
        font-size: 25px;
        margin-bottom: 8px;
    }

    .stat-label {
        font-size: 14px;
        opacity: 0.7;
    }

    .stat-value {
        font-size: 30px;
        font-weight: 800;
        margin-top: 3px;
    }

    .stat-description {
        font-size: 12px;
        opacity: 0.6;
        margin-top: 4px;
    }


    /* =====================================================
       GEM Card
       ===================================================== */

    .gem-card {
        padding: 20px;
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 16px;
        margin-bottom: 8px;
        min-height: 210px;
    }

    .gem-card-icon {
        font-size: 28px;
        margin-bottom: 8px;
    }

    .gem-card-title {
        font-size: 20px;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .gem-card-description {
        font-size: 14px;
        line-height: 1.6;
        opacity: 0.75;
        min-height: 46px;
    }

    .gem-card-meta {
        margin-top: 15px;
        padding-top: 12px;
        border-top: 1px solid rgba(128,128,128,0.15);
        font-size: 12px;
        opacity: 0.7;
    }


    /* =====================================================
       Quick Action
       ===================================================== */

    .quick-action-label {
        font-size: 12px;
        opacity: 0.65;
        margin-bottom: 3px;
    }


    /* =====================================================
       Chat
       ===================================================== */

    .chat-user {
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid rgba(128,128,128,0.2);
    }

    .chat-ai {
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid rgba(128,128,128,0.2);
    }


    /* =====================================================
       回到頁首
       ===================================================== */

    .scroll-top-space {
        height: 20px;
    }


    /* =====================================================
       手機
       ===================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
            padding-bottom: 4rem;
        }

        h1 {
            font-size: 1.65rem !important;
        }

        h2 {
            font-size: 1.4rem !important;
        }

        h3 {
            font-size: 1.15rem !important;
        }

        .stButton > button {
            width: 100%;
            min-height: 50px;
            font-size: 16px;
        }

        .stDownloadButton > button {
            width: 100%;
            min-height: 50px;
            font-size: 16px;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.8rem;
        }

        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            white-space: nowrap !important;
            display: flex !important;
        }

        [data-baseweb="tab"] {
            min-width: 105px !important;
        }

        [data-baseweb="select"] {
            width: 100% !important;
        }

        [data-baseweb="select"] > div {
            min-height: 48px !important;
        }

        .model-status {
            font-size: 14px;
        }

        .dashboard-hero {
            padding: 22px;
            border-radius: 16px;
        }

        .dashboard-hero-title {
            font-size: 23px;
        }

        .dashboard-hero-subtitle {
            font-size: 14px;
        }

        .stat-card {
            min-height: 105px;
            padding: 15px;
        }

        .stat-value {
            font-size: 25px;
        }

        .gem-card {
            min-height: auto;
            padding: 17px;
        }

        .gem-card-title {
            font-size: 18px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 3. Secrets
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]


# =========================================================
# 4. Supabase
# =========================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# =========================================================
# 5. Gemini Client
# =========================================================

def get_gemini_client():

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# 6. 取得可用 Gemini 模型
# =========================================================

@st.cache_data(ttl=3600)
def get_available_models():

    fallback_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro"
    ]

    try:

        client = get_gemini_client()

        models = client.models.list()

        available_models = []

        for model in models:

            try:

                model_name = getattr(
                    model,
                    "name",
                    None
                )

                if not model_name:
                    continue

                if model_name.startswith("models/"):

                    model_name = model_name.replace(
                        "models/",
                        ""
                    )

                if "gemini" not in model_name.lower():
                    continue

                if "embedding" in model_name.lower():
                    continue

                if "imagen" in model_name.lower():
                    continue

                if model_name not in available_models:

                    available_models.append(
                        model_name
                    )

            except Exception:

                continue

        if available_models:

            return available_models

        return fallback_models

    except Exception:

        return fallback_models


# =========================================================
# 7. Session State
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "首頁"


if "selected_gem_id" not in st.session_state:
    st.session_state.selected_gem_id = None


if "selected_chat_session_id" not in st.session_state:
    st.session_state.selected_chat_session_id = None


if "gemini_result" not in st.session_state:
    st.session_state.gemini_result = ""


if "optimizer_result" not in st.session_state:
    st.session_state.optimizer_result = ""


if "delete_confirm" not in st.session_state:
    st.session_state.delete_confirm = None


if "knowledge_delete_confirm" not in st.session_state:
    st.session_state.knowledge_delete_confirm = None


if "available_models" not in st.session_state:

    st.session_state.available_models = (
        get_available_models()
    )


if not st.session_state.available_models:

    st.session_state.available_models = [
        "gemini-2.5-flash"
    ]


if "selected_model" not in st.session_state:

    st.session_state.selected_model = (
        st.session_state.available_models[0]
    )


if (
    st.session_state.selected_model
    not in st.session_state.available_models
):

    st.session_state.selected_model = (
        st.session_state.available_models[0]
    )


# =========================================================
# 8. Gemini API
# =========================================================

def ask_gemini(prompt):

    try:

        client = get_gemini_client()

        model = st.session_state.selected_model

        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        if response and response.text:

            return response.text

        return "Gemini 沒有產生內容。"

    except Exception as e:

        return f"❌ Gemini 發生錯誤：{str(e)}"


# =========================================================
# 9. 模型狀態
# =========================================================

def show_model_status():

    current_model = (
        st.session_state.selected_model
    )

    st.markdown(
        f"""
        <div class="model-status">
        🤖 <b>目前使用 AI 模型：</b>
        {html.escape(current_model)}
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 10. GEM：取得全部
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

        st.error(
            f"讀取 GEM 失敗：{str(e)}"
        )

        return []


# =========================================================
# 11. GEM：取得單筆
# =========================================================

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


# =========================================================
# 12. GEM：建立
# =========================================================

def create_gem(
    name,
    role,
    workflow,
    greeting
):

    try:

        data = {
            "name": name,
            "role": role,
            "workflow": workflow,
            "greeting": greeting,
            "user_id": None
        }

        result = (
            supabase
            .table("gems")
            .insert(data)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"建立 GEM 失敗：{str(e)}"
        )

        return None


# =========================================================
# 13. GEM：更新
# =========================================================

def update_gem(
    gem_id,
    name,
    role,
    workflow,
    greeting
):

    try:

        data = {
            "name": name,
            "role": role,
            "workflow": workflow,
            "greeting": greeting
        }

        result = (
            supabase
            .table("gems")
            .update(data)
            .eq("id", gem_id)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"更新 GEM 失敗：{str(e)}"
        )

        return None


# =========================================================
# 14. GEM：刪除
# =========================================================

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

        st.error(
            f"刪除 GEM 失敗：{str(e)}"
        )

        return False


# =========================================================
# 15. Knowledge：取得
# =========================================================

def get_knowledge(gem_id):

    try:

        result = (
            supabase
            .table("gem_knowledge")
            .select("*")
            .eq("gem_id", gem_id)
            .order("id")
            .execute()
        )

        return result.data or []

    except Exception:

        return []


# =========================================================
# 16. Knowledge：建立
# =========================================================

def create_knowledge(
    gem_id,
    title,
    content
):

    try:

        data = {
            "gem_id": gem_id,
            "title": title,
            "content": content
        }

        result = (
            supabase
            .table("gem_knowledge")
            .insert(data)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"建立 Knowledge 失敗：{str(e)}"
        )

        return None


# =========================================================
# 17. Knowledge：更新
# =========================================================

def update_knowledge(
    knowledge_id,
    title,
    content
):

    try:

        data = {
            "title": title,
            "content": content
        }

        result = (
            supabase
            .table("gem_knowledge")
            .update(data)
            .eq("id", knowledge_id)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"更新 Knowledge 失敗：{str(e)}"
        )

        return None


# =========================================================
# 18. Knowledge：刪除
# =========================================================

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

    except Exception:

        return False


# =========================================================
# 19. 聊天 Session：取得
# =========================================================

def get_chat_sessions():

    try:

        result = (
            supabase
            .table("chat_sessions")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    except Exception:

        return []


# =========================================================
# 20. 依 GEM 取得聊天 Session
# =========================================================

def get_chat_sessions_by_gem(gem_id):

    try:

        result = (
            supabase
            .table("chat_sessions")
            .select("*")
            .eq("gem_id", gem_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    except Exception:

        return []


# =========================================================
# 21. 建立聊天 Session
# =========================================================

def create_chat_session(
    gem_id,
    title
):

    try:

        data = {
            "gem_id": gem_id,
            "title": title
        }

        result = (
            supabase
            .table("chat_sessions")
            .insert(data)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"建立聊天失敗：{str(e)}"
        )

        return None


# =========================================================
# 22. 刪除聊天 Session
# =========================================================

def delete_chat_session(session_id):

    try:

        (
            supabase
            .table("chat_messages")
            .delete()
            .eq("session_id", session_id)
            .execute()
        )

        (
            supabase
            .table("chat_sessions")
            .delete()
            .eq("id", session_id)
            .execute()
        )

        return True

    except Exception:

        return False


# =========================================================
# 23. 聊天訊息：取得
# =========================================================

def get_chat_messages(session_id):

    try:

        result = (
            supabase
            .table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )

        return result.data or []

    except Exception:

        return []


# =========================================================
# 24. 儲存聊天訊息
# =========================================================

def create_chat_message(
    session_id,
    role,
    content
):

    try:

        data = {
            "session_id": session_id,
            "role": role,
            "content": content
        }

        result = (
            supabase
            .table("chat_messages")
            .insert(data)
            .execute()
        )

        return result.data

    except Exception as e:

        st.error(
            f"儲存聊天訊息失敗：{str(e)}"
        )

        return None


# =========================================================
# 25. GEM → TXT
# =========================================================

def gem_to_txt(gem):

    return f"""
GEM 名稱：
{gem.get("name", "")}

==============================

ROLE
==============================

{gem.get("role", "")}

==============================

WORKFLOW & RULES
==============================

{gem.get("workflow", "")}

==============================

GREETING
==============================

{gem.get("greeting", "")}
""".strip()


# =========================================================
# 26. GEM → JSON
# =========================================================

def gem_to_json(gem):

    data = {

        "name": gem.get("name", ""),

        "role": gem.get("role", ""),

        "workflow": gem.get("workflow", ""),

        "greeting": gem.get("greeting", "")

    }

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# 27. Dashboard：統計卡片
# =========================================================

def show_dashboard_stats(
    gems,
    sessions,
    knowledge_count
):

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon">🧩</div>
                <div class="stat-label">我的 GEM</div>
                <div class="stat-value">{len(gems)}</div>
                <div class="stat-description">
                    雲端 AI GEM
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon">📚</div>
                <div class="stat-label">Knowledge</div>
                <div class="stat-value">{knowledge_count}</div>
                <div class="stat-description">
                    知識資料
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-label">聊天紀錄</div>
                <div class="stat-value">{len(sessions)}</div>
                <div class="stat-description">
                    AI 對話 Session
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# 28. GEM Card
# =========================================================

def show_gem_card(
    gem,
    key_prefix="gem"
):

    gem_id = gem.get("id")

    name = gem.get(
        "name",
        "未命名 GEM"
    )

    role = gem.get(
        "role",
        ""
    )

    description = (
        role[:150]
        if role
        else "尚未設定 GEM 描述。"
    )

    st.markdown(
        f"""
        <div class="gem-card">

            <div class="gem-card-icon">
                🧩
            </div>

            <div class="gem-card-title">
                {html.escape(str(name))}
            </div>

            <div class="gem-card-description">
                {html.escape(str(description))}
            </div>

            <div class="gem-card-meta">
                🤖 {html.escape(
                    str(st.session_state.selected_model)
                )}
                &nbsp;&nbsp;•&nbsp;&nbsp;
                ☁️ Cloud GEM
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "📂 開啟 GEM",
        key=f"{key_prefix}_open_{gem_id}",
        use_container_width=True
    ):

        st.session_state.selected_gem_id = gem_id

        st.session_state.page = "GEM 詳細"

        st.rerun()


# =========================================================
# 29. 首頁 Dashboard
# =========================================================

def show_home():

    # =====================================================
    # Hero
    # =====================================================

    st.markdown(
        """
        <div class="dashboard-hero">

            <div class="dashboard-hero-title">
                ☁️ GEM Builder Cloud
            </div>

            <div class="dashboard-hero-subtitle">
                你的個人 AI GEM 工作平台
                <br>
                建立、管理、測試、優化你的 AI GEM。
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    show_model_status()


    # =====================================================
    # 取得資料
    # =====================================================

    gems = get_gems()

    sessions = get_chat_sessions()

    knowledge_count = 0

    for gem in gems:

        knowledge_count += len(
            get_knowledge(
                gem.get("id")
            )
        )


    # =====================================================
    # 統計
    # =====================================================

    st.markdown(
        """
        <div class="dashboard-section-title">
            📊 工作平台概況
        </div>
        """,
        unsafe_allow_html=True
    )

    show_dashboard_stats(
        gems,
        sessions,
        knowledge_count
    )


    st.write("")


    # =====================================================
    # 快速操作
    # =====================================================

    st.markdown(
        """
        <div class="dashboard-section-title">
            ⚡ 快速操作
        </div>
        """,
        unsafe_allow_html=True
    )


    col1, col2 = st.columns(2)


    with col1:

        if st.button(
            "➕ 建立 GEM",
            type="primary",
            use_container_width=True
        ):

            st.session_state.page = "建立 GEM"

            st.rerun()


    with col2:

        if st.button(
            "🤖 AI 自動生成 GEM",
            use_container_width=True
        ):

            st.session_state.page = "Gemini 自動生成"

            st.rerun()


    col3, col4 = st.columns(2)


    with col3:

        if st.button(
            "🧩 開啟 GEM 工作區",
            use_container_width=True
        ):

            st.session_state.page = "GEM 工作區"

            st.rerun()


    with col4:

        if st.button(
            "💬 開始 GEM 對話",
            use_container_width=True
        ):

            st.session_state.page = "GEM 對話"

            st.rerun()


    st.divider()


    # =====================================================
    # 最近 GEM
    # =====================================================

    st.markdown(
        """
        <div class="dashboard-section-title">
            🧩 最近使用的 GEM
        </div>
        """,
        unsafe_allow_html=True
    )


    if not gems:

        st.info(
            "目前還沒有 GEM。建立你的第一個 GEM 開始使用吧！"
        )

        if st.button(
            "✨ 建立第一個 GEM",
            type="primary",
            use_container_width=True
        ):

            st.session_state.page = "建立 GEM"

            st.rerun()

        return


    recent_gems = gems[:6]


    # =====================================================
    # 電腦：三欄
    # 手機：Streamlit 自動堆疊
    # =====================================================

    for row_start in range(
        0,
        len(recent_gems),
        3
    ):

        row = recent_gems[
            row_start:row_start + 3
        ]

        columns = st.columns(
            len(row)
        )

        for index, gem in enumerate(row):

            with columns[index]:

                show_gem_card(
                    gem,
                    key_prefix=f"dashboard_{row_start}_{index}"
                )


    st.divider()


    # =====================================================
    # 更多 GEM
    # =====================================================

    if len(gems) > 6:

        st.caption(
            f"目前共有 {len(gems)} 個 GEM"
        )

        if st.button(
            "查看全部 GEM →",
            use_container_width=True
        ):

            st.session_state.page = "GEM 工作區"

            st.rerun()


# =========================================================
# 30. 建立 GEM
# =========================================================

def show_create_gem():

    st.title("➕ 建立 GEM")

    name = st.text_input(
        "GEM 名稱"
    )

    role = st.text_area(
        "Role",
        height=220
    )

    workflow = st.text_area(
        "Workflow & Rules",
        height=320
    )

    greeting = st.text_area(
        "Greeting",
        height=180
    )

    if st.button(
        "💾 建立 GEM",
        type="primary",
        use_container_width=True
    ):

        if not name.strip():

            st.warning(
                "請輸入 GEM 名稱。"
            )

            return

        result = create_gem(
            name,
            role,
            workflow,
            greeting
        )

        if result:

            st.success(
                "GEM 建立成功！"
            )

            st.session_state.selected_gem_id = (
                result[0]["id"]
            )

            st.session_state.page = "GEM 詳細"

            st.rerun()


# =========================================================
# 31. GEM 工作區
# =========================================================

def show_workspace():

    st.title("🧩 GEM 工作區")

    gems = get_gems()

    if not gems:

        st.info(
            "目前沒有 GEM。"
        )

        return

    search = st.text_input(
        "🔎 搜尋 GEM"
    )

    if search.strip():

        gems = [

            gem for gem in gems

            if search.lower()
            in gem.get(
                "name",
                ""
            ).lower()

        ]

    st.caption(
        f"找到 {len(gems)} 個 GEM"
    )


    for index, gem in enumerate(gems):

        gem_id = gem.get("id")

        with st.container(
            border=True
        ):

            st.markdown(
                f"### 🧩 {gem.get('name')}"
            )

            role = gem.get(
                "role",
                ""
            )

            if role:

                st.write(
                    role[:200]
                )

            col1, col2 = st.columns(2)


            with col1:

                if st.button(
                    "📂 開啟",
                    key=f"open_{gem_id}",
                    use_container_width=True
                ):

                    st.session_state.selected_gem_id = (
                        gem_id
                    )

                    st.session_state.page = (
                        "GEM 詳細"
                    )

                    st.rerun()


            with col2:

                if st.button(
                    "💬 對話",
                    key=f"chat_{gem_id}",
                    use_container_width=True
                ):

                    st.session_state.selected_gem_id = (
                        gem_id
                    )

                    st.session_state.page = (
                        "GEM 對話"
                    )

                    st.rerun()


# =========================================================
# 32. GEM 詳細
# =========================================================

def show_gem_detail():

    gem_id = (
        st.session_state.selected_gem_id
    )

    if not gem_id:

        st.warning(
            "尚未選擇 GEM。"
        )

        return

    gem = get_gem(gem_id)

    if not gem:

        st.error(
            "找不到 GEM。"
        )

        return

    st.title(
        f"🧩 {gem.get('name')}"
    )

    show_model_status()


    tabs = st.tabs(
        [
            "📋 內容",
            "✏️ 編輯",
            "📚 Knowledge",
            "✨ AI 優化",
            "🧪 測試",
            "💬 對話"
        ]
    )


    # =====================================================
    # TAB 內容
    # =====================================================

    with tabs[0]:

        st.subheader(
            "Role"
        )

        st.text_area(
            "Role",
            value=gem.get(
                "role",
                ""
            ),
            height=220,
            disabled=True,
            key=f"view_role_{gem_id}"
        )

        st.subheader(
            "Workflow & Rules"
        )

        st.text_area(
            "Workflow",
            value=gem.get(
                "workflow",
                ""
            ),
            height=300,
            disabled=True,
            key=f"view_workflow_{gem_id}"
        )

        st.subheader(
            "Greeting"
        )

        st.text_area(
            "Greeting",
            value=gem.get(
                "greeting",
                ""
            ),
            height=180,
            disabled=True,
            key=f"view_greeting_{gem_id}"
        )

        st.divider()


        col1, col2 = st.columns(2)


        with col1:

            st.download_button(
                "📄 匯出 TXT",
                data=gem_to_txt(gem),
                file_name=f"{gem.get('name')}.txt",
                use_container_width=True
            )


        with col2:

            st.download_button(
                "📋 匯出 JSON",
                data=gem_to_json(gem),
                file_name=f"{gem.get('name')}.json",
                use_container_width=True
            )


        st.divider()


        if st.button(
            "📋 一鍵複製 GEM",
            use_container_width=True
        ):

            result = create_gem(

                gem.get("name")
                + " - 複製版",

                gem.get(
                    "role",
                    ""
                ),

                gem.get(
                    "workflow",
                    ""
                ),

                gem.get(
                    "greeting",
                    ""
                )

            )

            if result:

                new_id = result[0]["id"]

                knowledge_list = (
                    get_knowledge(gem_id)
                )

                for item in knowledge_list:

                    create_knowledge(

                        new_id,

                        item.get(
                            "title",
                            ""
                        ),

                        item.get(
                            "content",
                            ""
                        )

                    )

                st.success(
                    "GEM 已完整複製！"
                )

                st.session_state.selected_gem_id = (
                    new_id
                )

                st.rerun()


    # =====================================================
    # TAB 編輯
    # =====================================================

    with tabs[1]:

        name = st.text_input(
            "GEM 名稱",
            value=gem.get(
                "name",
                ""
            ),
            key=f"name_{gem_id}"
        )

        role = st.text_area(
            "Role",
            value=gem.get(
                "role",
                ""
            ),
            height=220,
            key=f"role_{gem_id}"
        )

        workflow = st.text_area(
            "Workflow & Rules",
            value=gem.get(
                "workflow",
                ""
            ),
            height=300,
            key=f"workflow_{gem_id}"
        )

        greeting = st.text_area(
            "Greeting",
            value=gem.get(
                "greeting",
                ""
            ),
            height=180,
            key=f"greeting_{gem_id}"
        )

        if st.button(
            "💾 儲存修改",
            type="primary",
            use_container_width=True
        ):

            result = update_gem(
                gem_id,
                name,
                role,
                workflow,
                greeting
            )

            if result:

                st.success(
                    "更新成功！"
                )

                st.rerun()


    # =====================================================
    # TAB Knowledge
    # =====================================================

    with tabs[2]:

        knowledge_list = (
            get_knowledge(gem_id)
        )

        st.info(
            f"目前共有 {len(knowledge_list)} 筆 Knowledge"
        )


        with st.expander(
            "➕ 新增 Knowledge"
        ):

            title = st.text_input(
                "Knowledge 標題",
                key=f"k_title_{gem_id}"
            )

            content = st.text_area(
                "Knowledge 內容",
                height=250,
                key=f"k_content_{gem_id}"
            )

            if st.button(
                "💾 新增 Knowledge",
                use_container_width=True
            ):

                if title and content:

                    create_knowledge(
                        gem_id,
                        title,
                        content
                    )

                    st.success(
                        "新增成功！"
                    )

                    st.rerun()


        for item in knowledge_list:

            knowledge_id = item.get(
                "id"
            )

            with st.container(
                border=True
            ):

                st.subheader(
                    item.get(
                        "title"
                    )
                )

                st.write(
                    item.get(
                        "content"
                    )
                )


                with st.expander(
                    "✏️ 編輯"
                ):

                    new_title = st.text_input(
                        "標題",
                        value=item.get(
                            "title"
                        ),
                        key=f"edit_title_{knowledge_id}"
                    )

                    new_content = st.text_area(
                        "內容",
                        value=item.get(
                            "content"
                        ),
                        height=220,
                        key=f"edit_content_{knowledge_id}"
                    )

                    if st.button(
                        "💾 儲存",
                        key=f"save_k_{knowledge_id}",
                        use_container_width=True
                    ):

                        update_knowledge(
                            knowledge_id,
                            new_title,
                            new_content
                        )

                        st.success(
                            "更新成功！"
                        )

                        st.rerun()


                if st.button(
                    "🗑️ 刪除",
                    key=f"delete_k_{knowledge_id}",
                    use_container_width=True
                ):

                    delete_knowledge(
                        knowledge_id
                    )

                    st.rerun()


    # =====================================================
    # TAB AI 優化
    # =====================================================

    with tabs[3]:

        st.subheader(
            "✨ AI Prompt 智慧優化"
        )

        show_model_status()


        if st.button(
            "✨ 開始 AI 優化",
            type="primary",
            use_container_width=True
        ):

            prompt = f"""
你是一位專業的 AI Prompt 工程師。

請優化以下 GEM。

名稱：
{gem.get("name", "")}

Role：
{gem.get("role", "")}

Workflow：
{gem.get("workflow", "")}

Greeting：
{gem.get("greeting", "")}

要求：

1. 保留核心目的。
2. 強化角色定位。
3. 優化工作流程。
4. 增加必要規則。
5. 使用繁體中文。
6. 不要加入無關功能。

請輸出：

GEM 名稱：

Role：

Workflow & Rules：

Greeting：
"""

            with st.spinner(
                "AI 正在分析 GEM..."
            ):

                st.session_state.optimizer_result = (
                    ask_gemini(prompt)
                )


        if st.session_state.optimizer_result:

            st.text_area(
                "AI 優化結果",
                value=st.session_state.optimizer_result,
                height=600
            )


    # =====================================================
    # TAB 測試
    # =====================================================

    with tabs[4]:

        st.subheader(
            "🧪 GEM 測試"
        )

        show_model_status()

        user_message = st.text_area(
            "測試訊息",
            height=180
        )

        if st.button(
            "🤖 執行測試",
            type="primary",
            use_container_width=True
        ):

            prompt = f"""
你現在扮演以下 GEM。

GEM 名稱：
{gem.get("name", "")}

Role：
{gem.get("role", "")}

Workflow：
{gem.get("workflow", "")}

Greeting：
{gem.get("greeting", "")}

請嚴格依照設定回答。

使用者：

{user_message}
"""

            with st.spinner(
                "GEM 思考中..."
            ):

                result = ask_gemini(
                    prompt
                )

            st.subheader(
                "🤖 GEM 回覆"
            )

            st.write(
                result
            )


    # =====================================================
    # TAB 對話
    # =====================================================

    with tabs[5]:

        st.subheader(
            "💬 GEM 對話"
        )

        show_model_status()


        if st.button(
            "🚀 開始新對話",
            use_container_width=True
        ):

            result = create_chat_session(

                gem_id,

                f"{gem.get('name')} 對話"

            )

            if result:

                st.session_state.selected_chat_session_id = (
                    result[0]["id"]
                )

                st.rerun()


        sessions = (
            get_chat_sessions_by_gem(
                gem_id
            )
        )


        if sessions:

            session_options = {

                session.get("id"):
                session.get(
                    "title",
                    "未命名對話"
                )

                for session in sessions

            }


            if (
                st.session_state.selected_chat_session_id
                not in session_options
            ):

                st.session_state.selected_chat_session_id = (
                    sessions[0]["id"]
                )


            selected_session = st.selectbox(

                "選擇聊天紀錄",

                options=list(
                    session_options.keys()
                ),

                format_func=lambda x:
                session_options[x],

                key=f"session_select_{gem_id}"

            )


            st.session_state.selected_chat_session_id = (
                selected_session
            )


            messages = get_chat_messages(
                selected_session
            )


            for message in messages:

                role = message.get(
                    "role"
                )

                content = message.get(
                    "content"
                )

                if role == "user":

                    with st.chat_message(
                        "user"
                    ):

                        st.write(
                            content
                        )

                else:

                    with st.chat_message(
                        "assistant"
                    ):

                        st.write(
                            content
                        )


            user_input = st.chat_input(
                "輸入訊息..."
            )


            if user_input:

                create_chat_message(
                    selected_session,
                    "user",
                    user_input
                )


                history_text = ""

                messages = get_chat_messages(
                    selected_session
                )


                for message in messages[-12:]:

                    history_text += (
                        f"\n{message.get('role')}: "
                        f"{message.get('content')}"
                    )


                knowledge_list = (
                    get_knowledge(
                        gem_id
                    )
                )


                knowledge_text = ""


                for item in knowledge_list:

                    knowledge_text += f"""

Knowledge：
{item.get("title", "")}

{item.get("content", "")}
"""


                prompt = f"""
你現在是一個 GEM。

名稱：
{gem.get("name", "")}

Role：
{gem.get("role", "")}

Workflow：
{gem.get("workflow", "")}

Greeting：
{gem.get("greeting", "")}

{knowledge_text}

以下是最近對話紀錄：

{history_text}

請根據 GEM 設定回答最新使用者訊息。
使用繁體中文。
"""


                with st.spinner(
                    "AI 回覆中..."
                ):

                    ai_response = ask_gemini(
                        prompt
                    )


                create_chat_message(
                    selected_session,
                    "assistant",
                    ai_response
                )

                st.rerun()


        else:

            st.info(
                "尚未建立聊天，請點擊「開始新對話」。"
            )


# =========================================================
# 33. 獨立 GEM 對話
# =========================================================

def show_chat():

    st.title(
        "💬 GEM 對話中心"
    )

    show_model_status()

    gems = get_gems()

    if not gems:

        st.info(
            "請先建立 GEM。"
        )

        return


    gem_options = {

        gem.get("id"):
        gem.get("name")

        for gem in gems

    }


    default_index = 0


    if st.session_state.selected_gem_id in gem_options:

        default_index = list(
            gem_options.keys()
        ).index(
            st.session_state.selected_gem_id
        )


    selected_gem_id = st.selectbox(

        "選擇 GEM",

        options=list(
            gem_options.keys()
        ),

        index=default_index,

        format_func=lambda x:
        gem_options[x]

    )


    st.session_state.selected_gem_id = (
        selected_gem_id
    )


    gem = get_gem(
        selected_gem_id
    )


    st.subheader(
        f"🧩 {gem.get('name')}"
    )


    if st.button(
        "➕ 建立新聊天",
        type="primary",
        use_container_width=True
    ):

        title = (
            f"{gem.get('name')} - "
            f"{datetime.now().strftime('%Y/%m/%d %H:%M')}"
        )


        result = create_chat_session(
            selected_gem_id,
            title
        )


        if result:

            st.session_state.selected_chat_session_id = (
                result[0]["id"]
            )

            st.rerun()


    sessions = get_chat_sessions_by_gem(
        selected_gem_id
    )


    if not sessions:

        st.info(
            "請先建立新聊天。"
        )

        return


    session_options = {

        session.get("id"):
        session.get(
            "title",
            "未命名聊天"
        )

        for session in sessions

    }


    if (
        st.session_state.selected_chat_session_id
        not in session_options
    ):

        st.session_state.selected_chat_session_id = (
            sessions[0]["id"]
        )


    session_id = st.selectbox(

        "目前聊天",

        options=list(
            session_options.keys()
        ),

        format_func=lambda x:
        session_options[x]

    )


    st.session_state.selected_chat_session_id = (
        session_id
    )


    messages = get_chat_messages(
        session_id
    )


    for message in messages:

        with st.chat_message(

            "user"
            if message.get("role") == "user"
            else "assistant"

        ):

            st.write(
                message.get("content")
            )


    user_input = st.chat_input(
        "輸入訊息..."
    )


    if user_input:

        create_chat_message(
            session_id,
            "user",
            user_input
        )


        messages = get_chat_messages(
            session_id
        )


        history = ""


        for message in messages[-12:]:

            history += (
                f"\n{message.get('role')}: "
                f"{message.get('content')}"
            )


        knowledge_list = get_knowledge(
            selected_gem_id
        )


        knowledge_text = ""


        for item in knowledge_list:

            knowledge_text += f"""

{item.get("title", "")}

{item.get("content", "")}
"""


        prompt = f"""
你現在是：

{gem.get("name", "")}

Role：
{gem.get("role", "")}

Workflow：
{gem.get("workflow", "")}

Greeting：
{gem.get("greeting", "")}

Knowledge：
{knowledge_text}

聊天紀錄：
{history}

請回答最新使用者訊息。
請使用繁體中文。
"""


        with st.spinner(
            "AI 回覆中..."
        ):

            response = ask_gemini(
                prompt
            )


        create_chat_message(
            session_id,
            "assistant",
            response
        )

        st.rerun()


# =========================================================
# 34. 聊天紀錄中心
# =========================================================

def show_chat_history():

    st.title(
        "🕘 完整聊天紀錄中心"
    )

    sessions = get_chat_sessions()


    if not sessions:

        st.info(
            "目前沒有聊天紀錄。"
        )

        return


    st.caption(
        f"共有 {len(sessions)} 個聊天紀錄"
    )


    for session in sessions:

        session_id = session.get(
            "id"
        )

        gem_id = session.get(
            "gem_id"
        )

        gem = get_gem(
            gem_id
        )


        gem_name = (
            gem.get("name")
            if gem
            else "未知 GEM"
        )


        with st.container(
            border=True
        ):

            st.subheader(
                session.get(
                    "title",
                    "未命名聊天"
                )
            )

            st.caption(
                f"🧩 {gem_name}"
            )

            st.caption(
                f"建立時間：{session.get('created_at', '')}"
            )


            col1, col2 = st.columns(2)


            with col1:

                if st.button(

                    "💬 開啟",

                    key=f"history_open_{session_id}",

                    use_container_width=True

                ):

                    st.session_state.selected_gem_id = (
                        gem_id
                    )

                    st.session_state.selected_chat_session_id = (
                        session_id
                    )

                    st.session_state.page = (
                        "GEM 對話"
                    )

                    st.rerun()


            with col2:

                if st.button(

                    "🗑️ 刪除",

                    key=f"history_delete_{session_id}",

                    use_container_width=True

                ):

                    delete_chat_session(
                        session_id
                    )

                    st.success(
                        "聊天紀錄已刪除。"
                    )

                    st.rerun()


# =========================================================
# 35. Gemini 自動生成
# =========================================================

def show_gemini_generator():

    st.title(
        "🤖 Gemini GEM 自動生成器"
    )

    show_model_status()


    gem_purpose = st.text_area(
        "你想建立什麼 GEM？",
        height=180
    )


    target_user = st.text_input(
        "主要使用者"
    )


    special_requirements = st.text_area(
        "特殊要求",
        height=150
    )


    if st.button(
        "✨ 生成 GEM",
        type="primary",
        use_container_width=True
    ):

        if not gem_purpose.strip():

            st.warning(
                "請輸入 GEM 需求。"
            )

            return


        prompt = f"""
你是一位專業 AI GEM Prompt 設計專家。

請建立完整 GEM。

GEM 目的：
{gem_purpose}

主要使用者：
{target_user}

特殊要求：
{special_requirements}

請輸出：

GEM 名稱：

Role：

Workflow & Rules：

Greeting：

使用繁體中文。

不要解釋。
直接輸出完整 GEM。
"""


        with st.spinner(
            "Gemini 正在生成..."
        ):

            st.session_state.gemini_result = (
                ask_gemini(prompt)
            )


    if st.session_state.gemini_result:

        st.divider()

        st.text_area(
            "Gemini 生成結果",
            value=st.session_state.gemini_result,
            height=650
        )


# =========================================================
# 36. GEM 匯入
# =========================================================

def show_import():

    st.title(
        "📥 GEM 匯入"
    )


    uploaded_file = st.file_uploader(
        "選擇 JSON 或 TXT",
        type=["json", "txt"]
    )


    if uploaded_file is None:

        return


    content = uploaded_file.read()


    name = "匯入 GEM"

    role = ""

    workflow = ""

    greeting = ""


    if uploaded_file.name.lower().endswith(
        ".json"
    ):

        try:

            data = json.loads(
                content.decode(
                    "utf-8"
                )
            )


            name = data.get(
                "name",
                name
            )

            role = data.get(
                "role",
                ""
            )

            workflow = data.get(
                "workflow",
                ""
            )

            greeting = data.get(
                "greeting",
                ""
            )


        except Exception as e:

            st.error(
                f"JSON 錯誤：{e}"
            )

            return


    else:

        role = content.decode(
            "utf-8",
            errors="ignore"
        )


    st.text_input(
        "GEM 名稱",
        value=name,
        key="import_name"
    )


    if st.button(
        "☁️ 匯入 GEM",
        type="primary",
        use_container_width=True
    ):

        result = create_gem(

            st.session_state.import_name,

            role,

            workflow,

            greeting

        )


        if result:

            st.success(
                "匯入成功！"
            )


            st.session_state.selected_gem_id = (
                result[0]["id"]
            )


            st.session_state.page = (
                "GEM 詳細"
            )


            st.rerun()


# =========================================================
# 37. GEM 模板
# =========================================================

def show_templates():

    st.title(
        "📚 GEM 模板"
    )


    templates = {

        "職涯教練 GEM": {

            "role": """
你是一位專業職涯教練。

協助使用者探索興趣、能力、價值觀與職涯方向。
不要直接替使用者做決定。
""",

            "workflow": """
1. 了解目前困擾。
2. 使用開放式問題探索。
3. 整理使用者資訊。
4. 找出可能方向。
5. 協助形成下一步。
""",

            "greeting": """
你好，我是你的 AI 職涯教練。

我們可以一起探索你的下一步。
"""
        },


        "SFBT 教練 GEM": {

            "role": """
你是一位熟悉焦點解決短期治療精神的 AI 引導者。

協助使用者看見資源、例外與可能性。
""",

            "workflow": """
1. 了解問題。
2. 探索期待未來。
3. 尋找例外經驗。
4. 發現資源。
5. 找到小步驟。
""",

            "greeting": """
你好。

我們可以一起看看，
事情往更好的方向發展時，
你希望生活有什麼不同？
"""
        },


        "AI 陪聊 GEM": {

            "role": """
你是一位溫暖、有同理心的 AI 陪聊者。

主要任務是理解與陪伴，
而不是急著解決問題。
""",

            "workflow": """
1. 理解使用者。
2. 回應情緒。
3. 適度提問。
4. 不過度追問。
5. 需要時提供建議。
""",

            "greeting": """
嗨，我在這裡。

今天想聊些什麼？
"""
        }

    }


    for name, template in templates.items():

        with st.container(
            border=True
        ):

            st.subheader(
                name
            )

            st.write(
                template["role"]
            )


            if st.button(

                f"➕ 使用 {name}",

                key=f"template_{name}",

                use_container_width=True

            ):

                result = create_gem(

                    name,

                    template["role"],

                    template["workflow"],

                    template["greeting"]

                )


                if result:

                    st.success(
                        "建立成功！"
                    )


                    st.session_state.selected_gem_id = (
                        result[0]["id"]
                    )


                    st.session_state.page = (
                        "GEM 詳細"
                    )


                    st.rerun()


# =========================================================
# 38. 回到頁首
# =========================================================

def show_scroll_top():

    st.markdown(
        """
        <div class="scroll-top-space"></div>
        """,
        unsafe_allow_html=True
    )


    if st.button(
        "⬆️ 回到頁首",
        use_container_width=True,
        key="scroll_to_top"
    ):

        st.components.v1.html(
            """
            <script>
            window.parent.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            </script>
            """,
            height=0
        )


# =========================================================
# 39. Sidebar
# =========================================================

with st.sidebar:

    st.title(
        "☁️ GEM Builder Cloud"
    )


    st.caption(
        "Day 24-A｜Cloud 2.0"
    )


    st.divider()


    # =====================================================
    # Gemini 模型
    # =====================================================

    st.subheader(
        "🤖 Gemini 模型"
    )


    models = (
        st.session_state.available_models
    )


    if models:

        current_index = 0


        if (
            st.session_state.selected_model
            in models
        ):

            current_index = models.index(
                st.session_state.selected_model
            )


        selected_model = st.selectbox(

            "選擇模型",

            options=models,

            index=current_index,

            key="global_model_selector"

        )


        if (
            selected_model
            != st.session_state.selected_model
        ):

            st.session_state.selected_model = (
                selected_model
            )

            st.rerun()


        st.success(
            f"目前模型：\n"
            f"{st.session_state.selected_model}"
        )


    else:

        st.error(
            "沒有找到可用模型。"
        )


    # =====================================================
    # 重新偵測
    # =====================================================

    if st.button(
        "🔄 重新偵測模型",
        use_container_width=True
    ):

        get_available_models.clear()


        st.session_state.available_models = (
            get_available_models()
        )


        if (
            st.session_state.selected_model
            not in st.session_state.available_models
        ):

            st.session_state.selected_model = (
                st.session_state.available_models[0]
            )


        st.rerun()


    st.divider()


    # =====================================================
    # 導覽
    # =====================================================

    st.subheader(
        "🧭 功能"
    )


    if st.button(
        "🏠 Dashboard",
        use_container_width=True
    ):

        st.session_state.page = (
            "首頁"
        )

        st.rerun()


    if st.button(
        "➕ 建立 GEM",
        use_container_width=True
    ):

        st.session_state.page = (
            "建立 GEM"
        )

        st.rerun()


    if st.button(
        "🧩 GEM 工作區",
        use_container_width=True
    ):

        st.session_state.page = (
            "GEM 工作區"
        )

        st.rerun()


    if st.button(
        "💬 GEM 對話",
        use_container_width=True
    ):

        st.session_state.page = (
            "GEM 對話"
        )

        st.rerun()


    if st.button(
        "🕘 聊天紀錄中心",
        use_container_width=True
    ):

        st.session_state.page = (
            "聊天紀錄"
        )

        st.rerun()


    if st.button(
        "🤖 AI 自動生成",
        use_container_width=True
    ):

        st.session_state.page = (
            "Gemini 自動生成"
        )

        st.rerun()


    if st.button(
        "📥 GEM 匯入",
        use_container_width=True
    ):

        st.session_state.page = (
            "GEM 匯入"
        )

        st.rerun()


    if st.button(
        "📚 GEM 模板",
        use_container_width=True
    ):

        st.session_state.page = (
            "GEM 模板"
        )

        st.rerun()


    st.divider()


    st.caption(
        "☁️ Supabase Cloud"
    )


    st.caption(
        f"🤖 {st.session_state.selected_model}"
    )


    st.caption(
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )


# =========================================================
# 40. 頁面路由
# =========================================================

if st.session_state.page == "首頁":

    show_home()


elif st.session_state.page == "建立 GEM":

    show_create_gem()


elif st.session_state.page == "GEM 工作區":

    show_workspace()


elif st.session_state.page == "GEM 詳細":

    show_gem_detail()


elif st.session_state.page == "GEM 對話":

    show_chat()


elif st.session_state.page == "聊天紀錄":

    show_chat_history()


elif st.session_state.page == "Gemini 自動生成":

    show_gemini_generator()


elif st.session_state.page == "GEM 匯入":

    show_import()


elif st.session_state.page == "GEM 模板":

    show_templates()


# =========================================================
# 41. 頁面底部
# =========================================================

st.divider()

show_scroll_top()

st.caption(
    f"☁️ GEM Builder Cloud ｜ "
    f"目前模型："
    f"{st.session_state.selected_model}"
)

st.caption(
    "Day 24-A｜Cloud 2.0"
)
