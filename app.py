import json
import re
import time
from datetime import datetime

import streamlit as st
from supabase import create_client
from google import genai


# ============================================================
# GEM Builder Cloud
# Day 32-C
# Gemini 穩定版
# ============================================================

st.set_page_config(
    page_title="GEM Builder Cloud",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

html, body, [class*="css"] {
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Microsoft JhengHei",
        Arial,
        sans-serif;
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

.gem-card {
    border: 1px solid #e6e6e6;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
    background: #ffffff;
    box-shadow: 0 2px 10px rgba(0,0,0,.04);
}

.gem-title {
    font-size: 21px;
    font-weight: 700;
    margin-bottom: 5px;
}

.gem-role {
    color: #666;
    font-size: 14px;
    line-height: 1.6;
}

.small-muted {
    color: #888;
    font-size: 13px;
}

.model-status {
    padding: 10px 12px;
    border-radius: 10px;
    background: #f7f7f7;
    margin-bottom: 10px;
    font-size: 14px;
}

.result-box {
    border: 1px solid #e7e7e7;
    border-radius: 14px;
    padding: 18px;
    background: #fafafa;
    line-height: 1.8;
}

@media (max-width: 768px) {

    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-top: 0.8rem;
    }

    h1 {
        font-size: 1.7rem !important;
    }

    h2 {
        font-size: 1.4rem !important;
    }

    h3 {
        font-size: 1.15rem !important;
    }

    .gem-card {
        padding: 14px;
        border-radius: 12px;
    }

    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    div[data-testid="stHorizontalBlock"] > div {
        min-width: 100% !important;
    }

    button {
        min-height: 42px;
    }

}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Secrets
# ============================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"].strip()
except Exception:
    SUPABASE_URL = ""

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip()
except Exception:
    SUPABASE_KEY = ""

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"].strip()
except Exception:
    GEMINI_API_KEY = ""


# ============================================================
# Supabase
# ============================================================

supabase = None
supabase_error = ""

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )
    except Exception as e:
        supabase_error = str(e)
else:
    supabase_error = "尚未設定 SUPABASE_URL 或 SUPABASE_KEY"


# ============================================================
# Tables
# ============================================================

GEM_TABLE = "gems"
KNOWLEDGE_TABLE = "gem_knowledge"
CHAT_SESSION_TABLE = "gem_chat_sessions"
CHAT_MESSAGE_TABLE = "gem_chat_messages"
CLOUD_TEST_TABLE = "cloud_test"


# ============================================================
# Gemini 模型設定
# ============================================================

PREFERRED_GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]


MODEL_DISPLAY_NAMES = {
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-3.7-flash": "Gemini 3.7 Flash",
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemini-3.5-flash": "Gemini 3.5 Flash",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
}


# ============================================================
# Session State
# ============================================================

DEFAULT_STATE = {
    "page": "首頁",
    "selected_gem_id": None,
    "selected_chat_session_id": None,

    "gemini_result": "",
    "optimizer_result": "",

    "delete_confirm": False,

    "available_models": [],
    "selected_model": None,

    "model_error": "",
    "model_status": "unknown",

    "workspace_search": "",

    "optimization_preview": None,
    "optimization_source_gem_id": None,
    "optimization_error": "",

    "gemini_last_checked": None,

    "import_result": None,

    "generator_result": "",

    "chat_input": "",

    "template_result": "",

    "supabase_error": supabase_error,
}


for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# Gemini Client
# ============================================================

def get_gemini_client():
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY 尚未設定。\n\n"
            "請到 Streamlit Cloud → App → Settings → Secrets "
            "確認 GEMINI_API_KEY。"
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# Gemini 工具
# ============================================================

def normalize_model_name(name):
    if not name:
        return ""

    name = str(name).strip()

    if name.startswith("models/"):
        name = name[7:]

    return name


def get_supported_actions(model):
    """
    不同 google-genai SDK 版本可能回傳：

    ["generateContent"]

    或 enum：

    SupportedAction.GENERATE_CONTENT

    所以這裡統一處理。
    """

    raw_actions = getattr(
        model,
        "supported_actions",
        None,
    )

    if not raw_actions:
        return []

    result = []

    for action in raw_actions:

        value = getattr(
            action,
            "value",
            action,
        )

        text = str(value)

        text = text.replace("_", "")
        text = text.replace("-", "")
        text = text.lower()

        result.append(text)

    return result


def safe_error_text(error):
    """
    避免錯誤訊息中不小心出現 API Key。
    """

    text = str(error)

    text = re.sub(
        r"AIza[0-9A-Za-z_\-]{20,}",
        "[API KEY 已隱藏]",
        text,
    )

    if len(text) > 4000:
        text = text[:4000] + "\n..."

    return text


def model_is_generate_content_model(model):
    actions = get_supported_actions(model)

    # 有明確 action 才檢查。
    # 如果 SDK 沒提供 supported_actions，
    # 不要因此把模型全部判定為不可用。
    if actions:
        return "generatecontent" in actions

    return True


