import json
import re
import time
from datetime import datetime

import streamlit as st
from supabase import create_client
from google import genai


# =========================================================
# 1. Page
# =========================================================

st.set_page_config(
    page_title="GEM Builder Cloud",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# 2. Responsive CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    h1 {
        font-size: 2.2rem;
    }

    h2 {
        font-size: 1.7rem;
    }

    h3 {
        font-size: 1.35rem;
    }

    .stButton button,
    .stDownloadButton button {
        width: 100%;
        min-height: 44px;
        border-radius: 10px;
    }

    textarea,
    input {
        border-radius: 10px !important;
    }

    .gem-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }

    .info-card {
        border: 1px solid rgba(128,128,128,0.20);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 15px;
    }

    .model-card {
        border: 1px solid rgba(128,128,128,0.22);
        border-radius: 12px;
        padding: 12px 15px;
        margin-bottom: 8px;
    }

    .small-text {
        font-size: 0.85rem;
        opacity: 0.75;
    }

    @media (max-width: 768px) {

        .block-container {
            padding-top: 0.8rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        h1 {
            font-size: 1.7rem;
        }

        h2 {
            font-size: 1.4rem;
        }

        h3 {
            font-size: 1.15rem;
        }

        .stButton button,
        .stDownloadButton button {
            min-height: 48px;
            font-size: 1rem;
        }

        .gem-card,
        .info-card {
            padding: 14px;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. Secrets
# =========================================================

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error("❌ 無法讀取 Streamlit Secrets。")
    st.code(str(e))
    st.stop()


# =========================================================
# 4. Supabase
# =========================================================

try:
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )
except Exception as e:
    st.error("❌ Supabase 連線失敗")
    st.code(str(e))
    st.stop()


# =========================================================
# 5. Table names
# =========================================================

GEM_TABLE = "gems"
KNOWLEDGE_TABLE = "gem_knowledge"
CHAT_SESSION_TABLE = "gem_chat_sessions"
CHAT_MESSAGE_TABLE = "gem_chat_messages"
CLOUD_TEST_TABLE = "cloud_test"


# =========================================================
# 6. Session state
# =========================================================

defaults = {
    "page": "首頁",
    "selected_gem_id": None,
    "selected_chat_session_id": None,
    "gemini_result": "",
    "optimizer_result": "",
    "delete_confirm": False,
    "available_models": [],
    "selected_model": None,
    "model_error": "",
    "workspace_search": "",
    "optimization_preview": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 7. Gemini client
# =========================================================

def get_gemini_client():
    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# 8. Gemini model filtering
# =========================================================

def model_name_clean(name):
    """
    將 models/gemini-xxx 轉成 gemini-xxx
    """
    if not name:
        return ""

    name = str(name).strip()

    if name.startswith("models/"):
        name = name[7:]

    return name


def is_special_model(model_name):
    """
    排除不適合 GEM Builder 一般文字任務的模型。
    """

    name = model_name.lower()

    excluded_keywords = [
        "embedding",
        "imagen",
        "image",
        "robotics",
        "robot",
        "live",
        "audio",
        "tts",
        "speech",
        "transcribe",
        "veo",
    ]

    for keyword in excluded_keywords:
        if keyword in name:
            return True

    return False


def model_supports_generate_content(model):
    """
    嘗試確認模型是否支援 generateContent。
    """

    try:
        actions = getattr(model, "supported_actions", None)

        if actions:
            actions_text = " ".join(
                str(x).lower()
                for x in actions
            )

            if (
                "generatecontent" not in actions_text
                and "generate_content" not in actions_text
            ):
                return False

    except Exception:
        pass

    return True


def model_family(model_name):
    """
    將模型分類成：

    1 = Flash-Lite
    2 = Flash
    3 = Pro
    99 = 其他
    """

    name = model_name.lower()

    if "flash-lite" in name or "flash_lite" in name:
        return 1

    if "flash" in name:
        return 2

    if "pro" in name:
        return 3

    return 99


def version_numbers(model_name):
    """
    取得模型名稱裡的數字版本。

    例如：

    gemini-2.5-flash
    → [2, 5]

    gemini-3-pro
    → [3]
    """

    nums = re.findall(
        r"\d+(?:\.\d+)?",
        model_name
    )

    result = []

    for n in nums:
        try:
            if "." in n:
                result.append(float(n))
            else:
                result.append(float(n))
        except Exception:
            pass

    return result


def model_sort_key(model_name):
    """
    模型排序：

    Flash-Lite
    Flash
    Pro

    同類型內：
    新版本優先
    """

    family = model_family(model_name)

    versions = version_numbers(model_name)

    version_value = 0

    if versions:
        if len(versions) >= 2:
            version_value = versions[0] * 100 + versions[1]
        else:
            version_value = versions[0] * 100

    return (
        family,
        -version_value,
        model_name
    )


def get_primary_gemini_models(all_models):
    """
    從 Google 回傳的大量 Gemini 模型中，
    只挑出 GEM Builder 的主要模型。

    最終最多：

    1 個 Flash-Lite
    1 個 Flash
    1 個 Pro

    如果其中某一類不存在，就不顯示。
    """

    clean_models = []

    for model in all_models:

        name = model_name_clean(
            getattr(model, "name", "")
        )

        if not name:
            continue

        if not name.lower().startswith("gemini"):
            continue

        if is_special_model(name):
            continue

        if not model_supports_generate_content(model):
            continue

        clean_models.append(name)

    # 去除重複
    clean_models = list(dict.fromkeys(clean_models))

    flash_lite = []
    flash = []
    pro = []

    for name in clean_models:

        family = model_family(name)

        if family == 1:
            flash_lite.append(name)

        elif family == 2:
            flash.append(name)

        elif family == 3:
            pro.append(name)

    flash_lite.sort(key=model_sort_key)
    flash.sort(key=model_sort_key)
    pro.sort(key=model_sort_key)

    selected = []

    if flash_lite:
        selected.append(flash_lite[0])

    if flash:
        selected.append(flash[0])

    if pro:
        selected.append(pro[0])

    return selected


def load_gemini_models(force=False):

    if (
        st.session_state.available_models
        and not force
    ):
        return st.session_state.available_models

    try:

        client = get_gemini_client()

        raw_models = list(
            client.models.list()
        )

        primary_models = get_primary_gemini_models(
            raw_models
        )

        st.session_state.available_models = (
            primary_models
        )

        st.session_state.model_error = ""

        # -------------------------------------------------
        # 預設模型
        # 優先順序：
        # Flash → Flash-Lite → Pro
        # -------------------------------------------------

        preferred = None

        for model in primary_models:
            if model_family(model) == 2:
                preferred = model
                break

        if not preferred:
            for model in primary_models:
                if model_family(model) == 1:
                    preferred = model
                    break

        if not preferred and primary_models:
            preferred = primary_models[0]

        if (
            st.session_state.selected_model
            not in primary_models
        ):
            st.session_state.selected_model = preferred

        return primary_models

    except Exception as e:

        st.session_state.available_models = []
        st.session_state.model_error = str(e)

        return []


# =========================================================
# 9. Gemini model candidates / fallback
# =========================================================

def get_model_candidates():

    models = st.session_state.available_models

    selected = st.session_state.selected_model

    candidates = []

    if selected and selected in models:
        candidates.append(selected)

    for model in models:
        if model not in candidates:
            candidates.append(model)

    return candidates


# =========================================================
# 10. Gemini API
# =========================================================

def is_retryable_error(error_text):

    text = str(error_text).upper()

    retry_words = [
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "TIMEOUT",
        "DEADLINE",
        "OVERLOADED",
    ]

    return any(
        word in text
        for word in retry_words
    )


def ask_gemini(
    prompt,
    max_retry=2
):

    candidates = get_model_candidates()

    if not candidates:
        load_gemini_models(force=True)
        candidates = get_model_candidates()

    if not candidates:
        return (
            "❌ 目前沒有可使用的 Gemini 模型。\n\n"
            "請到側邊欄重新整理 Gemini 模型。"
        )

    errors = []

    for model in candidates:

        for attempt in range(
            max_retry + 1
        ):

            try:

                client = get_gemini_client()

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                text = getattr(
                    response,
                    "text",
                    None
                )

                if text:

                    st.session_state.selected_model = model

                    return text

                return (
                    "⚠️ Gemini 沒有返回文字內容。"
                )

            except Exception as e:

                error_text = str(e)

                errors.append(
                    f"{model}: {error_text}"
                )

                if (
                    not is_retryable_error(
                        error_text
                    )
                ):
                    break

                if attempt < max_retry:
                    time.sleep(
                        1.5 * (attempt + 1)
                    )

    return (
        "❌ Gemini 呼叫失敗\n\n"
        + "\n\n".join(errors)
    )


# =========================================================
# 11. GEM CRUD
# =========================================================

def get_gems():

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"❌ 讀取 GEM 失敗：{e}"
        )

        return []


def get_gem(gem_id):

    if not gem_id:
        return None

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .select("*")
            .eq("id", gem_id)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as e:

        st.error(
            f"❌ 讀取 GEM 失敗：{e}"
        )

    return None


def create_gem(
    name,
    description,
    role,
    workflow,
    greeting
):

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .insert({
                "name": name,
                "description": description,
                "role": role,
                "workflow": workflow,
                "greeting": greeting,
            })
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"❌ 建立 GEM 失敗：{e}"
        )

        return None


def update_gem(
    gem_id,
    name,
    description,
    role,
    workflow,
    greeting
):

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .update({
                "name": name,
                "description": description,
                "role": role,
                "workflow": workflow,
                "greeting": greeting,
            })
            .eq("id", gem_id)
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"❌ 更新 GEM 失敗：{e}"
        )

        return None


