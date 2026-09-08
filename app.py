````python
import streamlit as st
import json
import os
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="GEM Builder Cloud",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# SUPABASE
# =========================================================

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

# =========================================================
# GEMINI
# =========================================================

try:
    from google import genai
except Exception:
    genai = None


# =========================================================
# SESSION STATE
# =========================================================

DEFAULT_STATE = {
    "user": None,
    "gems": [],
    "selected_gem": None,
    "optimized_result": None,
    "optimizer_open": False,
    "model_name": "",
    "gemini_client": None,
    "page": "home",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# ENV / SECRETS
# =========================================================

def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ---------- Global ---------- */

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1400px;
    }

    h1, h2, h3 {
        letter-spacing: -0.3px;
    }

    /* ---------- Cards ---------- */

    .gem-card {
        padding: 18px;
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 16px;
        margin-bottom: 12px;
        background: rgba(128,128,128,0.04);
    }

    .gem-title {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .gem-version {
        font-size: 13px;
        opacity: 0.7;
    }

    .optimizer-box {
        padding: 20px;
        border-radius: 18px;
        border: 2px solid rgba(80,120,255,0.35);
        background: rgba(80,120,255,0.05);
        margin-top: 15px;
        margin-bottom: 20px;
    }

    .success-box {
        padding: 16px;
        border-radius: 14px;
        border: 1px solid rgba(0,160,100,0.35);
        background: rgba(0,160,100,0.05);
    }

    /* ---------- Mobile ---------- */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 1rem;
        }

        h1 {
            font-size: 1.8rem !important;
        }

        h2 {
            font-size: 1.45rem !important;
        }

        h3 {
            font-size: 1.2rem !important;
        }

        div.stButton > button {
            min-height: 44px;
            border-radius: 10px;
        }

        textarea {
            font-size: 16px !important;
        }

    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SUPABASE CLIENT
# =========================================================

@st.cache_resource
def get_supabase():

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    if create_client is None:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception:
        return None


supabase = get_supabase()


# =========================================================
# GEMINI CLIENT
# =========================================================

def create_gemini_client():

    if not GEMINI_API_KEY:
        return None

    if genai is None:
        return None

    try:
        return genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception:
        return None


if st.session_state.gemini_client is None:
    st.session_state.gemini_client = create_gemini_client()


# =========================================================
# AVAILABLE GEMINI MODELS
# =========================================================

MODEL_OPTIONS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


# =========================================================
# SESSION USER
# =========================================================

def get_current_user():

    if supabase is None:
        return None

    try:
        response = supabase.auth.get_user()

        if response and response.user:
            return response.user

    except Exception:
        pass

    return None


# =========================================================
# LOGIN
# =========================================================

def login_user(email, password):

    if supabase is None:
        return False, "Supabase 尚未設定。"

    try:

        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password
            }
        )

        if response.user:
            st.session_state.user = response.user
            return True, "登入成功"

        return False, "登入失敗"

    except Exception as e:
        return False, str(e)


# =========================================================
# REGISTER
# =========================================================

def register_user(email, password):

    if supabase is None:
        return False, "Supabase 尚未設定。"

    try:

        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password
            }
        )

        if response.user:
            return True, "註冊成功，請依照 Email 驗證。"

        return False, "註冊失敗"

    except Exception as e:
        return False, str(e)


# =========================================================
# LOGOUT
# =========================================================

def logout():

    if supabase:

        try:
            supabase.auth.sign_out()
        except Exception:
            pass

    st.session_state.user = None
    st.session_state.gems = []
    st.session_state.selected_gem = None

    st.rerun()


# =========================================================
# LOAD GEMS
# =========================================================