def probe_gemini_model(model_name):
    """
    用極小請求測試 Gemini 是否真的可以呼叫。

    只在 models.list() 無法取得有效模型時使用，
    避免大量消耗 API quota。
    """

    client = get_gemini_client()

    response = client.models.generate_content(
        model=model_name,
        contents="請只回答 OK",
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if text and str(text).strip():
        return True, str(text).strip()

    return False, "模型沒有回傳文字"


# ============================================================
# Gemini 模型偵測
# ============================================================

def load_gemini_models(force=False):

    if (
        not force
        and st.session_state.available_models
    ):
        return st.session_state.available_models

    st.session_state.model_error = ""
    st.session_state.model_status = "checking"
    st.session_state.available_models = []

    if not GEMINI_API_KEY:

        st.session_state.model_status = "error"

        st.session_state.model_error = (
            "GEMINI_API_KEY 尚未設定。"
        )

        return []

    list_error = ""

    try:

        client = get_gemini_client()

        api_models = list(
            client.models.list()
        )

        found = {}

        for model in api_models:

            name = normalize_model_name(
                getattr(
                    model,
                    "name",
                    "",
                )
            )

            if not name:
                continue

            if name not in PREFERRED_GEMINI_MODELS:
                continue

            if not model_is_generate_content_model(model):
                continue

            found[name] = model

        available = [
            model_name
            for model_name in PREFERRED_GEMINI_MODELS
            if model_name in found
        ]

        # ----------------------------------------------------
        # 如果 API 有正常回傳，但是沒有抓到模型
        # 再用 Gemini 3.6 Flash 做一次實際測試。
        # ----------------------------------------------------

        if not available:

            fallback_model = "gemini-3.6-flash"

            try:

                success, _ = probe_gemini_model(
                    fallback_model
                )

                if success:
                    available = [
                        fallback_model
                    ]

                else:
                    st.session_state.model_error = (
                        "Gemini API 可以連線，但目前沒有偵測到 "
                        "可用的主要文字生成模型。"
                    )

            except Exception as fallback_error:

                st.session_state.model_error = (
                    "Gemini 模型清單沒有找到可用模型。\n\n"
                    "另外測試 Gemini 3.6 Flash 也失敗：\n"
                    + safe_error_text(
                        fallback_error
                    )
                )

        st.session_state.available_models = available

        if available:

            current = (
                st.session_state.selected_model
            )

            if current not in available:
                st.session_state.selected_model = (
                    available[0]
                )

            st.session_state.model_status = "connected"

            st.session_state.gemini_last_checked = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        else:

            st.session_state.selected_model = None

            if not st.session_state.model_error:

                st.session_state.model_error = (
                    "目前沒有偵測到可用 Gemini 模型。"
                )

            st.session_state.model_status = "error"

    except Exception as error:

        list_error = safe_error_text(error)

        # ----------------------------------------------------
        # models.list() 失敗
        # 不代表 generate_content 一定不能用。
        #
        # 所以再測試一次 Gemini 3.6 Flash。
        # ----------------------------------------------------

        fallback_model = "gemini-3.6-flash"

        try:

            success, _ = probe_gemini_model(
                fallback_model
            )

            if success:

                st.session_state.available_models = [
                    fallback_model
                ]

                st.session_state.selected_model = (
                    fallback_model
                )

                st.session_state.model_status = "connected"

                st.session_state.model_error = (
                    "模型清單 API 無法取得完整清單，"
                    "但 Gemini 3.6 Flash 實際呼叫成功，"
                    "因此已啟用 Gemini 3.6 Flash。"
                )

                st.session_state.gemini_last_checked = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

            else:

                st.session_state.model_status = "error"

                st.session_state.model_error = (
                    "Gemini 模型清單讀取失敗：\n\n"
                    + list_error
                    + "\n\n"
                    "Gemini 3.6 Flash 測試也沒有成功。"
                )

        except Exception as fallback_error:

            st.session_state.model_status = "error"

            st.session_state.model_error = (
                "Gemini API 偵測失敗。\n\n"
                "① models.list()：\n"
                + list_error
                + "\n\n"
                "② Gemini 3.6 Flash 測試：\n"
                + safe_error_text(
                    fallback_error
                )
            )

    return st.session_state.available_models


# ============================================================
# 啟動時偵測 Gemini
# ============================================================

if not st.session_state.available_models:
    load_gemini_models()


# ============================================================
# Gemini 模型候選
# ============================================================

def get_model_candidates():

    candidates = []

    selected = (
        st.session_state.selected_model
    )

    if selected:
        candidates.append(selected)

    for model in (
        st.session_state.available_models
    ):

        if model not in candidates:
            candidates.append(model)

    return candidates


# ============================================================
# Gemini 問答
# ============================================================

def ask_gemini(
    prompt,
    model=None,
    retries=2,
):

    candidates = []

    if model:
        candidates.append(model)

    for item in get_model_candidates():

        if item not in candidates:
            candidates.append(item)

    if not candidates:

        load_gemini_models(
            force=True
        )

        candidates = get_model_candidates()

    if not candidates:

        error_message = (
            st.session_state.model_error
            or
            "目前沒有可使用的 Gemini 模型。"
        )

        return (
            "❌ Gemini 無法使用。\n\n"
            + error_message
        )

    try:

        client = get_gemini_client()

    except Exception as error:

        return (
            "❌ Gemini Client 建立失敗。\n\n"
            + safe_error_text(error)
        )

    errors = []

    for model_name in candidates:

        for attempt in range(
            retries + 1
        ):

            try:

                response = (
                    client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                )

                text = getattr(
                    response,
                    "text",
                    None,
                )

                if text and str(text).strip():

                    st.session_state.selected_model = (
                        model_name
                    )

                    return str(text).strip()

                errors.append(
                    f"{model_name}：模型沒有回傳文字"
                )

                break

            except Exception as error:

                error_text = safe_error_text(
                    error
                )

                errors.append(
                    f"{model_name}：{error_text}"
                )

                temporary = any(
                    keyword in error_text.upper()
                    for keyword in [
                        "503",
                        "UNAVAILABLE",
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "500",
                        "INTERNAL",
                        "TIMEOUT",
                        "DEADLINE",
                    ]
                )

                if temporary and attempt < retries:

                    time.sleep(
                        1.5 * (attempt + 1)
                    )

                    continue

                break

    return (
        "❌ Gemini 呼叫失敗。\n\n"
        + "\n\n".join(errors)
    )


# ============================================================
# Supabase 工具
# ============================================================

def supabase_ready():

    if supabase is None:
        return False

    return True


def get_gems():

    if not supabase_ready():
        return []

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .select("*")
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return response.data or []

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return []


def get_gem(gem_id):

    if not supabase_ready():
        return None

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .select("*")
            .eq(
                "id",
                gem_id,
            )
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return None


def create_gem(
    name,
    role,
    workflow,
    greeting,
    category="一般",
    tags="",
):

    if not supabase_ready():
        return None, "Supabase 尚未連線"

    data = {
        "name": name,
        "role": role,
        "workflow": workflow,
        "greeting": greeting,
        "category": category,
        "tags": tags,
    }

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .insert(data)
            .execute()
        )

        if response.data:
            return response.data[0], ""

        return None, "建立 GEM 失敗"

    except Exception as error:

        return None, safe_error_text(error)


def update_gem(
    gem_id,
    data,
):

    if not supabase_ready():
        return False, "Supabase 尚未連線"

    try:

        (
            supabase
            .table(GEM_TABLE)
            .update(data)
            .eq(
                "id",
                gem_id,
            )
            .execute()
        )

        return True, ""

    except Exception as error:

        return False, safe_error_text(error)


def delete_gem(
    gem_id,
):

    if not supabase_ready():
        return False, "Supabase 尚未連線"

    try:

        (
            supabase
            .table(GEM_TABLE)
            .delete()
            .eq(
                "id",
                gem_id,
            )
            .execute()
        )

        return True, ""

    except Exception as error:

        return False, safe_error_text(error)