def delete_gem(gem_id):

    try:

        (
            supabase
            .table(GEM_TABLE)
            .delete()
            .eq("id", gem_id)
            .execute()
        )

        return True

    except Exception as e:

        st.error(
            f"❌ 刪除 GEM 失敗：{e}"
        )

        return False


# =========================================================
# 12. Knowledge
# =========================================================

def get_knowledge(gem_id):

    if not gem_id:
        return []

    try:

        response = (
            supabase
            .table(KNOWLEDGE_TABLE)
            .select("*")
            .eq("gem_id", gem_id)
            .order("id", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"❌ 讀取 Knowledge 失敗：{e}"
        )

        return []


def create_knowledge(
    gem_id,
    title,
    content
):

    try:

        response = (
            supabase
            .table(KNOWLEDGE_TABLE)
            .insert({
                "gem_id": gem_id,
                "title": title,
                "content": content,
            })
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"❌ 新增 Knowledge 失敗：{e}"
        )

        return None


def update_knowledge(
    knowledge_id,
    title,
    content
):

    try:

        response = (
            supabase
            .table(KNOWLEDGE_TABLE)
            .update({
                "title": title,
                "content": content,
            })
            .eq("id", knowledge_id)
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"❌ 更新 Knowledge 失敗：{e}"
        )

        return None


def delete_knowledge(
    knowledge_id
):

    try:

        (
            supabase
            .table(KNOWLEDGE_TABLE)
            .delete()
            .eq("id", knowledge_id)
            .execute()
        )

        return True

    except Exception as e:

        st.error(
            f"❌ 刪除 Knowledge 失敗：{e}"
        )

        return False


# =========================================================
# 13. Chat sessions
# =========================================================

def get_chat_sessions():

    try:

        response = (
            supabase
            .table(CHAT_SESSION_TABLE)
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"❌ 讀取對話紀錄失敗：{e}"
        )

        return []


def get_chat_sessions_by_gem(
    gem_id
):

    if not gem_id:
        return []

    try:

        response = (
            supabase
            .table(CHAT_SESSION_TABLE)
            .select("*")
            .eq("gem_id", gem_id)
            .order("id", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"❌ 讀取 GEM 對話紀錄失敗：{e}"
        )

        return []


def create_chat_session(
    gem_id,
    title="新對話"
):

    try:

        response = (
            supabase
            .table(CHAT_SESSION_TABLE)
            .insert({
                "gem_id": gem_id,
                "title": title,
            })
            .execute()
        )

        if response.data:
            return response.data[0]

    except Exception as e:

        st.error(
            f"❌ 建立對話失敗：{e}"
        )

    return None


def delete_chat_session(
    session_id
):

    try:

        (
            supabase
            .table(CHAT_MESSAGE_TABLE)
            .delete()
            .eq("chat_id", session_id)
            .execute()
        )

        (
            supabase
            .table(CHAT_SESSION_TABLE)
            .delete()
            .eq("id", session_id)
            .execute()
        )

        return True

    except Exception as e:

        st.error(
            f"❌ 刪除對話失敗：{e}"
        )

        return False


# =========================================================
# 14. Chat messages
# =========================================================

def get_chat_messages(
    chat_id
):

    if not chat_id:
        return []

    try:

        response = (
            supabase
            .table(CHAT_MESSAGE_TABLE)
            .select("*")
            .eq("chat_id", chat_id)
            .order("created_at", desc=False)
            .execute()
        )

        return response.data or []

    except Exception as e:

        st.error(
            f"❌ 讀取訊息失敗：{e}"
        )

        return []


def create_chat_message(
    chat_id,
    role,
    content
):

    try:

        response = (
            supabase
            .table(CHAT_MESSAGE_TABLE)
            .insert({
                "chat_id": chat_id,
                "role": role,
                "content": content,
            })
            .execute()
        )

        return response.data

    except Exception as e:

        st.error(
            f"❌ 儲存訊息失敗：{e}"
        )

        return None


# =========================================================
# 15. Export
# =========================================================

def gem_to_txt(gem):

    if not gem:
        return ""

    knowledge = get_knowledge(
        gem.get("id")
    )

    text = []

    text.append(
        f"# {gem.get('name', '')}"
    )

    text.append("")

    text.append(
        "## Description"
    )

    text.append(
        gem.get("description", "")
    )

    text.append("")

    text.append("## Role")

    text.append(
        gem.get("role", "")
    )

    text.append("")

    text.append("## Workflow")

    text.append(
        gem.get("workflow", "")
    )

    text.append("")

    text.append("## Greeting")

    text.append(
        gem.get("greeting", "")
    )

    text.append("")

    text.append("## Knowledge")

    for item in knowledge:

        text.append(
            f"### {item.get('title', '')}"
        )

        text.append(
            item.get("content", "")
        )

        text.append("")

    return "\n".join(text)


def gem_to_json(gem):

    if not gem:
        return {}

    knowledge = get_knowledge(
        gem.get("id")
    )

    result = dict(gem)

    result["knowledge"] = knowledge

    return result


def gem_backup_json():

    gems = get_gems()

    backup = []

    for gem in gems:
        backup.append(
            gem_to_json(gem)
        )

    return json.dumps(
        backup,
        ensure_ascii=False,
        indent=2,
        default=str
    )


# =========================================================
# 16. Prompt builder
# =========================================================

def build_gem_prompt(
    gem,
    user_message=""
):

    if not gem:
        return ""

    knowledge = get_knowledge(
        gem.get("id")
    )

    knowledge_text = ""

    for item in knowledge:

        knowledge_text += (
            f"\n\n### {item.get('title', '')}\n"
            f"{item.get('content', '')}"
        )

    prompt = f"""
你現在是以下 GEM：

名稱：
{gem.get('name', '')}

Description：
{gem.get('description', '')}

Role：
{gem.get('role', '')}

Workflow：
{gem.get('workflow', '')}

Greeting：
{gem.get('greeting', '')}

Knowledge：
{knowledge_text}

請嚴格依照上述 GEM 的角色、流程與 Knowledge 回答使用者。

使用者訊息：
{user_message}
"""

    return prompt.strip()


# =========================================================
# 17. Dashboard stats
# =========================================================

def get_dashboard_stats():

    gems = get_gems()

    sessions = get_chat_sessions()

    return {
        "gems": len(gems),
        "sessions": len(sessions),
    }


# =========================================================
# 18. JSON extraction
# =========================================================

def extract_json_from_text(text):

    if not text:
        return None

    text = text.strip()

    # 去除 markdown code fence
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:

        return json.loads(text)

    except Exception:
        pass

    # 找第一個 { 到最後一個 }
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:

        try:

            return json.loads(
                text[start:end + 1]
            )

        except Exception:
            pass

    return None


# =========================================================
# 19. Normalize optimization result
# =========================================================

def normalize_optimization_result(
    result
):

    if not isinstance(result, dict):
        return None

    fields = [
        "problem_analysis",
        "optimized_role",
        "optimized_workflow",
        "optimized_greeting",
        "knowledge_suggestions",
        "overall_suggestions",
    ]

    normalized = {}

    for field in fields:

        value = result.get(
            field,
            ""
        )

        if isinstance(value, list):
            value = "\n".join(
                str(x)
                for x in value
            )

        if value is None:
            value = ""

        normalized[field] = str(value)

    return normalized


# =========================================================
# 20. AI optimization
# =========================================================

def optimize_gem(gem):

    if not gem:
        return None

    knowledge = get_knowledge(
        gem.get("id")
    )

    knowledge_text = ""

    for item in knowledge:

        knowledge_text += (
            f"\n\n標題：{item.get('title', '')}\n"
            f"內容：{item.get('content', '')}"
        )

    prompt = f"""
你是一位專業的 GEM Prompt 架構設計師。

請分析以下 GEM，找出角色定位、流程、
Greeting 與 Knowledge 可以改善的地方。

GEM 名稱：
{gem.get('name', '')}

Description：
{gem.get('description', '')}

Role：
{gem.get('role', '')}

Workflow：
{gem.get('workflow', '')}

Greeting：
{gem.get('greeting', '')}

Knowledge：
{knowledge_text}

請完成以下工作：

1. 分析目前 GEM 的主要問題
2. 優化 Role
3. 優化 Workflow
4. 優化 Greeting
5. 提出 Knowledge 建議
6. 提出整體改善建議

非常重要：

只輸出合法 JSON。

JSON 格式必須完全符合：

{{
  "problem_analysis": "...",
  "optimized_role": "...",
  "optimized_workflow": "...",
  "optimized_greeting": "...",
  "knowledge_suggestions": "...",
  "overall_suggestions": "..."
}}

不要輸出 Markdown。
不要輸出 ```json。
不要加入 JSON 以外的說明。
"""

    result_text = ask_gemini(
        prompt
    )

    result = extract_json_from_text(
        result_text
    )

    if result is None:

        return {
            "problem_analysis":
                "Gemini 沒有返回可解析的 JSON。",
            "optimized_role": "",
            "optimized_workflow": "",
            "optimized_greeting": "",
            "knowledge_suggestions": "",
            "overall_suggestions":
                result_text,
        }

    return normalize_optimization_result(
        result
    )


# =========================================================
# 21. Apply optimization
# =========================================================

def apply_optimization(
    gem,
    optimization
):

    if not gem or not optimization:
        return False

    try:

        response = (
            supabase
            .table(GEM_TABLE)
            .update({
                "role": optimization.get(
                    "optimized_role",
                    gem.get("role", "")
                ),
                "workflow": optimization.get(
                    "optimized_workflow",
                    gem.get("workflow", "")
                ),
                "greeting": optimization.get(
                    "optimized_greeting",
                    gem.get("greeting", "")
                ),
            })
            .eq(
                "id",
                gem.get("id")
            )
            .execute()
        )

        return bool(response.data)

    except Exception as e:

        st.error(
            f"❌ 套用優化失敗：{e}"
        )

        return False


# =========================================================
# 22. Sidebar model management
# =========================================================

def show_model_management():

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "🤖 Gemini 模型"
    )

    models = load_gemini_models()

    if st.session_state.model_error:

        st.sidebar.warning(
            "⚠️ 模型讀取發生問題"
        )

    if not models:

        st.sidebar.error(
            "目前沒有偵測到可用 Gemini 模型"
        )

        if st.sidebar.button(
            "🔄 重新偵測模型",
            key="reload_models_empty"
        ):

            load_gemini_models(
                force=True
            )

            st.rerun()

        return

    # -----------------------------------------------------
    # 模型顯示名稱
    # -----------------------------------------------------

    def display_model_name(model):

        name = model.lower()

        if "flash-lite" in name:
            return f"⚡ Flash-Lite  ·  {model}"

        if "flash" in name:
            return f"🚀 Flash  ·  {model}"

        if "pro" in name:
            return f"🧠 Pro  ·  {model}"

        return model

    options = models

    current = st.session_state.selected_model

    if current not in options:
        current = options[0]

    selected = st.sidebar.selectbox(
        "主要模型",
        options=options,
        index=options.index(current),
        format_func=display_model_name,
        key="model_selector",
    )

    if selected != st.session_state.selected_model:

        st.session_state.selected_model = selected

    st.sidebar.caption(
        f"目前使用：{selected}"
    )

    st.sidebar.caption(
        "已自動篩選主要 Gemini 模型"
    )

    if st.sidebar.button(
        "🔄 重新偵測模型",
        key="reload_models"
    ):

        load_gemini_models(
            force=True
        )

        st.rerun()


# =========================================================
# 23. Header
# =========================================================

def show_header():

    col1, col2 = st.columns(
        [4, 1]
    )

    with col1:

        st.title(
            "☁️ GEM Builder Cloud"
        )

        st.caption(
            "Day 32-A｜主要 Gemini 模型管理版"
        )

    with col2:

        if st.session_state.selected_model:

            st.metric(
                "AI 模型",
                model_family(
                    st.session_state.selected_model
                ) == 1
                and "Flash-Lite"
                or model_family(
                    st.session_state.selected_model
                ) == 2
                and "Flash"
                or model_family(
                    st.session_state.selected_model
                ) == 3
                and "Pro"
                or "Gemini"
            )


# =========================================================
# 24. Home
# =========================================================

def show_home():

    show_header()

    stats = get_dashboard_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "GEM 數量",
            stats["gems"]
        )

    with col2:
        st.metric(
            "對話數",
            stats["sessions"]
        )

    with col3:
        st.metric(
            "主要模型",
            len(
                st.session_state.available_models
            )
        )

    st.markdown("---")

    st.subheader(
        "🚀 GEM Builder Cloud"
    )

    st.write(
        "建立、管理、測試與優化你的 AI GEM。"
    )

    st.info(
        "目前版本已限制模型選單只顯示主要 "
        "Flash-Lite、Flash、Pro 模型。"
    )

    gems = get_gems()

    if not gems:

        st.info(
            "目前還沒有 GEM。"
        )

        if st.button(
            "＋ 建立第一個 GEM"
        ):

            st.session_state.page = "建立 GEM"
            st.rerun()

        return

    st.subheader(
        "📦 最近 GEM"
    )

    for gem in gems[:6]:

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {gem.get('name', '未命名 GEM')}"
            )

            st.write(
                gem.get(
                    "description",
                    ""
                )
            )

            if st.button(
                "開啟 GEM",
                key=f"home_open_{gem.get('id')}"
            ):

                st.session_state.selected_gem_id = (
                    gem.get("id")
                )

                st.session_state.page = (
                    "GEM 詳細"
                )

                st.rerun()