def load_gems():

    user = st.session_state.user

    if not user or supabase is None:
        return []

    try:

        result = (
            supabase
            .table("gems")
            .select("*")
            .eq("user_id", user.id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data or []

    except Exception as e:

        st.error(f"讀取 GEM 失敗：{e}")
        return []


# =========================================================
# SAVE GEM
# =========================================================

def insert_gem(data):

    user = st.session_state.user

    if not user or supabase is None:
        return None

    payload = dict(data)

    payload["user_id"] = user.id

    try:

        result = (
            supabase
            .table("gems")
            .insert(payload)
            .execute()
        )

        if result.data:
            return result.data[0]

    except Exception as e:

        st.error(f"新增 GEM 失敗：{e}")

    return None


# =========================================================
# UPDATE GEM
# =========================================================

def update_gem(gem_id, data):

    user = st.session_state.user

    if not user or supabase is None:
        return None

    payload = dict(data)

    try:

        result = (
            supabase
            .table("gems")
            .update(payload)
            .eq("id", gem_id)
            .eq("user_id", user.id)
            .execute()
        )

        if result.data:
            return result.data[0]

    except Exception as e:

        st.error(f"更新 GEM 失敗：{e}")

    return None


# =========================================================
# DELETE GEM
# =========================================================

def delete_gem(gem_id):

    user = st.session_state.user

    if not user or supabase is None:
        return False

    try:

        (
            supabase
            .table("gems")
            .delete()
            .eq("id", gem_id)
            .eq("user_id", user.id)
            .execute()
        )

        return True

    except Exception as e:

        st.error(f"刪除 GEM 失敗：{e}")
        return False


# =========================================================
# SAFE VALUE
# =========================================================

def safe_value(gem, key, default=""):

    value = gem.get(key)

    if value is None:
        return default

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )

    if isinstance(value, list):
        return "\n".join(
            str(x) for x in value
        )

    return str(value)


# =========================================================
# GEMINI CALL
# =========================================================

def call_gemini(prompt, model):

    client = st.session_state.gemini_client

    if client is None:
        return None, "Gemini API 尚未設定。"

    try:

        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        if response and response.text:
            return response.text.strip(), None

        return None, "Gemini 沒有返回內容。"

    except Exception as e:

        error_text = str(e)

        if "503" in error_text or "UNAVAILABLE" in error_text:

            return (
                None,
                "Gemini 目前服務忙碌（503 UNAVAILABLE），請稍後再試。"
            )

        if "429" in error_text:

            return (
                None,
                "Gemini API 使用量已達限制，請稍後再試。"
            )

        return None, error_text


# =========================================================
# EXTRACT JSON
# =========================================================

def extract_json(text):

    if not text:
        return None

    text = text.strip()

    if text.startswith("```"):

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    try:
        return json.loads(text)

    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        try:
            return json.loads(
                text[start:end + 1]
            )
        except Exception:
            pass

    return None


# =========================================================
# DAY 32 - GEM OPTIMIZER
# =========================================================

def optimize_gem(gem, model):

    name = safe_value(gem, "name")
    description = safe_value(gem, "description")
    prompt = safe_value(gem, "prompt")
    knowledge = safe_value(gem, "knowledge")
    version = safe_value(gem, "version", "1.0")

    optimizer_prompt = f"""
你是一位專業的 GEM Prompt Architect。

你的任務是：
「完整優化以下 GEM」。

請不要只是修改文字，而是要從「AI 實際執行效果」的角度，
重新檢查並強化這個 GEM。

【目前 GEM】

名稱：
{name}

說明：
{description}

版本：
{version}

原始 Prompt：
{prompt}

Knowledge：
{knowledge}

━━━━━━━━━━━━━━━━━━

請從以下 8 個方向進行優化：

1. 角色定位
2. 核心任務
3. 使用者需求理解
4. 執行步驟
5. 回應規則
6. 輸出格式
7. 邊界與限制
8. 品質控制

特別檢查：

- 是否有模糊指令
- 是否存在互相衝突的指令
- AI 是否容易誤解角色
- AI 是否知道每一步要做什麼
- 是否缺少輸出格式
- 是否缺少必要的判斷條件
- 是否缺少錯誤處理
- 是否缺少使用者資訊不足時的處理方式
- 是否可以讓 AI 更穩定地重複產生高品質結果

請保留原本 GEM 的核心目的，
不要任意改變 GEM 的用途。

請輸出 JSON。

格式必須完全如下：

{{
    "optimized_name": "",
    "optimized_description": "",
    "optimized_prompt": "",
    "optimization_summary": "",
    "improvements": [
        "",
        "",
        ""
    ],
    "quality_score_before": 0,
    "quality_score_after": 0
}}

quality_score_before 和 quality_score_after
請使用 0～100 的整數。

optimized_prompt 必須是可以直接放進 GEM 的完整 Prompt。
不要輸出 Markdown code block。
"""

    result, error = call_gemini(
        optimizer_prompt,
        model
    )

    if error:
        return None, error

    data = extract_json(result)

    if data is None:

        return None, (
            "Gemini 已完成分析，但無法解析成標準 JSON。"
        )

    return data, None


# =========================================================
# CREATE OPTIMIZED GEM
# =========================================================

def save_optimized_as_new_version(
    original_gem,
    optimized
):

    old_version = safe_value(
        original_gem,
        "version",
        "1.0"
    )

    try:

        parts = old_version.split(".")

        major = int(parts[0])
        minor = int(parts[1])

        new_version = f"{major}.{minor + 1}"

    except Exception:

        new_version = "1.1"

    payload = {
        "name": optimized.get(
            "optimized_name",
            safe_value(original_gem, "name")
        ),
        "description": optimized.get(
            "optimized_description",
            safe_value(original_gem, "description")
        ),
        "prompt": optimized.get(
            "optimized_prompt",
            safe_value(original_gem, "prompt")
        ),
        "knowledge": safe_value(
            original_gem,
            "knowledge"
        ),
        "version": new_version,
    }

    return insert_gem(payload)


# =========================================================
# LOGIN PAGE
# =========================================================

def show_login():

    st.title("💎 GEM Builder Cloud")

    st.subheader("登入你的 GEM Builder")

    tab1, tab2 = st.tabs(
        [
            "🔐 登入",
            "📝 註冊"
        ]
    )

    with tab1:

        email = st.text_input(
            "Email",
            key="login_email"
        )

        password = st.text_input(
            "密碼",
            type="password",
            key="login_password"
        )

        if st.button(
            "🔐 登入",
            use_container_width=True
        ):

            if not email or not password:

                st.warning(
                    "請輸入 Email 與密碼。"
                )

            else:

                success, message = login_user(
                    email,
                    password
                )

                if success:

                    st.success(message)
                    st.rerun()

                else:

                    st.error(message)

    with tab2:

        email2 = st.text_input(
            "註冊 Email",
            key="register_email"
        )

        password2 = st.text_input(
            "註冊密碼",
            type="password",
            key="register_password"
        )

        if st.button(
            "📝 建立帳號",
            use_container_width=True
        ):

            if not email2 or not password2:

                st.warning(
                    "請輸入 Email 與密碼。"
                )

            else:

                success, message = register_user(
                    email2,
                    password2
                )

                if success:

                    st.success(message)

                else:

                    st.error(message)


# =========================================================
# SIDEBAR
# =========================================================

def show_sidebar():

    with st.sidebar:

        st.title("💎 GEM Builder")

        st.caption("Cloud Edition · Day 32")

        st.divider()

        st.subheader("🤖 Gemini 模型")

        selected_model = st.selectbox(
            "目前使用模型",
            MODEL_OPTIONS,
            index=(
                MODEL_OPTIONS.index(
                    st.session_state.model_name
                )
                if st.session_state.model_name
                in MODEL_OPTIONS
                else 0
            ),
        )

        st.session_state.model_name = selected_model

        st.caption(
            "模型設定會套用於 GEM 優化功能。"
        )

        st.divider()

        if st.button(
            "🏠 回到首頁",
            use_container_width=True
        ):

            st.session_state.page = "home"
            st.session_state.selected_gem = None
            st.session_state.optimizer_open = False
            st.rerun()

        if st.button(
            "➕ 建立 GEM",
            use_container_width=True
        ):

            st.session_state.page = "create"
            st.session_state.selected_gem = None
            st.rerun()

        st.divider()

        if st.session_state.user:

            st.caption(
                f"👤 {st.session_state.user.email}"
            )

            if st.button(
                "🚪 登出",
                use_container_width=True
            ):

                logout()


# =========================================================
# CREATE PAGE
# =========================================================

def show_create_page():

    st.title("➕ 建立 GEM")

    name = st.text_input(
        "GEM 名稱"
    )

    description = st.text_area(
        "GEM 說明",
        height=100
    )

    prompt = st.text_area(
        "GEM Prompt",
        height=350,
        placeholder="輸入你的 GEM 指令..."
    )

    knowledge = st.text_area(
        "Knowledge Base",
        height=180,
        placeholder="輸入這個 GEM 需要知道的知識..."
    )

    version = st.text_input(
        "版本",
        value="1.0"
    )

    if st.button(
        "💾 儲存 GEM",
        type="primary",
        use_container_width=True
    ):

        if not name.strip():

            st.warning(
                "請輸入 GEM 名稱。"
            )

            return

        payload = {
            "name": name,
            "description": description,
            "prompt": prompt,
            "knowledge": knowledge,
            "version": version
        }

        result = insert_gem(payload)

        if result:

            st.success(
                "🎉 GEM 建立成功！"
            )

            st.session_state.gems = load_gems()

            st.rerun()


# =========================================================
# GEM OPTIMIZER UI
# =========================================================

def show_optimizer(gem):

    st.markdown(
        '<div class="optimizer-box">',
        unsafe_allow_html=True
    )

    st.subheader("✨ GEM 一鍵優化")

    st.write(
        "讓 Gemini 自動檢查並強化你的 GEM Prompt，"
        "提升 AI 執行的穩定性與完整度。"
    )

    st.markdown(
        """
        **Day 32 優化項目**

        ✅ 角色定位  
        ✅ 核心任務  
        ✅ 執行流程  
        ✅ 回應規則  
        ✅ 輸出格式  
        ✅ 邊界條件  
        ✅ 錯誤處理  
        ✅ 品質控制
        """
    )

    model = st.session_state.model_name

    st.info(
        f"目前優化模型：**{model}**"
    )

    col1, col2 = st.columns(2)

    with col1:

        optimize_button = st.button(
            "✨ 開始一鍵優化",
            type="primary",
            use_container_width=True
        )

    with col2:

        cancel_button = st.button(
            "✕ 關閉",
            use_container_width=True
        )

    if cancel_button:

        st.session_state.optimizer_open = False
        st.session_state.optimized_result = None
        st.rerun()

    if optimize_button:

        with st.spinner(
            "🤖 Gemini 正在分析並優化你的 GEM..."
        ):

            optimized, error = optimize_gem(
                gem,
                model
            )

        if error:

            st.error(
                f"❌ 優化失敗：{error}"
            )

        else:

            st.session_state.optimized_result = optimized

            st.success(
                "🎉 GEM 優化完成！"
            )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


# =========================================================
# OPTIMIZATION RESULT
# =========================================================

def show_optimization_result(gem):

    optimized = st.session_state.optimized_result

    if not optimized:
        return

    st.divider()

    st.subheader("📊 優化結果")

    before = optimized.get(
        "quality_score_before",
        0
    )

    after = optimized.get(
        "quality_score_after",
        0
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "優化前",
            f"{before}/100"
        )

    with col2:

        st.metric(
            "優化後",
            f"{after}/100",
            delta=after - before
        )

    with col3:

        improvement = after - before

        st.metric(
            "提升",
            f"+{improvement}"
        )

    st.subheader("📝 優化摘要")

    st.write(
        optimized.get(
            "optimization_summary",
            ""
        )
    )

    improvements = optimized.get(
        "improvements",
        []
    )

    if improvements:

        st.subheader("🔧 主要改善")

        for item in improvements:

            st.markdown(
                f"- {item}"
            )

    st.divider()

    st.subheader("🔍 Prompt 比較")

    left, right = st.columns(2)

    with left:

        st.markdown("### 原始 Prompt")

        st.text_area(
            "原始 Prompt",
            value=safe_value(
                gem,
                "prompt"
            ),
            height=450,
            disabled=True,
            label_visibility="collapsed"
        )

    with right:

        st.markdown("### ✨ 優化後 Prompt")

        optimized_prompt = optimized.get(
            "optimized_prompt",
            ""
        )

        st.text_area(
            "優化後 Prompt",
            value=optimized_prompt,
            height=450,
            label_visibility="collapsed"
        )

    st.divider()

    st.subheader("💾 儲存優化版本")

    st.caption(
        "原本的 GEM 不會被覆蓋，"
        "系統會建立一個新的版本。"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "💾 儲存為新版本",
            type="primary",
            use_container_width=True
        ):

            with st.spinner(
                "正在儲存新的 GEM 版本..."
            ):

                result = save_optimized_as_new_version(
                    gem,
                    optimized
                )

            if result:

                st.success(
                    "🎉 優化版本已成功儲存！"
                )

                st.session_state.gems = load_gems()

                st.session_state.optimized_result = None
                st.session_state.optimizer_open = False

                st.rerun()

    with col2:

        if st.button(
            "🗑️ 放棄優化結果",
            use_container_width=True
        ):

            st.session_state.optimized_result = None
            st.rerun()


# =========================================================
# GEM DETAIL PAGE
# =========================================================

def show_gem_detail(gem):

    st.title(
        f"💎 {safe_value(gem, 'name')}"
    )

    st.caption(
        f"版本：{safe_value(gem, 'version', '1.0')}"
    )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 基本資料",
            "🧠 Prompt",
            "📚 Knowledge",
            "✨ 一鍵優化"
        ]
    )

    with tab1:

        name = st.text_input(
            "GEM 名稱",
            value=safe_value(
                gem,
                "name"
            )
        )

        description = st.text_area(
            "GEM 說明",
            value=safe_value(
                gem,
                "description"
            ),
            height=120
        )

        version = st.text_input(
            "版本",
            value=safe_value(
                gem,
                "version",
                "1.0"
            )
        )

        if st.button(
            "💾 儲存基本資料",
            use_container_width=True
        ):

            result = update_gem(
                gem["id"],
                {
                    "name": name,
                    "description": description,
                    "version": version
                }
            )

            if result:

                st.success(
                    "基本資料已更新。"
                )

                st.session_state.gems = load_gems()
                st.rerun()

    with tab2:

        prompt = st.text_area(
            "GEM Prompt",
            value=safe_value(
                gem,
                "prompt"
            ),
            height=500
        )

        if st.button(
            "💾 儲存 Prompt",
            use_container_width=True
        ):

            result = update_gem(
                gem["id"],
                {
                    "prompt": prompt
                }
            )

            if result:

                st.success(
                    "Prompt 已更新。"
                )

                st.session_state.gems = load_gems()
                st.rerun()

    with tab3:

        knowledge = st.text_area(
            "Knowledge Base",
            value=safe_value(
                gem,
                "knowledge"
            ),
            height=450
        )

        if st.button(
            "💾 儲存 Knowledge",
            use_container_width=True
        ):

            result = update_gem(
                gem["id"],
                {
                    "knowledge": knowledge
                }
            )

            if result:

                st.success(
                    "Knowledge Base 已更新。"
                )

                st.session_state.gems = load_gems()
                st.rerun()

    with tab4:

        show_optimizer(gem)

        show_optimization_result(gem)

    st.divider()

    st.subheader("🗑️ 危險操作")

    if st.button(
        "🗑️ 刪除這個 GEM",
        use_container_width=True
    ):

        st.session_state["confirm_delete"] = gem["id"]

    if st.session_state.get(
        "confirm_delete"
    ) == gem["id"]:

        st.warning(
            "確定要刪除這個 GEM 嗎？此操作無法復原。"
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "確定刪除",
                type="primary",
                use_container_width=True
            ):

                if delete_gem(gem["id"]):

                    st.session_state.gems = load_gems()
                    st.session_state.selected_gem = None
                    st.session_state.confirm_delete = None

                    st.success(
                        "GEM 已刪除。"
                    )

                    st.rerun()

        with col2:

            if st.button(
                "取消",
                use_container_width=True
            ):

                st.session_state.confirm_delete = None
                st.rerun()