# ============================================================
# Knowledge
# ============================================================

def get_knowledge(
    gem_id,
):

    if not supabase_ready():
        return []

    try:

        response = (
            supabase
            .table(KNOWLEDGE_TABLE)
            .select("*")
            .eq(
                "gem_id",
                gem_id,
            )
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return response.data or []

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return []


def create_knowledge(
    gem_id,
    title,
    content,
):

    if not supabase_ready():
        return False, "Supabase 尚未連線"

    data = {
        "gem_id": gem_id,
        "title": title,
        "content": content,
    }

    try:

        (
            supabase
            .table(KNOWLEDGE_TABLE)
            .insert(data)
            .execute()
        )

        return True, ""

    except Exception as error:

        return False, safe_error_text(error)


def delete_knowledge(
    knowledge_id,
):

    if not supabase_ready():
        return False, "Supabase 尚未連線"

    try:

        (
            supabase
            .table(KNOWLEDGE_TABLE)
            .delete()
            .eq(
                "id",
                knowledge_id,
            )
            .execute()
        )

        return True, ""

    except Exception as error:

        return False, safe_error_text(error)


# ============================================================
# Chat
# ============================================================

def get_chat_sessions(
    gem_id=None,
):

    if not supabase_ready():
        return []

    try:

        query = (
            supabase
            .table(CHAT_SESSION_TABLE)
            .select("*")
        )

        if gem_id is not None:
            query = query.eq(
                "gem_id",
                gem_id,
            )

        response = (
            query
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return response.data or []

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return []


def create_chat_session(
    gem_id,
    title="新的對話",
):

    if not supabase_ready():
        return None

    try:

        response = (
            supabase
            .table(CHAT_SESSION_TABLE)
            .insert(
                {
                    "gem_id": gem_id,
                    "title": title,
                }
            )
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return None


def get_chat_messages(
    session_id,
):

    if not supabase_ready():
        return []

    try:

        response = (
            supabase
            .table(CHAT_MESSAGE_TABLE)
            .select("*")
            .eq(
                "session_id",
                session_id,
            )
            .order(
                "created_at",
                desc=False,
            )
            .execute()
        )

        return response.data or []

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return []


def create_chat_message(
    session_id,
    role,
    content,
):

    if not supabase_ready():
        return False

    try:

        (
            supabase
            .table(CHAT_MESSAGE_TABLE)
            .insert(
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                }
            )
            .execute()
        )

        return True

    except Exception as error:

        st.session_state.supabase_error = (
            safe_error_text(error)
        )

        return False


# ============================================================
# GEM Prompt
# ============================================================

def build_gem_prompt(
    gem,
    knowledge,
    history,
    user_message,
):

    role = gem.get(
        "role",
        "",
    )

    workflow = gem.get(
        "workflow",
        "",
    )

    greeting = gem.get(
        "greeting",
        "",
    )

    knowledge_text = ""

    for item in knowledge:

        title = item.get(
            "title",
            "",
        )

        content = item.get(
            "content",
            "",
        )

        knowledge_text += (
            f"\n【{title}】\n"
            f"{content}\n"
        )

    history_text = ""

    for item in history[-12:]:

        role_name = item.get(
            "role",
            "",
        )

        content = item.get(
            "content",
            "",
        )

        if role_name == "user":
            label = "使用者"
        else:
            label = "GEM"

        history_text += (
            f"{label}：{content}\n"
        )

    prompt = f"""
你是一個 GEM Builder 中的專業 AI GEM。

【GEM 名稱】
{gem.get("name", "")}

【角色】
{role}

【工作流程與規則】
{workflow}

【開場白】
{greeting}

【Knowledge】
{knowledge_text}

【近期對話】
{history_text}

【使用者目前訊息】
{user_message}

請依照 GEM 的角色、工作流程、規則與 Knowledge 回應。

要求：

1. 使用繁體中文。
2. 不要說自己是 GEM Builder。
3. 不要自行捏造 Knowledge 中不存在的資料。
4. 回答要自然、實用。
5. 如果資訊不足，可以先詢問必要問題。
6. 如果 GEM 本身有指定工作流程，優先遵循工作流程。
"""

    return prompt


# ============================================================
# 匯出
# ============================================================

def gem_to_dict(gem):

    return {
        "name": gem.get(
            "name",
            "",
        ),
        "role": gem.get(
            "role",
            "",
        ),
        "workflow": gem.get(
            "workflow",
            "",
        ),
        "greeting": gem.get(
            "greeting",
            "",
        ),
        "category": gem.get(
            "category",
            "",
        ),
        "tags": gem.get(
            "tags",
            "",
        ),
    }


def build_txt_export(
    gem,
    knowledge,
):

    text = f"""
GEM 名稱：{gem.get("name", "")}

角色：
{gem.get("role", "")}

工作流程與規則：
{gem.get("workflow", "")}

開場白：
{gem.get("greeting", "")}

分類：
{gem.get("category", "")}

標籤：
{gem.get("tags", "")}

====================
Knowledge
====================

"""

    for item in knowledge:

        text += (
            f"\n【{item.get('title', '')}】\n"
            f"{item.get('content', '')}\n"
        )

    return text


def build_json_export(
    gem,
    knowledge,
):

    return json.dumps(
        {
            "gem": gem_to_dict(gem),
            "knowledge": [
                {
                    "title": item.get(
                        "title",
                        "",
                    ),
                    "content": item.get(
                        "content",
                        "",
                    ),
                }
                for item in knowledge
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


# ============================================================
# AI 優化
# ============================================================

def extract_json_from_text(
    text,
):

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.I,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.S,
    )

    if match:

        try:
            return json.loads(
                match.group(0)
            )
        except Exception:
            return None

    return None


def normalize_optimization_result(
    data,
):

    if not isinstance(data, dict):
        return None

    result = {}

    result["name"] = str(
        data.get(
            "name",
            "",
        )
    ).strip()

    result["role"] = str(
        data.get(
            "role",
            "",
        )
    ).strip()

    result["workflow"] = str(
        data.get(
            "workflow",
            "",
        )
    ).strip()

    result["greeting"] = str(
        data.get(
            "greeting",
            "",
        )
    ).strip()

    return result


def optimize_gem(
    gem,
    knowledge,
):

    knowledge_text = ""

    for item in knowledge:

        knowledge_text += (
            f"【{item.get('title', '')}】\n"
            f"{item.get('content', '')}\n\n"
        )

    prompt = f"""
你是一名專業 AI GEM 設計師。

請幫我優化以下 GEM。

【目前名稱】
{gem.get("name", "")}

【目前角色】
{gem.get("role", "")}

【目前工作流程】
{gem.get("workflow", "")}

【目前開場白】
{gem.get("greeting", "")}

【Knowledge】
{knowledge_text}

請改善：

1. GEM 名稱
2. GEM 角色
3. GEM 工作流程
4. GEM 開場白

要求：

- 保留原本核心用途
- 讓角色更加清楚
- 讓工作流程更加容易執行
- 讓 AI 回答更加穩定
- 使用繁體中文
- 不要增加與原始用途無關的功能

只輸出 JSON：

{{
    "name": "...",
    "role": "...",
    "workflow": "...",
    "greeting": "..."
}}
"""

    result = ask_gemini(
        prompt
    )

    if result.startswith("❌"):
        return None, result

    data = extract_json_from_text(
        result
    )

    normalized = normalize_optimization_result(
        data
    )

    if not normalized:
        return None, (
            "AI 有回應，但無法解析成正確 JSON。\n\n"
            + result
        )

    return normalized, ""


# ============================================================
# GEM 卡片
# ============================================================

def render_gem_card(
    gem,
):

    name = gem.get(
        "name",
        "未命名 GEM",
    )

    role = gem.get(
        "role",
        "",
    )

    category = gem.get(
        "category",
        "一般",
    )

    tags = gem.get(
        "tags",
        "",
    )

    st.markdown(
        f"""
<div class="gem-card">

<div class="gem-title">
{name}
</div>

<div class="gem-role">
{role}
</div>

<div class="small-muted">
分類：{category}
</div>

<div class="small-muted">
標籤：{tags}
</div>

</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Dashboard
# ============================================================

def render_dashboard():

    gems = get_gems()

    knowledge_count = 0
    chat_count = 0

    if supabase_ready():

        try:

            result = (
                supabase
                .table(KNOWLEDGE_TABLE)
                .select(
                    "id",
                    count="exact",
                )
                .execute()
            )

            knowledge_count = (
                result.count or 0
            )

        except Exception:
            knowledge_count = 0

        try:

            result = (
                supabase
                .table(CHAT_MESSAGE_TABLE)
                .select(
                    "id",
                    count="exact",
                )
                .execute()
            )

            chat_count = (
                result.count or 0
            )

        except Exception:
            chat_count = 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "GEM",
            len(gems),
        )

    with col2:
        st.metric(
            "Knowledge",
            knowledge_count,
        )

    with col3:
        st.metric(
            "Chat 訊息",
            chat_count,
        )

    with col4:
        st.metric(
            "Gemini 模型",
            len(
                st.session_state.available_models
            ),
        )


# ============================================================
# 首頁
# ============================================================

def page_home():

    st.title(
        "☁️ GEM Builder Cloud"
    )

    st.caption(
        "Day 32-C｜Gemini 穩定版"
    )

    status = (
        st.session_state.model_status
    )

    selected_model = (
        st.session_state.selected_model
    )

    if (
        status == "connected"
        and selected_model
    ):

        st.success(
            "🟢 Gemini 已連線｜目前模型："
            + MODEL_DISPLAY_NAMES.get(
                selected_model,
                selected_model,
            )
        )

    elif (
        st.session_state.model_error
    ):

        st.error(
            "🔴 Gemini 目前無法正常偵測"
        )

        with st.expander(
            "查看 Gemini 詳細診斷資訊"
        ):

            st.code(
                st.session_state.model_error
            )

    else:

        st.warning(
            "🟡 目前沒有偵測到可用 Gemini 模型。"
        )

    render_dashboard()

    st.divider()

    st.subheader(
        "🧩 最近 GEM"
    )

    gems = get_gems()

    if not gems:

        st.info(
            "目前還沒有 GEM。"
        )

        if st.button(
            "➕ 建立第一個 GEM",
            use_container_width=True,
        ):
            st.session_state.page = "建立 GEM"
            st.rerun()

        return

    for gem in gems[:6]:

        with st.container():

            render_gem_card(
                gem
            )

            if st.button(
                "開啟",
                key=f"home_open_{gem.get('id')}",
            ):

                st.session_state.selected_gem_id = (
                    gem.get("id")
                )

                st.session_state.page = "GEM 詳情"

                st.rerun()


# ============================================================
# 建立 GEM
# ============================================================

def page_create_gem():

    st.title(
        "➕ 建立 GEM"
    )

    with st.form(
        "create_gem_form"
    ):

        name = st.text_input(
            "GEM 名稱"
        )

        role = st.text_area(
            "角色",
            height=120,
            placeholder="例如：青年職涯探索陪談夥伴",
        )

        workflow = st.text_area(
            "工作流程與規則",
            height=240,
            placeholder=(
                "請描述 AI 要怎麼工作、"
                "回答順序、限制與原則。"
            ),
        )

        greeting = st.text_area(
            "開場白",
            height=120,
        )

        category = st.text_input(
            "分類",
            value="一般",
        )

        tags = st.text_input(
            "標籤",
            placeholder="例如：職涯, MBTI, SFBT",
        )

        submitted = st.form_submit_button(
            "🚀 建立 GEM",
            use_container_width=True,
        )

    if submitted:

        if not name.strip():

            st.error(
                "請輸入 GEM 名稱。"
            )

            return

        gem, error = create_gem(
            name=name.strip(),
            role=role.strip(),
            workflow=workflow.strip(),
            greeting=greeting.strip(),
            category=category.strip(),
            tags=tags.strip(),
        )

        if error:

            st.error(error)

        else:

            st.success(
                "🎉 GEM 建立成功！"
            )

            st.session_state.selected_gem_id = (
                gem.get("id")
            )

            st.session_state.page = "GEM 詳情"

            st.rerun()


# ============================================================
# Workspace
# ============================================================

def page_workspace():

    st.title(
        "🗂️ GEM Workspace"
    )

    search = st.text_input(
        "搜尋 GEM",
        value=st.session_state.workspace_search,
        placeholder="搜尋名稱、角色、分類、標籤",
    )

    st.session_state.workspace_search = search

    gems = get_gems()

    search_lower = search.lower().strip()

    if search_lower:

        gems = [
            gem
            for gem in gems
            if search_lower in (
                str(
                    gem.get(
                        "name",
                        "",
                    )
                )
                + " "
                + str(
                    gem.get(
                        "role",
                        "",
                    )
                )
                + " "
                + str(
                    gem.get(
                        "category",
                        "",
                    )
                )
                + " "
                + str(
                    gem.get(
                        "tags",
                        "",
                    )
                )
            ).lower()
        ]

    if not gems:

        st.info(
            "找不到 GEM。"
        )

        return

    for gem in gems:

        with st.container():

            render_gem_card(
                gem
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "開啟",
                    key=f"workspace_open_{gem.get('id')}",
                    use_container_width=True,
                ):

                    st.session_state.selected_gem_id = (
                        gem.get("id")
                    )

                    st.session_state.page = "GEM 詳情"

                    st.rerun()

            with col2:

                if st.button(
                    "編輯",
                    key=f"workspace_edit_{gem.get('id')}",
                    use_container_width=True,
                ):

                    st.session_state.selected_gem_id = (
                        gem.get("id")
                    )

                    st.session_state.page = "編輯 GEM"

                    st.rerun()


# ============================================================
# GEM 詳情
# ============================================================

def page_gem_detail():

    gem_id = (
        st.session_state.selected_gem_id
    )

    if not gem_id:

        st.warning(
            "尚未選擇 GEM。"
        )

        return

    gem = get_gem(
        gem_id
    )

    if not gem:

        st.error(
            "找不到 GEM。"
        )

        return

    st.title(
        "🧩 " + gem.get(
            "name",
            "未命名 GEM",
        )
    )

    st.caption(
        gem.get(
            "role",
            "",
        )
    )

    tabs = st.tabs(
        [
            "內容",
            "編輯",
            "Knowledge",
            "AI 優化",
            "測試",
            "Chat",
        ]
    )

    # --------------------------------------------------------
    # Content
    # --------------------------------------------------------

    with tabs[0]:

        st.subheader(
            "角色"
        )

        st.write(
            gem.get(
                "role",
                "",
            )
        )

        st.subheader(
            "工作流程與規則"
        )

        st.code(
            gem.get(
                "workflow",
                "",
            )
        )

        st.subheader(
            "開場白"
        )

        st.write(
            gem.get(
                "greeting",
                "",
            )
        )

        st.divider()

        knowledge = get_knowledge(
            gem_id
        )

        col1, col2 = st.columns(2)

        with col1:

            txt_data = build_txt_export(
                gem,
                knowledge,
            )

            st.download_button(
                "⬇️ 匯出 TXT",
                data=txt_data.encode(
                    "utf-8"
                ),
                file_name=(
                    f"{gem.get('name', 'gem')}.txt"
                ),
                mime="text/plain",
                use_container_width=True,
            )

        with col2:

            json_data = build_json_export(
                gem,
                knowledge,
            )

            st.download_button(
                "⬇️ 匯出 JSON",
                data=json_data.encode(
                    "utf-8"
                ),
                file_name=(
                    f"{gem.get('name', 'gem')}.json"
                ),
                mime="application/json",
                use_container_width=True,
            )

        st.divider()

        if st.button(
            "🗑️ 刪除 GEM",
            use_container_width=True,
        ):

            st.session_state.delete_confirm = True

        if st.session_state.delete_confirm:

            st.warning(
                "確定要刪除這個 GEM 嗎？"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "確定刪除",
                    use_container_width=True,
                ):

                    ok, error = delete_gem(
                        gem_id
                    )

                    if ok:

                        st.session_state.selected_gem_id = None
                        st.session_state.delete_confirm = False
                        st.session_state.page = "工作區"

                        st.rerun()

                    else:

                        st.error(error)

            with col2:

                if st.button(
                    "取消",
                    use_container_width=True,
                ):

                    st.session_state.delete_confirm = False
                    st.rerun()

    # --------------------------------------------------------
    # Edit
    # --------------------------------------------------------

    with tabs[1]:

        st.subheader(
            "編輯 GEM"
        )

        name = st.text_input(
            "名稱",
            value=gem.get(
                "name",
                "",
            ),
            key="detail_edit_name",
        )

        role = st.text_area(
            "角色",
            value=gem.get(
                "role",
                "",
            ),
            height=120,
            key="detail_edit_role",
        )

        workflow = st.text_area(
            "工作流程",
            value=gem.get(
                "workflow",
                "",
            ),
            height=240,
            key="detail_edit_workflow",
        )

        greeting = st.text_area(
            "開場白",
            value=gem.get(
                "greeting",
                "",
            ),
            height=120,
            key="detail_edit_greeting",
        )

        category = st.text_input(
            "分類",
            value=gem.get(
                "category",
                "",
            ),
            key="detail_edit_category",
        )

        tags = st.text_input(
            "標籤",
            value=gem.get(
                "tags",
                "",
            ),
            key="detail_edit_tags",
        )

        if st.button(
            "💾 儲存修改",
            use_container_width=True,
        ):

            ok, error = update_gem(
                gem_id,
                {
                    "name": name,
                    "role": role,
                    "workflow": workflow,
                    "greeting": greeting,
                    "category": category,
                    "tags": tags,
                },
            )

            if ok:

                st.success(
                    "已儲存。"
                )

                time.sleep(.4)
                st.rerun()

            else:

                st.error(error)

    # --------------------------------------------------------
    # Knowledge
    # --------------------------------------------------------

    with tabs[2]:

        st.subheader(
            "📚 Knowledge"
        )

        knowledge = get_knowledge(
            gem_id
        )

        with st.form(
            f"knowledge_form_{gem_id}"
        ):

            title = st.text_input(
                "Knowledge 標題"
            )

            content = st.text_area(
                "Knowledge 內容",
                height=220,
            )

            submitted = st.form_submit_button(
                "➕ 新增 Knowledge",
                use_container_width=True,
            )

        if submitted:

            if not title.strip():

                st.error(
                    "請輸入標題。"
                )

            elif not content.strip():

                st.error(
                    "請輸入內容。"
                )

            else:

                ok, error = create_knowledge(
                    gem_id,
                    title,
                    content,
                )

                if ok:

                    st.success(
                        "Knowledge 已新增。"
                    )

                    st.rerun()

                else:

                    st.error(error)

        st.divider()

        if not knowledge:

            st.info(
                "目前沒有 Knowledge。"
            )

        for item in knowledge:

            with st.expander(
                item.get(
                    "title",
                    "未命名",
                )
            ):

                st.write(
                    item.get(
                        "content",
                        "",
                    )
                )

                if st.button(
                    "刪除",
                    key=f"delete_knowledge_{item.get('id')}",
                ):

                    ok, error = delete_knowledge(
                        item.get("id")
                    )

                    if ok:
                        st.rerun()

                    else:
                        st.error(error)

    # --------------------------------------------------------
    # AI Optimization
    # --------------------------------------------------------

    with tabs[3]:

        st.subheader(
            "✨ Day 32｜AI GEM 優化"
        )

        st.write(
            "讓 Gemini 分析目前 GEM，"
            "並產生一份優化版本。"
        )

        if st.button(
            "🚀 開始 AI 優化",
            use_container_width=True,
        ):

            with st.spinner(
                "Gemini 正在分析 GEM..."
            ):

                result, error = optimize_gem(
                    gem,
                    get_knowledge(
                        gem_id
                    ),
                )

            if error:

                st.error(error)

                st.session_state.optimization_error = (
                    error
                )

            else:

                st.session_state.optimization_preview = (
                    result
                )

                st.session_state.optimization_source_gem_id = (
                    gem_id
                )

                st.session_state.optimization_error = ""

                st.rerun()

        preview = (
            st.session_state.optimization_preview
        )

        if (
            preview
            and
            st.session_state.optimization_source_gem_id
            == gem_id
        ):

            st.divider()

            st.subheader(
                "AI 優化預覽"
            )

            st.text_input(
                "名稱",
                value=preview.get(
                    "name",
                    "",
                ),
                disabled=True,
            )

            st.text_area(
                "角色",
                value=preview.get(
                    "role",
                    "",
                ),
                height=120,
                disabled=True,
            )

            st.text_area(
                "工作流程",
                value=preview.get(
                    "workflow",
                    "",
                ),
                height=240,
                disabled=True,
            )

            st.text_area(
                "開場白",
                value=preview.get(
                    "greeting",
                    "",
                ),
                height=120,
                disabled=True,
            )

            if st.button(
                "✅ 套用 AI 優化版本",
                use_container_width=True,
            ):

                ok, error = update_gem(
                    gem_id,
                    preview,
                )

                if ok:

                    st.session_state.optimization_preview = None

                    st.success(
                        "AI 優化版本已套用。"
                    )

                    time.sleep(.5)

                    st.rerun()

                else:

                    st.error(error)

    # --------------------------------------------------------
    # Test
    # --------------------------------------------------------

    with tabs[4]:

        st.subheader(
            "🧪 GEM 測試"
        )

        user_message = st.text_area(
            "輸入測試訊息",
            height=140,
            placeholder="例如：我最近不知道自己適合什麼工作。",
            key=f"test_message_{gem_id}",
        )

        if st.button(
            "🤖 測試 GEM",
            use_container_width=True,
        ):

            if not user_message.strip():

                st.warning(
                    "請輸入測試訊息。"
                )

            else:

                with st.spinner(
                    "Gemini 回應中..."
                ):

                    prompt = build_gem_prompt(
                        gem,
                        get_knowledge(
                            gem_id
                        ),
                        [],
                        user_message,
                    )

                    result = ask_gemini(
                        prompt
                    )

                st.session_state.gemini_result = (
                    result
                )

        if st.session_state.gemini_result:

            st.divider()

            st.subheader(
                "AI 回應"
            )

            st.markdown(
                st.session_state.gemini_result
            )

    # --------------------------------------------------------
    # Chat
    # --------------------------------------------------------

    with tabs[5]:

        st.subheader(
            "💬 GEM Chat"
        )

        sessions = get_chat_sessions(
            gem_id
        )

        if sessions:

            session_options = {
                str(
                    item.get(
                        "id"
                    )
                ): item
                for item in sessions
            }

            labels = [
                item.get(
                    "title",
                    "未命名對話",
                )
                for item in sessions
            ]

            selected_index = 0

            if (
                st.session_state.selected_chat_session_id
                in session_options
            ):

                for index, item in enumerate(
                    sessions
                ):

                    if str(
                        item.get("id")
                    ) == str(
                        st.session_state.selected_chat_session_id
                    ):
                        selected_index = index
                        break

            selected_session = st.selectbox(
                "選擇對話",
                sessions,
                index=selected_index,
                format_func=lambda x: x.get(
                    "title",
                    "未命名對話",
                ),
                key=f"chat_session_select_{gem_id}",
            )

            st.session_state.selected_chat_session_id = (
                selected_session.get("id")
            )

        else:

            selected_session = None

        if st.button(
            "➕ 建立新對話",
            use_container_width=True,
        ):

            new_session = create_chat_session(
                gem_id
            )

            if new_session:

                st.session_state.selected_chat_session_id = (
                    new_session.get("id")
                )

                st.rerun()

        if not selected_session:

            st.info(
                "請建立一個新的對話。"
            )

        else:

            messages = get_chat_messages(
                selected_session.get("id")
            )

            for message in messages:

                role = message.get(
                    "role",
                    "user",
                )

                if role == "user":

                    with st.chat_message(
                        "user"
                    ):

                        st.write(
                            message.get(
                                "content",
                                "",
                            )
                        )

                else:

                    with st.chat_message(
                        "assistant"
                    ):

                        st.markdown(
                            message.get(
                                "content",
                                "",
                            )
                        )

            chat_input = st.chat_input(
                "輸入訊息..."
            )

            if chat_input:

                session_id = (
                    selected_session.get(
                        "id"
                    )
                )

                create_chat_message(
                    session_id,
                    "user",
                    chat_input,
                )

                history = get_chat_messages(
                    session_id
                )

                prompt = build_gem_prompt(
                    gem,
                    get_knowledge(
                        gem_id
                    ),
                    history,
                    chat_input,
                )

                with st.spinner(
                    "Gemini 思考中..."
                ):

                    response = ask_gemini(
                        prompt
                    )

                create_chat_message(
                    session_id,
                    "assistant",
                    response,
                )

                st.rerun()


# ============================================================
# 編輯 GEM 頁面
# ============================================================

def page_edit_gem():

    gem_id = (
        st.session_state.selected_gem_id
    )

    gem = get_gem(
        gem_id
    ) if gem_id else None

    if not gem:

        st.warning(
            "尚未選擇 GEM。"
        )

        return

    st.title(
        "✏️ 編輯 GEM"
    )

    name = st.text_input(
        "名稱",
        value=gem.get(
            "name",
            "",
        ),
    )

    role = st.text_area(
        "角色",
        value=gem.get(
            "role",
            "",
        ),
        height=120,
    )

    workflow = st.text_area(
        "工作流程與規則",
        value=gem.get(
            "workflow",
            "",
        ),
        height=250,
    )

    greeting = st.text_area(
        "開場白",
        value=gem.get(
            "greeting",
            "",
        ),
        height=120,
    )

    category = st.text_input(
        "分類",
        value=gem.get(
            "category",
            "",
        ),
    )

    tags = st.text_input(
        "標籤",
        value=gem.get(
            "tags",
            "",
        ),
    )

    if st.button(
        "💾 儲存",
        use_container_width=True,
    ):

        ok, error = update_gem(
            gem_id,
            {
                "name": name,
                "role": role,
                "workflow": workflow,
                "greeting": greeting,
                "category": category,
                "tags": tags,
            },
        )

        if ok:

            st.success(
                "儲存成功。"
            )

            time.sleep(.4)

            st.session_state.page = "GEM 詳情"

            st.rerun()

        else:

            st.error(error)


# ============================================================
# Knowledge Center
# ============================================================

def page_knowledge():

    st.title(
        "📚 Knowledge Center"
    )

    gems = get_gems()

    if not gems:

        st.info(
            "目前沒有 GEM。"
        )

        return

    gem = st.selectbox(
        "選擇 GEM",
        gems,
        format_func=lambda x: x.get(
            "name",
            "未命名",
        ),
    )

    gem_id = gem.get(
        "id"
    )

    knowledge = get_knowledge(
        gem_id
    )

    st.metric(
        "Knowledge 數量",
        len(knowledge),
    )

    for item in knowledge:

        with st.expander(
            item.get(
                "title",
                "未命名",
            )
        ):

            st.write(
                item.get(
                    "content",
                    "",
                )
            )


# ============================================================
# Chat Center
# ============================================================

def page_chat_center():

    st.title(
        "💬 Chat Center"
    )

    gems = get_gems()

    if not gems:

        st.info(
            "目前沒有 GEM。"
        )

        return

    gem = st.selectbox(
        "選擇 GEM",
        gems,
        format_func=lambda x: x.get(
            "name",
            "未命名",
        ),
    )

    st.session_state.selected_gem_id = (
        gem.get("id")
    )

    st.info(
        "請進入「GEM 詳情 → Chat」開始對話。"
    )

    if st.button(
        "開啟 GEM Chat",
        use_container_width=True,
    ):

        st.session_state.page = "GEM 詳情"

        st.rerun()


# ============================================================
# Chat History
# ============================================================

def page_chat_history():

    st.title(
        "🕘 Chat History"
    )

    sessions = get_chat_sessions()

    if not sessions:

        st.info(
            "目前沒有聊天紀錄。"
        )

        return

    for session in sessions:

        with st.expander(
            session.get(
                "title",
                "未命名對話",
            )
        ):

            messages = get_chat_messages(
                session.get(
                    "id"
                )
            )

            for message in messages:

                role = message.get(
                    "role",
                    "",
                )

                label = (
                    "使用者"
                    if role == "user"
                    else "GEM"
                )

                st.markdown(
                    f"**{label}**"
                )

                st.write(
                    message.get(
                        "content",
                        "",
                    )
                )

                st.divider()


# ============================================================
# Gemini Auto Generator
# ============================================================

def page_gemini_generator():

    st.title(
        "🤖 Gemini GEM 自動生成器"
    )

    st.write(
        "描述你想建立什麼樣的 GEM，"
        "讓 Gemini 自動產生初始版本。"
    )

    description = st.text_area(
        "你想建立什麼 GEM？",
        height=180,
        placeholder=(
            "例如：\n"
            "我想建立一個青年職涯探索陪談 GEM，"
            "使用 MBTI、SFBT 與提問技巧協助 20 多歲青年。"
        ),
    )

    if st.button(
        "✨ 產生 GEM",
        use_container_width=True,
    ):

        if not description.strip():

            st.warning(
                "請先輸入需求。"
            )

        else:

            prompt = f"""
請幫我設計一個 AI GEM。

使用者需求：
{description}

請使用繁體中文。

請輸出：

GEM 名稱：
角色：
工作流程與規則：
開場白：
"""

            with st.spinner(
                "Gemini 正在設計 GEM..."
            ):

                result = ask_gemini(
                    prompt
                )

            st.session_state.generator_result = (
                result
            )

    if st.session_state.generator_result:

        st.divider()

        st.subheader(
            "生成結果"
        )

        st.markdown(
            st.session_state.generator_result
        )


# ============================================================
# 匯入
# ============================================================

def page_import():

    st.title(
        "📥 GEM 匯入"
    )

    uploaded = st.file_uploader(
        "上傳 GEM JSON",
        type=["json"],
    )

    if not uploaded:
        return

    try:

        data = json.loads(
            uploaded.read().decode(
                "utf-8"
            )
        )

    except Exception as error:

        st.error(
            "JSON 解析失敗："
            + safe_error_text(error)
        )

        return

    gem_data = data.get(
        "gem",
        data,
    )

    knowledge_data = data.get(
        "knowledge",
        [],
    )

    st.subheader(
        "匯入預覽"
    )

    st.json(
        data
    )

    if st.button(
        "🚀 匯入 GEM",
        use_container_width=True,
    ):

        gem, error = create_gem(
            name=gem_data.get(
                "name",
                "匯入 GEM",
            ),
            role=gem_data.get(
                "role",
                "",
            ),
            workflow=gem_data.get(
                "workflow",
                "",
            ),
            greeting=gem_data.get(
                "greeting",
                "",
            ),
            category=gem_data.get(
                "category",
                "匯入",
            ),
            tags=gem_data.get(
                "tags",
                "",
            ),
        )

        if error:

            st.error(error)

            return

        imported_count = 0

        for item in knowledge_data:

            ok, _ = create_knowledge(
                gem.get("id"),
                item.get(
                    "title",
                    "",
                ),
                item.get(
                    "content",
                    "",
                ),
            )

            if ok:
                imported_count += 1

        st.success(
            f"匯入成功！Knowledge：{imported_count} 筆"
        )


# ============================================================
# GEM Templates
# ============================================================

TEMPLATES = {
    "青年職涯探索夥伴": {
        "role": (
            "協助青年探索職涯方向的 AI 陪談夥伴。"
            "透過提問、整理與反思協助使用者釐清方向。"
        ),
        "workflow": (
            "1. 先理解使用者目前狀態。\n"
            "2. 使用開放式問題探索。\n"
            "3. 整理使用者提到的線索。\n"
            "4. 避免直接替使用者決定人生。\n"
            "5. 協助形成下一個小步驟。"
        ),
        "greeting": (
            "你好，我是你的職涯探索夥伴。"
            "我們可以一起慢慢釐清你現在的方向。"
        ),
    },

    "SFBT 陪談夥伴": {
        "role": (
            "使用焦點解決短期治療概念協助使用者"
            "探索例外、資源、目標與下一小步。"
        ),
        "workflow": (
            "1. 理解目前困擾。\n"
            "2. 探索例外經驗。\n"
            "3. 探索已存在的能力與資源。\n"
            "4. 使用量尺問題。\n"
            "5. 找到可執行的小步驟。"
        ),
        "greeting": (
            "最近有什麼事情，讓你特別想找人談談呢？"
        ),
    },

    "MBTI 職涯探索夥伴": {
        "role": (
            "協助使用者理解 MBTI 偏好，"
            "並將 MBTI 與興趣、能力、價值觀及經驗一起探索。"
        ),
        "workflow": (
            "MBTI → 偏好\n"
            "興趣 → 喜歡什麼\n"
            "能力 → 能做什麼\n"
            "價值觀 → 什麼重要\n"
            "經驗 → 過去發生什麼\n"
            "SFBT → 下一步做什麼"
        ),
        "greeting": (
            "我們可以先從你最近對工作或未來的想法開始。"
        ),
    },
}


def page_templates():

    st.title(
        "🧰 GEM 模板"
    )

    template_name = st.selectbox(
        "選擇模板",
        list(
            TEMPLATES.keys()
        ),
    )

    template = TEMPLATES[
        template_name
    ]

    st.subheader(
        template_name
    )

    st.text_area(
        "角色",
        value=template["role"],
        height=140,
        disabled=True,
    )

    st.text_area(
        "工作流程",
        value=template["workflow"],
        height=220,
        disabled=True,
    )

    st.text_area(
        "開場白",
        value=template["greeting"],
        height=120,
        disabled=True,
    )

    if st.button(
        "➕ 使用這個模板建立 GEM",
        use_container_width=True,
    ):

        gem, error = create_gem(
            name=template_name,
            role=template["role"],
            workflow=template["workflow"],
            greeting=template["greeting"],
            category="模板",
            tags="GEM Template",
        )

        if error:

            st.error(error)

        else:

            st.success(
                "模板 GEM 建立成功！"
            )

            st.session_state.selected_gem_id = (
                gem.get("id")
            )

            st.session_state.page = "GEM 詳情"

            st.rerun()


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.title(
        "☁️ GEM Builder"
    )

    st.caption(
        "Day 32-C"
    )

    st.divider()

    # --------------------------------------------------------
    # Gemini
    # --------------------------------------------------------

    st.subheader(
        "🤖 Gemini"
    )

    available_models = (
        st.session_state.available_models
    )

    if available_models:

        current_model = (
            st.session_state.selected_model
        )

        if current_model not in available_models:
            current_model = available_models[0]

        current_index = available_models.index(
            current_model
        )

        selected_model = st.selectbox(
            "目前模型",
            available_models,
            index=current_index,
            format_func=lambda x:
                MODEL_DISPLAY_NAMES.get(
                    x,
                    x,
                ),
            key="sidebar_model_select",
        )

        st.session_state.selected_model = (
            selected_model
        )

        st.success(
            "🟢 Gemini 已連線"
        )

        st.caption(
            "目前："
            + MODEL_DISPLAY_NAMES.get(
                selected_model,
                selected_model,
            )
        )

    else:

        st.error(
            "🔴 Gemini 未連線"
        )

    if st.button(
        "🔄 重新偵測 Gemini 模型",
        use_container_width=True,
    ):

        st.session_state.available_models = []
        st.session_state.selected_model = None
        st.session_state.model_error = ""

        load_gemini_models(
            force=True
        )

        st.rerun()

    if (
        st.session_state.model_error
        and not available_models
    ):

        with st.expander(
            "🔎 Gemini 診斷"
        ):

            st.code(
                st.session_state.model_error
            )

    st.divider()

    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------

    st.subheader(
        "🧭 導覽"
    )

    navigation = st.radio(
        "頁面",
        [
            "首頁",
            "建立 GEM",
            "工作區",
            "Knowledge",
            "Chat Center",
            "Chat History",
            "Gemini Generator",
            "匯入",
            "模板",
        ],
        key="main_navigation",
    )

    page = navigation

    # --------------------------------------------------------
    # GEM
    # --------------------------------------------------------

    if st.session_state.selected_gem_id:

        st.divider()

        st.subheader(
            "🧩 目前 GEM"
        )

        selected_gem = get_gem(
            st.session_state.selected_gem_id
        )

        if selected_gem:

            st.caption(
                selected_gem.get(
                    "name",
                    "",
                )
            )

            if st.button(
                "🧩 開啟目前 GEM",
                use_container_width=True,
            ):

                st.session_state.page = "GEM 詳情"

                st.rerun()

            if st.button(
                "✏️ 編輯目前 GEM",
                use_container_width=True,
            ):

                st.session_state.page = "編輯 GEM"

                st.rerun()

    st.divider()

    st.caption(
        "Supabase："
        + (
            "🟢 已連線"
            if supabase is not None
            else "🔴 未連線"
        )
    )

    st.caption(
        "更新："
        + datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )


# ============================================================
# Main Router
# ============================================================

if page == "首頁":

    page_home()

elif page == "建立 GEM":

    page_create_gem()

elif page == "工作區":

    page_workspace()

elif page == "Knowledge":

    page_knowledge()

elif page == "Chat Center":

    page_chat_center()

elif page == "Chat History":

    page_chat_history()

elif page == "Gemini Generator":

    page_gemini_generator()

elif page == "匯入":

    page_import()

elif page == "模板":

    page_templates()

elif page == "GEM 詳情":

    page_gem_detail()

elif page == "編輯 GEM":

    page_edit_gem()

else:

    page_home()


# ============================================================
# Footer
# ============================================================

st.divider()

st.caption(
    "☁️ GEM Builder Cloud｜Day 32-C｜Gemini 穩定版"
)