# =========================================================
# 25. Create GEM
# =========================================================

def show_create_gem():

    show_header()

    st.header(
        "＋ 建立 GEM"
    )

    name = st.text_input(
        "GEM 名稱"
    )

    description = st.text_area(
        "Description",
        height=120
    )

    role = st.text_area(
        "Role",
        height=220
    )

    workflow = st.text_area(
        "Workflow",
        height=220
    )

    greeting = st.text_area(
        "Greeting",
        height=150
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "💾 建立 GEM",
            type="primary"
        ):

            if not name.strip():

                st.error(
                    "請輸入 GEM 名稱。"
                )

            else:

                result = create_gem(
                    name,
                    description,
                    role,
                    workflow,
                    greeting
                )

                if result:

                    st.success(
                        "✅ GEM 建立成功"
                    )

                    gem_id = (
                        result[0].get("id")
                        if result
                        else None
                    )

                    st.session_state.selected_gem_id = (
                        gem_id
                    )

                    st.session_state.page = (
                        "GEM 詳細"
                    )

                    st.rerun()

    with col2:

        if st.button(
            "取消"
        ):

            st.session_state.page = "首頁"
            st.rerun()


# =========================================================
# 26. Workspace
# =========================================================

def show_workspace():

    show_header()

    st.header(
        "🗂️ GEM 工作區"
    )

    search = st.text_input(
        "搜尋 GEM",
        value=st.session_state.workspace_search
    )

    st.session_state.workspace_search = search

    gems = get_gems()

    if search.strip():

        keyword = search.lower()

        gems = [
            gem
            for gem in gems
            if keyword in str(
                gem.get("name", "")
            ).lower()
            or keyword in str(
                gem.get("description", "")
            ).lower()
        ]

    if not gems:

        st.info(
            "找不到符合條件的 GEM。"
        )

        return

    for gem in gems:

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {gem.get('name', '未命名')}"
            )

            st.caption(
                gem.get(
                    "description",
                    ""
                )
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "開啟",
                    key=f"workspace_open_{gem.get('id')}"
                ):

                    st.session_state.selected_gem_id = (
                        gem.get("id")
                    )

                    st.session_state.page = (
                        "GEM 詳細"
                    )

                    st.rerun()

            with col2:

                if st.button(
                    "🗑️ 刪除",
                    key=f"workspace_delete_{gem.get('id')}"
                ):

                    st.session_state.selected_gem_id = (
                        gem.get("id")
                    )

                    st.session_state.delete_confirm = True

                    st.rerun()

    if st.session_state.delete_confirm:

        gem = get_gem(
            st.session_state.selected_gem_id
        )

        if gem:

            st.warning(
                f"確定要刪除「{gem.get('name', '')}」嗎？"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "確定刪除",
                    type="primary",
                    key="confirm_delete"
                ):

                    if delete_gem(
                        gem.get("id")
                    ):

                        st.session_state.delete_confirm = False
                        st.session_state.selected_gem_id = None

                        st.success(
                            "GEM 已刪除。"
                        )

                        st.rerun()

            with col2:

                if st.button(
                    "取消",
                    key="cancel_delete"
                ):

                    st.session_state.delete_confirm = False
                    st.rerun()