# =========================================================
# HOME PAGE
# =========================================================

def show_home():

    st.title("💎 GEM Builder Cloud")

    st.write(
        "建立、管理、優化你的 AI GEM。"
    )

    st.divider()

    # -----------------------------------------------------
    # Stats
    # -----------------------------------------------------

    total = len(st.session_state.gems)

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "💎 GEM 數量",
            total
        )

    with col2:

        st.metric(
            "🤖 Gemini",
            "已連線"
            if st.session_state.gemini_client
            else "未設定"
        )

    with col3:

        st.metric(
            "☁️ Supabase",
            "已連線"
            if supabase
            else "未設定"
        )

    st.divider()

    # -----------------------------------------------------
    # Quick Action
    # -----------------------------------------------------

    st.subheader("⚡ 快速操作")

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "➕ 建立新 GEM",
            type="primary",
            use_container_width=True
        ):

            st.session_state.page = "create"
            st.rerun()

    with col2:

        if st.button(
            "🔄 重新整理",
            use_container_width=True
        ):

            st.session_state.gems = load_gems()
            st.rerun()

    st.divider()

    # -----------------------------------------------------
    # GEM LIST
    # -----------------------------------------------------

    st.subheader("📚 我的 GEM")

    gems = st.session_state.gems

    if not gems:

        st.info(
            "目前還沒有 GEM。"
            "點擊「建立新 GEM」開始建立你的第一個 GEM。"
        )

        return

    for gem in gems:

        name = safe_value(
            gem,
            "name",
            "未命名 GEM"
        )

        description = safe_value(
            gem,
            "description",
            ""
        )

        version = safe_value(
            gem,
            "version",
            "1.0"
        )

        with st.container():

            st.markdown(
                '<div class="gem-card">',
                unsafe_allow_html=True
            )

            st.markdown(
                f'<div class="gem-title">{name}</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                f'<div class="gem-version">版本 {version}</div>',
                unsafe_allow_html=True
            )

            if description:

                st.write(
                    description[:180]
                )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "📋 開啟 GEM",
                    key=f"open_{gem['id']}",
                    use_container_width=True
                ):

                    st.session_state.selected_gem = gem["id"]
                    st.session_state.page = "detail"
                    st.session_state.optimizer_open = False
                    st.session_state.optimized_result = None

                    st.rerun()

            with col2:

                if st.button(
                    "✨ 一鍵優化",
                    key=f"opt_{gem['id']}",
                    use_container_width=True
                ):

                    st.session_state.selected_gem = gem["id"]
                    st.session_state.page = "detail"
                    st.session_state.optimizer_open = True
                    st.session_state.optimized_result = None

                    st.rerun()

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )


# =========================================================
# MAIN APP
# =========================================================

def main():

    # -----------------------------------------------------
    # Get user
    # -----------------------------------------------------

    if st.session_state.user is None:

        st.session_state.user = get_current_user()

    # -----------------------------------------------------
    # Login
    # -----------------------------------------------------

    if st.session_state.user is None:

        show_login()
        return

    # -----------------------------------------------------
    # Sidebar
    # -----------------------------------------------------

    show_sidebar()

    # -----------------------------------------------------
    # Load GEMs
    # -----------------------------------------------------

    if not st.session_state.gems:

        st.session_state.gems = load_gems()

    # -----------------------------------------------------
    # Pages
    # -----------------------------------------------------

    page = st.session_state.page

    if page == "create":

        show_create_page()

    elif page == "detail":

        gem_id = st.session_state.selected_gem

        selected = None

        for gem in st.session_state.gems:

            if str(gem.get("id")) == str(gem_id):

                selected = gem
                break

        if selected:

            show_gem_detail(selected)

        else:

            st.warning(
                "找不到這個 GEM。"
            )

            st.session_state.page = "home"

            st.rerun()

    else:

        show_home()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
````