# =========================================================
# 27. GEM detail
# =========================================================

def show_gem_detail():

    gem = get_gem(
        st.session_state.selected_gem_id
    )

    if not gem:

        st.error(
            "❌ 找不到 GEM。"
        )

        return

    st.header(
        f"🧩 {gem.get('name', 'GEM')}"
    )

    st.caption(
        gem.get(
            "description",
            ""
        )
    )

    tabs = st.tabs([
        "📋 內容",
        "✏️ 編輯",
        "📚 Knowledge",
        "✨ AI 優化",
        "🧪 測試",
        "💬 對話",
    ])

    # =====================================================
    # Tab 1 Content
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
            key=f"view_role_{gem.get('id')}"
        )

        st.subheader(
            "Workflow"
        )

        st.text_area(
            "Workflow",
            value=gem.get(
                "workflow",
                ""
            ),
            height=220,
            disabled=True,
            key=f"view_workflow_{gem.get('id')}"
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
            height=150,
            disabled=True,
            key=f"view_greeting_{gem.get('id')}"
        )

        st.download_button(
            "⬇️ 匯出 TXT",
            data=gem_to_txt(gem),
            file_name=f"{gem.get('name', 'gem')}.txt",
            mime="text/plain",
            key=f"download_txt_{gem.get('id')}"
        )

        st.download_button(
            "⬇️ 匯出 JSON",
            data=json.dumps(
                gem_to_json(gem),
                ensure_ascii=False,
                indent=2,
                default=str
            ),
            file_name=f"{gem.get('name', 'gem')}.json",
            mime="application/json",
            key=f"download_json_{gem.get('id')}"
        )

    # =====================================================
    # Tab 2 Edit
    # =====================================================

    with tabs[1]:

        name = st.text_input(
            "GEM 名稱",
            value=gem.get(
                "name",
                ""
            ),
            key=f"edit_name_{gem.get('id')}"
        )

        description = st.text_area(
            "Description",
            value=gem.get(
                "description",
                ""
            ),
            height=120,
            key=f"edit_description_{gem.get('id')}"
        )

        role = st.text_area(
            "Role",
            value=gem.get(
                "role",
                ""
            ),
            height=220,
            key=f"edit_role_{gem.get('id')}"
        )

        workflow = st.text_area(
            "Workflow",
            value=gem.get(
                "workflow",
                ""
            ),
            height=220,
            key=f"edit_workflow_{gem.get('id')}"
        )

        greeting = st.text_area(
            "Greeting",
            value=gem.get(
                "greeting",
                ""
            ),
            height=150,
            key=f"edit_greeting_{gem.get('id')}"
        )

        if st.button(
            "💾 儲存修改",
            type="primary",
            key=f"save_gem_{gem.get('id')}"
        ):

            result = update_gem(
                gem.get("id"),
                name,
                description,
                role,
                workflow,
                greeting
            )

            if result:

                st.success(
                    "✅ GEM 更新成功"
                )

                st.rerun()

    # =====================================================
    # Tab 3 Knowledge
    # =====================================================

    with tabs[2]:

        knowledge = get_knowledge(
            gem.get("id")
        )

        st.subheader(
            "📚 Knowledge"
        )

        with st.expander(
            "＋ 新增 Knowledge",
            expanded=False
        ):

            new_title = st.text_input(
                "標題",
                key=f"new_knowledge_title_{gem.get('id')}"
            )

            new_content = st.text_area(
                "內容",
                height=220,
                key=f"new_knowledge_content_{gem.get('id')}"
            )

            if st.button(
                "新增 Knowledge",
                key=f"add_knowledge_{gem.get('id')}"
            ):

                if not new_title.strip():

                    st.error(
                        "請輸入 Knowledge 標題。"
                    )

                else:

                    result = create_knowledge(
                        gem.get("id"),
                        new_title,
                        new_content
                    )

                    if result:

                        st.success(
                            "✅ Knowledge 新增成功"
                        )

                        st.rerun()

        if not knowledge:

            st.info(
                "目前沒有 Knowledge。"
            )

        for item in knowledge:

            with st.expander(
                f"📄 {item.get('title', 'Knowledge')}"
            ):

                title = st.text_input(
                    "標題",
                    value=item.get(
                        "title",
                        ""
                    ),
                    key=f"knowledge_title_{item.get('id')}"
                )

                content = st.text_area(
                    "內容",
                    value=item.get(
                        "content",
                        ""
                    ),
                    height=220,
                    key=f"knowledge_content_{item.get('id')}"
                )

                col1, col2 = st.columns(2)

                with col1:

                    if st.button(
                        "💾 儲存",
                        key=f"knowledge_save_{item.get('id')}"
                    ):

                        result = update_knowledge(
                            item.get("id"),
                            title,
                            content
                        )

                        if result:

                            st.success(
                                "已儲存"
                            )

                            st.rerun()

                with col2:

                    if st.button(
                        "🗑️ 刪除",
                        key=f"knowledge_delete_{item.get('id')}"
                    ):

                        if delete_knowledge(
                            item.get("id")
                        ):

                            st.success(
                                "已刪除"
                            )

                            st.rerun()

    # =====================================================
    # Tab 4 AI Optimization
    # =====================================================

    with tabs[3]:

        show_gem_ai_optimization(
            gem
        )

    # =====================================================
    # Tab 5 Test
    # =====================================================

    with tabs[4]:

        st.subheader(
            "🧪 測試 GEM"
        )

        user_message = st.text_area(
            "輸入測試問題",
            height=180,
            key=f"test_message_{gem.get('id')}"
        )

        if st.button(
            "🤖 送出測試",
            type="primary",
            key=f"test_gem_{gem.get('id')}"
        ):

            if not user_message.strip():

                st.warning(
                    "請先輸入測試問題。"
                )

            else:

                prompt = build_gem_prompt(
                    gem,
                    user_message
                )

                with st.spinner(
                    "Gemini 思考中..."
                ):

                    result = ask_gemini(
                        prompt
                    )

                st.session_state.gemini_result = result

        if st.session_state.gemini_result:

            st.markdown("---")

            st.subheader(
                "🤖 Gemini 回覆"
            )

            st.write(
                st.session_state.gemini_result
            )

    # =====================================================
    # Tab 6 Chat
    # =====================================================

    with tabs[5]:

        show_chat(
            gem
        )


# =========================================================
# 28. AI Optimization UI
# =========================================================

def show_gem_ai_optimization(
    gem
):

    st.subheader(
        "✨ AI 優化"
    )

    st.info(
        "AI 會分析這個 GEM 的 Role、Workflow、"
        "Greeting 與 Knowledge，提出完整優化版本。"
    )

    st.markdown(
        f"""
        **目前 GEM**

        名稱：{gem.get('name', '')}

        Role：{len(gem.get('role', '') or '')} 字

        Workflow：{len(gem.get('workflow', '') or '')} 字

        Greeting：{len(gem.get('greeting', '') or '')} 字
        """
    )

    st.markdown("---")

    if st.button(
        "🔥 一鍵開始 AI 優化",
        type="primary",
        key=f"start_optimize_{gem.get('id')}"
    ):

        with st.spinner(
            "Gemini 正在分析你的 GEM..."
        ):

            result = optimize_gem(
                gem
            )

        st.session_state.optimizer_result = (
            result
        )

        st.session_state.optimization_preview = (
            result
        )

        st.rerun()

    optimization = (
        st.session_state.optimization_preview
    )

    if not optimization:
        return

    st.markdown("---")

    st.success(
        "✅ AI 優化分析完成"
    )

    st.warning(
        "以下內容目前只是「預覽」，"
        "尚未修改 Supabase。"
    )

    # -----------------------------------------------------
    # 問題分析
    # -----------------------------------------------------

    st.subheader(
        "🔎 問題分析"
    )

    st.write(
        optimization.get(
            "problem_analysis",
            ""
        )
    )

    # -----------------------------------------------------
    # Role
    # -----------------------------------------------------

    st.subheader(
        "🎯 優化後 Role"
    )

    st.text_area(
        "優化後 Role",
        value=optimization.get(
            "optimized_role",
            ""
        ),
        height=260,
        disabled=True,
        key=f"optimized_role_preview_{gem.get('id')}"
    )

    # -----------------------------------------------------
    # Workflow
    # -----------------------------------------------------

    st.subheader(
        "🔄 優化後 Workflow"
    )

    st.text_area(
        "優化後 Workflow",
        value=optimization.get(
            "optimized_workflow",
            ""
        ),
        height=300,
        disabled=True,
        key=f"optimized_workflow_preview_{gem.get('id')}"
    )

    # -----------------------------------------------------
    # Greeting
    # -----------------------------------------------------

    st.subheader(
        "👋 優化後 Greeting"
    )

    st.text_area(
        "優化後 Greeting",
        value=optimization.get(
            "optimized_greeting",
            ""
        ),
        height=180,
        disabled=True,
        key=f"optimized_greeting_preview_{gem.get('id')}"
    )

    # -----------------------------------------------------
    # Knowledge suggestions
    # -----------------------------------------------------

    st.subheader(
        "📚 Knowledge 建議"
    )

    st.write(
        optimization.get(
            "knowledge_suggestions",
            ""
        )
    )

    # -----------------------------------------------------
    # Overall
    # -----------------------------------------------------

    st.subheader(
        "💡 整體建議"
    )

    st.write(
        optimization.get(
            "overall_suggestions",
            ""
        )
    )

    st.markdown("---")

    st.warning(
        "⚠️ 「套用優化版本」會直接更新目前 GEM 的 "
        "Role、Workflow、Greeting。"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "❌ 放棄這次優化",
            key=f"discard_optimize_{gem.get('id')}"
        ):

            st.session_state.optimizer_result = ""
            st.session_state.optimization_preview = None

            st.success(
                "已放棄這次優化，原 GEM 不會變更。"
            )

            st.rerun()

    with col2:

        if st.button(
            "✅ 套用優化版本",
            type="primary",
            key=f"apply_optimize_{gem.get('id')}"
        ):

            success = apply_optimization(
                gem,
                optimization
            )

            if success:

                st.session_state.optimizer_result = ""
                st.session_state.optimization_preview = None

                st.success(
                    "🎉 AI 優化版本已成功套用！"
                )

                st.rerun()


# =========================================================
# 29. Chat
# =========================================================

def show_chat(gem):

    st.subheader(
        "💬 GEM 對話"
    )

    sessions = get_chat_sessions_by_gem(
        gem.get("id")
    )

    if not sessions:

        if st.button(
            "＋ 建立新對話",
            key=f"create_chat_{gem.get('id')}"
        ):

            session = create_chat_session(
                gem.get("id"),
                "新對話"
            )

            if session:

                st.session_state.selected_chat_session_id = (
                    session.get("id")
                )

                st.rerun()

        st.info(
            "目前還沒有對話，請建立新對話。"
        )

        return

    session_options = {
        session.get("id"):
            session.get(
                "title",
                "新對話"
            )
        for session in sessions
    }

    session_ids = list(
        session_options.keys()
    )

    current_session = (
        st.session_state.selected_chat_session_id
    )

    if current_session not in session_ids:
        current_session = session_ids[0]

        st.session_state.selected_chat_session_id = (
            current_session
        )

    selected_session = st.selectbox(
        "選擇對話",
        options=session_ids,
        index=session_ids.index(
            current_session
        ),
        format_func=lambda x:
            session_options.get(
                x,
                "新對話"
            ),
        key=f"chat_selector_{gem.get('id')}"
    )

    st.session_state.selected_chat_session_id = (
        selected_session
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "＋ 新對話",
            key=f"new_chat_{gem.get('id')}"
        ):

            session = create_chat_session(
                gem.get("id"),
                "新對話"
            )

            if session:

                st.session_state.selected_chat_session_id = (
                    session.get("id")
                )

                st.rerun()

    with col2:

        if st.button(
            "🗑️ 刪除目前對話",
            key=f"delete_chat_{gem.get('id')}"
        ):

            if delete_chat_session(
                selected_session
            ):

                st.session_state.selected_chat_session_id = None

                st.success(
                    "對話已刪除。"
                )

                st.rerun()

    st.markdown("---")

    messages = get_chat_messages(
        selected_session
    )

    for message in messages:

        role = message.get(
            "role",
            "assistant"
        )

        content = message.get(
            "content",
            ""
        )

        with st.chat_message(
            role
            if role in ["user", "assistant"]
            else "assistant"
        ):

            st.write(content)

    user_message = st.chat_input(
        "輸入訊息...",
        key=f"chat_input_{gem.get('id')}"
    )

    if user_message:

        create_chat_message(
            selected_session,
            "user",
            user_message
        )

        prompt = build_gem_prompt(
            gem,
            user_message
        )

        with st.spinner(
            "Gemini 回覆中..."
        ):

            answer = ask_gemini(
                prompt
            )

        create_chat_message(
            selected_session,
            "assistant",
            answer
        )

        st.rerun()


# =========================================================
# 30. Gemini Prompt Generator
# =========================================================

def show_prompt_generator():

    show_header()

    st.header(
        "✨ Gemini Prompt 自動生成器"
    )

    purpose = st.text_area(
        "你想建立什麼 GEM？",
        height=150,
        placeholder="例如：青年職涯探索 AI 顧問"
    )

    target = st.text_area(
        "主要服務對象",
        height=120,
        placeholder="例如：20～30 歲正在探索職涯方向的年輕人"
    )

    functions = st.text_area(
        "主要功能",
        height=150,
        placeholder="例如：職涯探索、提問、整理優勢、提供下一步行動"
    )

    tone = st.text_input(
        "希望 AI 的語氣",
        value="溫暖、專業、具支持感"
    )

    if st.button(
        "🤖 自動產生 GEM Prompt",
        type="primary"
    ):

        prompt = f"""
請幫我設計一個高品質 AI GEM。

GEM 目的：
{purpose}

服務對象：
{target}

主要功能：
{functions}

語氣：
{tone}

請產生：

1. GEM 名稱
2. Description
3. Role
4. Workflow
5. Greeting

要求：
- Role 要清楚
- Workflow 要可以執行
- 具有實際專業價值
- 不要過度空泛
- 使用繁體中文
"""

        with st.spinner(
            "Gemini 正在建立 GEM..."
        ):

            result = ask_gemini(
                prompt
            )

        st.session_state.gemini_result = (
            result
        )

    if st.session_state.gemini_result:

        st.markdown("---")

        st.subheader(
            "🤖 生成結果"
        )

        st.write(
            st.session_state.gemini_result
        )


# =========================================================
# 31. Chat history
# =========================================================

def show_chat_history():

    show_header()

    st.header(
        "💬 對話歷史"
    )

    sessions = get_chat_sessions()

    if not sessions:

        st.info(
            "目前沒有對話紀錄。"
        )

        return

    for session in sessions:

        gem = get_gem(
            session.get("gem_id")
        )

        gem_name = (
            gem.get("name", "未知 GEM")
            if gem
            else "未知 GEM"
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {session.get('title', '新對話')}"
            )

            st.caption(
                f"GEM：{gem_name}"
            )

            if st.button(
                "開啟對話",
                key=f"history_open_{session.get('id')}"
            ):

                st.session_state.selected_gem_id = (
                    session.get("gem_id")
                )

                st.session_state.selected_chat_session_id = (
                    session.get("id")
                )

                st.session_state.page = (
                    "GEM 詳細"
                )

                st.rerun()


# =========================================================
# 32. Export / Backup
# =========================================================

def show_export():

    show_header()

    st.header(
        "⬇️ 匯出與備份"
    )

    gems = get_gems()

    st.metric(
        "目前 GEM",
        len(gems)
    )

    st.download_button(
        "⬇️ 匯出全部 GEM 備份 JSON",
        data=gem_backup_json(),
        file_name=(
            "gem_builder_cloud_backup.json"
        ),
        mime="application/json"
    )

    st.markdown("---")

    for gem in gems:

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {gem.get('name', '')}"
            )

            st.download_button(
                "⬇️ TXT",
                data=gem_to_txt(gem),
                file_name=f"{gem.get('name', 'gem')}.txt",
                mime="text/plain",
                key=f"export_txt_{gem.get('id')}"
            )

            st.download_button(
                "⬇️ JSON",
                data=json.dumps(
                    gem_to_json(gem),
                    ensure_ascii=False,
                    indent=2,
                    default=str
                ),
                file_name=f"{gem.get('name', 'gem')}.json",
                mime="application/json",
                key=f"export_json_{gem.get('id')}"
            )


# =========================================================
# 33. Templates
# =========================================================

def show_templates():

    show_header()

    st.header(
        "📦 GEM 模板"
    )

    templates = [

        {
            "name": "職涯顧問 GEM",
            "description":
                "協助使用者進行職涯探索。",
            "role":
                "你是一位專業、溫暖且具支持性的職涯顧問。",
            "workflow":
                "先理解使用者目前狀態，再提出探索問題，"
                "整理資訊，最後提供具體下一步。",
            "greeting":
                "你好，我會陪你一起探索適合你的職涯方向。"
        },

        {
            "name": "AI 陪聊 GEM",
            "description":
                "提供溫暖自然的 AI 對話。",
            "role":
                "你是一位溫暖、耐心、尊重使用者的 AI 陪聊夥伴。",
            "workflow":
                "先理解使用者情緒與需求，再自然回應，"
                "避免過度說教。",
            "greeting":
                "嗨，很高興陪你聊聊。今天想從哪裡開始？"
        },

        {
            "name": "學習教練 GEM",
            "description":
                "協助使用者建立學習計畫。",
            "role":
                "你是一位有耐心、重視實作的 AI 學習教練。",
            "workflow":
                "確認學習目標、目前程度與可用時間，"
                "建立具體計畫並追蹤進度。",
            "greeting":
                "你好，我們一起把你的學習目標變成可以執行的計畫。"
        },
    ]

    for template in templates:

        with st.container(
            border=True
        ):

            st.subheader(
                template["name"]
            )

            st.write(
                template["description"]
            )

            if st.button(
                "使用此模板",
                key=f"template_{template['name']}"
            ):

                result = create_gem(
                    template["name"],
                    template["description"],
                    template["role"],
                    template["workflow"],
                    template["greeting"]
                )

                if result:

                    st.success(
                        "✅ 模板 GEM 建立成功"
                    )

                    st.rerun()


# =========================================================
# 34. Import
# =========================================================

def show_import():

    show_header()

    st.header(
        "⬆️ 匯入 GEM"
    )

    uploaded = st.file_uploader(
        "上傳 JSON",
        type=["json"]
    )

    if not uploaded:
        st.info(
            "請選擇 GEM JSON 檔案。"
        )
        return

    try:

        content = uploaded.read()

        data = json.loads(
            content.decode("utf-8")
        )

    except Exception as e:

        st.error(
            f"❌ JSON 讀取失敗：{e}"
        )

        return

    st.success(
        "JSON 讀取成功。"
    )

    if isinstance(data, dict):

        data = [data]

    if not isinstance(data, list):

        st.error(
            "JSON 格式不正確。"
        )

        return

    st.write(
        f"共找到 {len(data)} 個 GEM。"
    )

    if st.button(
        "⬆️ 匯入全部 GEM",
        type="primary"
    ):

        success_count = 0

        for item in data:

            result = create_gem(
                item.get(
                    "name",
                    "未命名 GEM"
                ),
                item.get(
                    "description",
                    ""
                ),
                item.get(
                    "role",
                    ""
                ),
                item.get(
                    "workflow",
                    ""
                ),
                item.get(
                    "greeting",
                    ""
                )
            )

            if result:

                success_count += 1

                new_gem = result[0]

                knowledge = item.get(
                    "knowledge",
                    []
                )

                for k in knowledge:

                    create_knowledge(
                        new_gem.get("id"),
                        k.get(
                            "title",
                            ""
                        ),
                        k.get(
                            "content",
                            ""
                        )
                    )

        st.success(
            f"🎉 成功匯入 {success_count} 個 GEM"
        )

        st.rerun()


# =========================================================
# 35. Sidebar navigation
# =========================================================

def show_sidebar():

    st.sidebar.title(
        "☁️ GEM Builder"
    )

    st.sidebar.caption(
        "Cloud Edition"
    )

    pages = [
        "首頁",
        "建立 GEM",
        "工作區",
        "Prompt 生成器",
        "對話歷史",
        "匯出與備份",
        "GEM 模板",
        "匯入 GEM",
    ]

    current_page = st.session_state.page

    selected_page = st.sidebar.radio(
        "功能",
        pages,
        index=(
            pages.index(current_page)
            if current_page in pages
            else 0
        ),
        key="main_navigation"
    )

    if selected_page != st.session_state.page:

        st.session_state.page = (
            selected_page
        )

        st.rerun()

    show_model_management()

    st.sidebar.markdown("---")

    if st.session_state.selected_model:

        st.sidebar.success(
            "🟢 Gemini 已連線"
        )

        st.sidebar.caption(
            st.session_state.selected_model
        )

    else:

        st.sidebar.warning(
            "🟡 尚未選擇 Gemini"
        )


# =========================================================
# 36. Router
# =========================================================

show_sidebar()

page = st.session_state.page

if page == "首頁":

    show_home()

elif page == "建立 GEM":

    show_create_gem()

elif page == "工作區":

    show_workspace()

elif page == "GEM 詳細":

    show_gem_detail()

elif page == "Prompt 生成器":

    show_prompt_generator()

elif page == "對話歷史":

    show_chat_history()

elif page == "匯出與備份":

    show_export()

elif page == "GEM 模板":

    show_templates()

elif page == "匯入 GEM":

    show_import()

else:

    show_home()


# =========================================================
# 37. Footer
# =========================================================

st.markdown("---")

st.caption(
    "GEM Builder Cloud｜Day 32-A｜"
    "Responsive Desktop + Mobile + Tablet"
)
