import os
import sys
import json
import random
import time
import re
import webbrowser
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import httpx
import uvicorn

app = FastAPI(title="Second Brain System Pro Perfect")
LAST_LLM_ERROR = ""

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "database.json")
STATIC_DIR = os.path.join(BUNDLE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.join(BASE_DIR, "static")

ADMIN_USER = "babycck"

def sanitize_user_id(user_id: Optional[str]) -> str:
    if not user_id:
        return ADMIN_USER
    clean = re.sub(r'[^\w\u4e00-\u9fa5_-]', '', str(user_id)).strip()
    return clean if clean else ADMIN_USER

def get_initial_template_for_new_user() -> Dict[str, Any]:
    return {
        "assets": [
            {
                "id": "asset-init-1",
                "category": "creation",
                "sub_type": "technique",
                "title": "三幕式叙事结构与转折点设计",
                "source": "编剧工业经典模型",
                "scenario": "长篇小说、剧本、故事推演等创意构思阶段调用",
                "content": "核心拆解：\n\n【第一幕·建置】：交代人物目标与现状，在10%-15%处制造激励事件，彻底打破人物平静生活。\n\n【第二幕·对抗】：人物进入陌生环境，遭遇层层升级的阻碍。中间点（50%）发生虚假胜利或虚假失败，随后在75%处迎来灵魂黑夜（全盘皆输）。\n\n【第三幕·高潮与结局】：绝地反击，核心矛盾正面对决，展现人物弧线升华。",
                "evidence": "出处：经典编剧理论与视听工业范式",
                "tags": ["创作资料", "三幕式", "转折点", "新手示例"],
                "relations": [],
                "created_at": time.strftime("%Y-%m-%d %H:%M")
            },
            {
                "id": "asset-init-2",
                "category": "skill",
                "sub_type": "method",
                "title": "费曼学习法与知识工业化萃取",
                "source": "现代认知科学",
                "scenario": "接触复杂新概念、行业黑话或需要向他人交付方案时调用",
                "content": "核心拆解：\n\n1. 明确目标：选定一个具体概念或技能。\n2. 讲给外行听：尝试用8岁小孩能听懂的极简白话解释它，杜绝一切行话黑话。\n3. 卡壳回溯：遇到解释不通或生涩的地方，重新查阅原始资料直到彻底打通。\n4. 精炼与类比：使用生活中的具象隐喻进行包装与交付。",
                "evidence": "出处：理查德·费曼物理学讲义认知心法",
                "tags": ["我的技能", "费曼学习法", "知识工程", "新手示例"],
                "relations": [],
                "created_at": time.strftime("%Y-%m-%d %H:%M")
            }
        ]
    }

def get_user_db_path(user_id: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    clean_user = sanitize_user_id(user_id)
    if clean_user in [ADMIN_USER, "admin", "default"]:
        return os.path.join(DATA_DIR, f"database_{ADMIN_USER}.json")
    return os.path.join(DATA_DIR, f"database_{clean_user}.json")

def load_db(user_id: str = ADMIN_USER) -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    clean_user = sanitize_user_id(user_id)
    target_file = get_user_db_path(clean_user)

    # 兼容历史数据：若访问 babycck 或旧的 admin/default，且专属库尚不存在，优先从旧数据库文件迁移原有全部资产与日记
    if clean_user in [ADMIN_USER, "admin", "default"] and not os.path.exists(target_file):
        for candidate in ["database_admin.json", "database.json", "database_default.json"]:
            old_file = os.path.join(DATA_DIR, candidate)
            if os.path.exists(old_file):
                try:
                    with open(old_file, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    with open(target_file, "w", encoding="utf-8") as f:
                        json.dump(old_data, f, ensure_ascii=False, indent=2)
                    return old_data
                except Exception as e:
                    print(f"[Migration Error] {e}")

    # 若该用户库不存在，创建新库
    if not os.path.exists(target_file):
        if clean_user in [ADMIN_USER, "admin", "default"]:
            initial_data = {"assets": []}
        else:
            initial_data = get_initial_template_for_new_user()
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)
        return initial_data

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"assets": []}

def save_db(data: Dict[str, Any], user_id: str = ADMIN_USER):
    os.makedirs(DATA_DIR, exist_ok=True)
    clean_user = sanitize_user_id(user_id)
    target_file = get_user_db_path(clean_user)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

CONFIG_FILE = os.path.join(DATA_DIR, "system_config.json")

def load_system_config() -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "admin_user": ADMIN_USER,
            "allowed_spaces": [ADMIN_USER]
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if "allowed_spaces" not in cfg or not isinstance(cfg["allowed_spaces"], list):
                cfg["allowed_spaces"] = [ADMIN_USER]
            if ADMIN_USER not in cfg["allowed_spaces"]:
                cfg["allowed_spaces"].append(ADMIN_USER)
            return cfg
    except Exception:
        return {"admin_user": ADMIN_USER, "allowed_spaces": [ADMIN_USER]}

def save_system_config(cfg: Dict[str, Any]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def extract_user_id(request: Request) -> str:
    user = (
        request.headers.get("X-User-Space")
        or request.headers.get("X-Space-Id")
        or request.query_params.get("user")
        or request.query_params.get("space")
        or ADMIN_USER
    )
    return sanitize_user_id(user)

def is_admin_user(request: Request) -> bool:
    user = extract_user_id(request)
    return user in [ADMIN_USER, "admin", "default"]

def check_space_access(user_id: str, request: Request):
    clean_user = sanitize_user_id(user_id)

    # 1. 管理员专属主空间 babycck：仅当请求来源是管理员时放行
    if clean_user in [ADMIN_USER, "admin", "default"]:
        if not is_admin_user(request):
            raise HTTPException(
                status_code=403,
                detail=f"【无权访问】{ADMIN_USER} 为管理员最高主库，其他用户无权查看或修改！"
            )
        return True

    # 2. 普通好友空间（如 tom, any, 小明）：必须由 babycck 授权开通，否则拒绝访问
    cfg = load_system_config()
    allowed = cfg.get("allowed_spaces", [])
    target_file = get_user_db_path(clean_user)
    if clean_user not in allowed and not os.path.exists(target_file):
        raise HTTPException(
            status_code=403,
            detail=f"【空间未授权】专属空间『{clean_user}』尚未由管理员 {ADMIN_USER} 开通！请联系 {ADMIN_USER} 开通您的私密专属空间。"
        )
    return True

class CreateSpaceRequest(BaseModel):
    space_name: str

class DeleteSpaceRequest(BaseModel):
    space_name: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class VerifyAdminRequest(BaseModel):
    password: str

class MatchQueryRequest(BaseModel):
    query: str
    target_type: str = "book"
    model: Optional[str] = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class DimensionAnalyzeRequest(BaseModel):
    target_title: str
    target_meta: str = ""
    dimension: str
    custom_prompt: Optional[str] = ""
    full_text: Optional[str] = ""  # 上传的全本文档内容
    model: Optional[str] = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class UniversalAnalyzeRequest(BaseModel):
    content: str
    mode: Optional[str] = "note"
    selected_target: Optional[Dict[str, Any]] = None
    model: Optional[str] = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class SaveAssetRequest(BaseModel):
    category: str
    sub_type: str = "general"
    title: str
    source: str = "万能输入拆解"
    scenario: str = "通用场景"
    content: str
    evidence: str = ""
    tags: List[str] = Field(default_factory=list)
    relations: List[Dict[str, Any]] = Field(default_factory=list)

class DeleteAssetRequest(BaseModel):
    id: str

class BrainstormRequest(BaseModel):
    idea: str
    model: Optional[str] = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class GachaRequest(BaseModel):
    anchor_asset_id: Optional[str] = None
    output_form: Optional[str] = "random"
    model: Optional[str] = "deepseek-chat"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

# 智能 LLM 请求：内置国内直连防代理卡死、模型自动纠正与细粒度超时保护
async def call_llm(prompt: str, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None, timeout_sec: float = 120.0) -> str:
    key = (api_key or "").strip() or os.environ.get("DEEPSEEK_API_KEY", "").strip() or os.environ.get("API_KEY", "").strip()
    url = (base_url or "").strip().rstrip("/") or os.environ.get("BASE_URL", "").strip().rstrip("/")
    if not key:
        print("[LLM Error] API Key 未填写，请在设置中配置！")
        return ""
    if not url:
        url = "https://api.deepseek.com"

    # 1. 模型别名自动纠正：DeepSeek 官方对话模型为 deepseek-chat，不存在 flash
    target_model = (model or "").strip()
    if not target_model or target_model in ["deepseek-flash", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek"]:
        target_model = "deepseek-chat"

    if url.endswith("/chat/completions"):
        endpoint = url
    elif url.endswith("/v1"):
        endpoint = f"{url}/chat/completions"
    else:
        endpoint = f"{url}/v1/chat/completions" if "deepseek" in url else f"{url}/chat/completions"

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": "你是一个顶级叙事工业解构与知识工程专家。你总是输出精准、犀利、结构严密的结构化产物，严禁一切泛泛而谈的废话套话。必须严格遵循 JSON 格式输出。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 8192
    }

    # 2. 细粒度超时：连接超时 10 秒，读写超时 120 秒，杜绝无限卡死
    client_timeout = httpx.Timeout(timeout=timeout_sec, connect=10.0, read=timeout_sec, write=15.0)

    # 3. 智能代理分流：针对 DeepSeek 等国内服务，默认走原生直连 (trust_env=False)，避开本地代理器(Clash/VPN)的死等与误拦截
    is_domestic = any(d in url.lower() for d in ["deepseek.com", "siliconflow", "baidubce", "aliyun", "tencent"])
    trust_env_options = [False, True] if is_domestic else [True, False]

    global LAST_LLM_ERROR
    LAST_LLM_ERROR = ""
    last_error = None
    for use_env_proxy in trust_env_options:
        try:
            mode_desc = "系统代理" if use_env_proxy else "原生直连"
            async with httpx.AsyncClient(timeout=client_timeout, trust_env=use_env_proxy) as client:
                res = await client.post(endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    LAST_LLM_ERROR = ""
                    return data["choices"][0]["message"]["content"]
                else:
                    err_msg = f"HTTP {res.status_code}: {res.text}"
                    print(f"[LLM Error - {mode_desc}] {err_msg}")
                    last_error = err_msg
                    LAST_LLM_ERROR = err_msg
                    # 鉴权错误或模型名错误无需换通道重试
                    if res.status_code in [400, 401, 403, 404]:
                        break
        except httpx.ReadTimeout:
            err_detail = "等待模型生成响应超时 (ReadTimeout)。DeepSeek 官方服务器当前可能正在排队，请稍后重试"
            last_error = f"[{mode_desc}] {err_detail}"
            LAST_LLM_ERROR = last_error
            print(f"[LLM Exception - {mode_desc}] {err_detail}")
            break
        except Exception as e:
            err_detail = f"{type(e).__name__}" + (f": {e}" if str(e) else "")
            last_error = f"[{mode_desc}] {err_detail}"
            LAST_LLM_ERROR = last_error
            print(f"[LLM Exception - {mode_desc}] {err_detail}")

    return ""

def normalize_card(card: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(card, dict):
        return card

    # 1. 规范化 content 字段（若大模型输出为嵌套字典或列表，自动转为格式化文本，杜绝 [object Object]）
    content_val = card.get("content")
    if isinstance(content_val, dict):
        lines = []
        for k, v in content_val.items():
            if isinstance(v, list):
                v_str = "\n".join(f"• {x}" for x in v)
            elif isinstance(v, dict):
                v_str = json.dumps(v, ensure_ascii=False, indent=2)
            else:
                v_str = str(v)
            prefix = "" if str(k).startswith("【") else f"【{k}】：\n"
            lines.append(f"{prefix}{v_str}")
        card["content"] = "\n\n".join(lines)
    elif isinstance(content_val, list):
        card["content"] = "\n".join(f"• {x}" if not str(x).startswith("•") else str(x) for x in content_val)
    elif content_val is None:
        card["content"] = ""
    else:
        card["content"] = str(content_val)

    # 2. 规范化 evidence 字段
    evidence_val = card.get("evidence")
    if isinstance(evidence_val, dict):
        card["evidence"] = "\n".join(f"【{k}】{v}" for k, v in evidence_val.items())
    elif isinstance(evidence_val, list):
        card["evidence"] = "\n".join(str(x) for x in evidence_val)
    elif evidence_val is None:
        card["evidence"] = ""
    else:
        card["evidence"] = str(evidence_val)

    # 3. 规范化 scenario 字段
    scenario_val = card.get("scenario")
    if isinstance(scenario_val, dict):
        card["scenario"] = " / ".join(f"{k}: {v}" for k, v in scenario_val.items())
    elif isinstance(scenario_val, list):
        card["scenario"] = " / ".join(str(x) for x in scenario_val)
    elif scenario_val is None:
        card["scenario"] = "通用场景"
    else:
        card["scenario"] = str(scenario_val)

    return card

def clean_and_parse_json(raw_text: str) -> List[Dict[str, Any]]:
    if not raw_text:
        return []
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # 1. 尝试 strict=False 的标准 loads（处理字符串内部实际换行符）
    try:
        data = json.loads(text, strict=False)
        if isinstance(data, list):
            return [normalize_card(x) for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [normalize_card(data)]
    except Exception:
        pass

    # 2. 截断自动补齐
    try:
        fixed_text = text.rstrip().rstrip(",") + "]"
        data = json.loads(fixed_text, strict=False)
        if isinstance(data, list):
            return [normalize_card(x) for x in data if isinstance(x, dict)]
    except Exception:
        pass

    try:
        fixed_text = text.rstrip().rstrip(",") + "}]"
        data = json.loads(fixed_text, strict=False)
        if isinstance(data, list):
            return [normalize_card(x) for x in data if isinstance(x, dict)]
    except Exception:
        pass

    # 3. 状态机精准切分每一个独立顶级 {...} 对象
    extracted = []
    in_string = False
    escape = False
    brace_depth = 0
    start_pos = -1

    for idx, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == '{':
                if brace_depth == 0:
                    start_pos = idx
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0 and start_pos != -1:
                    chunk = text[start_pos : idx + 1]
                    try:
                        obj = json.loads(chunk, strict=False)
                        if isinstance(obj, dict) and ("title" in obj or "content" in obj):
                            extracted.append(normalize_card(obj))
                    except Exception:
                        pass
                    start_pos = -1

    return extracted

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools():
    return Response(content="{}", media_type="application/json")

@app.get("/api/db")
def get_database(request: Request):
    user_id = extract_user_id(request)
    check_space_access(user_id, request)
    return load_db(user_id)

@app.get("/api/admin/spaces")
def list_spaces(request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="【权限拒绝】只有管理员 babycck 才能查看空间管理列表")
    cfg = load_system_config()
    allowed = list(dict.fromkeys(cfg.get("allowed_spaces", []) + [ADMIN_USER]))
    spaces_info = []
    for sp in allowed:
        sp_path = get_user_db_path(sp)
        count = 0
        if os.path.exists(sp_path):
            try:
                with open(sp_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    count = len(data.get("assets", []))
            except Exception:
                pass
        spaces_info.append({
            "name": sp,
            "is_admin": (sp == ADMIN_USER or sp in ["admin", "default"]),
            "asset_count": count,
            "created": os.path.exists(sp_path)
        })
    return {"spaces": spaces_info}

@app.post("/api/admin/space/create")
def create_space(req: CreateSpaceRequest, request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="【权限拒绝】只有管理员 babycck 才能创建和分享好友专属空间！")
    space_name = sanitize_user_id(req.space_name)
    if not space_name or space_name in [ADMIN_USER, "admin", "default"]:
        raise HTTPException(status_code=400, detail="空间名称不合法或不可与管理员同名")

    cfg = load_system_config()
    if space_name not in cfg["allowed_spaces"]:
        cfg["allowed_spaces"].append(space_name)
        save_system_config(cfg)

    # 预初始化该好友的专属独立数据库文件
    target_file = get_user_db_path(space_name)
    if not os.path.exists(target_file):
        init_data = get_initial_template_for_new_user()
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(init_data, f, ensure_ascii=False, indent=2)

    return {"status": "ok", "space_name": space_name}

@app.post("/api/admin/space/delete")
def delete_space(req: DeleteSpaceRequest, request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="【权限拒绝】只有管理员 babycck 才能删除好友空间！")
    space_name = sanitize_user_id(req.space_name)
    if space_name in [ADMIN_USER, "admin", "default"]:
        raise HTTPException(status_code=400, detail="不可删除 babycck 主管理员空间")

    cfg = load_system_config()
    cfg["allowed_spaces"] = [s for s in cfg["allowed_spaces"] if s != space_name]
    save_system_config(cfg)
    return {"status": "ok", "deleted_space": space_name}

@app.post("/api/test_connection")
async def test_connection(req: MatchQueryRequest):
    key = (req.api_key or "").strip()
    url = (req.base_url or "").strip().rstrip("/")
    if not key:
        return {"status": "error", "message": "API Key 不能为空，请先在设置中填写！"}
    if not url:
        url = "https://api.deepseek.com"

    target_model = (req.model or "").strip()
    if not target_model or target_model in ["deepseek-flash", "deepseek-v4-flash", "deepseek-v4-flash-vision-exp", "deepseek"]:
        target_model = "deepseek-chat"

    if url.endswith("/chat/completions"):
        endpoint = url
    elif url.endswith("/v1"):
        endpoint = f"{url}/chat/completions"
    else:
        endpoint = f"{url}/v1/chat/completions" if "deepseek" in url else f"{url}/chat/completions"

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": target_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 10
    }

    start_time = time.time()
    client_timeout = httpx.Timeout(timeout=30.0, connect=10.0, read=30.0, write=10.0)
    is_domestic = any(d in url.lower() for d in ["deepseek.com", "siliconflow", "baidubce", "aliyun", "tencent"])
    trust_env_options = [False, True] if is_domestic else [True, False]

    last_err = ""
    latency = 0
    for use_env_proxy in trust_env_options:
        mode_desc = "系统代理" if use_env_proxy else "原生直连"
        try:
            async with httpx.AsyncClient(timeout=client_timeout, trust_env=use_env_proxy) as client:
                res = await client.post(endpoint, headers=headers, json=payload)
                latency = int((time.time() - start_time) * 1000)
                if res.status_code == 200:
                    data = res.json()
                    reply = data["choices"][0]["message"]["content"].strip()
                    return {
                        "status": "ok",
                        "latency_ms": latency,
                        "model": target_model,
                        "message": f"连接成功！通道: [{mode_desc}]，耗时: {latency}ms，模型 [{target_model}] 响应正常 (回复: {reply})。"
                    }
                else:
                    return {
                        "status": "error",
                        "latency_ms": latency,
                        "model": target_model,
                        "message": f"接口报错 (HTTP {res.status_code}): {res.text}"
                    }
        except httpx.ReadTimeout:
            latency = int((time.time() - start_time) * 1000)
            last_err = f"[{mode_desc}] 成功连接服务器，但模型在 30 秒内未生成完毕 (ReadTimeout)。DeepSeek 官方当前可能处于高峰期拥堵排队中，请稍后重试。"
            break
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            last_err = f"[{mode_desc}] {type(e).__name__}" + (f": {e}" if str(e) else "")

    return {
        "status": "error",
        "latency_ms": latency,
        "model": target_model,
        "message": f"连接失败: {last_err}"
    }

@app.post("/api/match_targets")
async def match_targets(req: MatchQueryRequest):
    q = req.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="线索不能为空")

    target_name = "图书/网络小说/出版名著" if req.target_type == "book" else "电影/电视剧/动漫/短剧"
    prompt = f"""用户记不清具体名字，只提供了一段模糊记忆线索：
"{q}"

目标类型：【{target_name}】
请从大模型海量知识库中推测匹配出最可能的 3 个具体作品候选项。
格式严格为 JSON 数组：
[
  {{
    "title": "作品标准名称（如《星际牛仔》《狂飙》《诡秘之主》）",
    "meta": "作者/导演/年份/体裁",
    "confidence": "匹配度百分比（如：95%）",
    "summary": "一句话核心剧情与名场面特质"
  }}
]
只输出合法 JSON 数组！"""

    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=60.0)
    options = clean_and_parse_json(res)
    if not options:
        if req.target_type == "video":
            options = [
                {"title": "《狂飙》", "meta": "徐纪周 执导 / 张译、张颂文 主演 / 2023", "confidence": "95%", "summary": "旧厂街鱼贩高启强跨越二十年的草根黑化与警匪博弈"},
                {"title": "《漫长的季节》", "meta": "辛爽 执导 / 范伟、秦昊 主演 / 2023", "confidence": "88%", "summary": "东北重工业小城碎尸悬案，三条时空线交织与红毛衣命运回响"},
                {"title": "《盗梦空间》", "meta": "克里斯托弗·诺兰 执导 / 2010", "confidence": "75%", "summary": "陀螺图腾、多层造梦与潜意识潜伏因果闭环"}
            ]
        else:
            options = [
                {"title": "《诡秘之主》", "meta": "爱潜水的乌贼 著 / 奇幻序列克苏鲁网文", "confidence": "95%", "summary": "占卜家序列、魔药晋升机制与廷根市高潮牺牲大纲"},
                {"title": "《三体》", "meta": "刘慈欣 著 / 硬科幻雨果奖名著", "confidence": "88%", "summary": "黑暗森林法则、面壁者计划与降维打击世界观全景"},
                {"title": "《白夜行》", "meta": "东野圭吾 著 / 经典悬疑长篇小说", "confidence": "90%", "summary": "亮司与雪穗互为太阳与暗影，跨越十九年的无声共生与残酷救赎"}
            ]

    return {"options": options}

@app.post("/api/analyze_dimension")
async def analyze_dimension(req: DimensionAnalyzeRequest):
    dim = req.dimension
    title = req.target_title
    meta = req.target_meta
    full_text = (req.full_text or "").strip()

    # 精准溯源优化：严格要求标注具体章节/分卷与名场面关键词
    evidence_instruction = "在引用【evidence 证据依据】时，必须尽量标注出自第几章、第几卷，或当时的具体标志性场景关键词（例如：【出处：第13章/高中时期】手作刺绣包交接场景），以便于原著精准溯源对照！"

    if dim == "character":
        task_instruction = f"""必须全面深挖【{title}】中所有真实的核心主要角色群像（根据作品实际设定，提取主角、核心伙伴、对照人物、关键配角等，有几位真实主要角色就生成几张卡片，每位人物必须生成单独一张独立卡片）。
每张卡片的 title 必须包含该角色的真实姓名（例如：泉此方人物极性档案 / 高启强人物极性档案 / 唐川友纪人物极性档案）。
每张卡片的 content 必须是格式排版工整的纯文本字符串（严禁输出为嵌套子对象），分点包含：
【身份与定位】：
【核心欲望与行动驱动】：
【深层软肋或反差特质】：
【核心矛盾与戏剧张力】：
【人物弧线与高光节拍】：
{evidence_instruction}"""
    elif dim == "relations":
        task_instruction = f"""深入挖掘【{title}】中多位核心角色之间的利益纠葛、死敌博弈、情感软肋与阶层借势网络。生成 1~2 张关系网总览卡片，卡片内的 relations 数组必须包含全剧 5~8 组核心对抗与羁绊关系（每组包含 source, target, relation, desc）。
{evidence_instruction}"""
    elif dim == "plot":
        task_instruction = f"""深入挖掘【{title}】的剧情结构地图。严格按照分卷或三幕式横轴推进，每一卷/幕拆分为一张独立卡片（例如第1幕·破局点、第2幕·蓄水对抗、第3幕·终局高潮反转等，生成 3~4 张卡片）。
{evidence_instruction}"""
    elif dim == "foreshadow":
        task_instruction = f"""深入挖掘【{title}】中贯穿全剧/全书的多条经典伏笔回收链。每一条独立的伏笔链路必须生成一张独立卡片（生成 3~4 张卡片），按【埋线】->【呼应】->【回收】展开。
{evidence_instruction}"""
    elif dim == "world":
        task_instruction = f"""深入挖掘【{title}】背后的世界观底层潜规则、权力/金钱/阶层上升法则。每一个核心规则拆分为一张独立卡片（生成 3~4 张卡片）。
{evidence_instruction}"""
    elif dim == "technique":
        task_instruction = f"""深入挖掘【{title}】的视听反差蒙太奇、叙事技巧、信息差制造法。每一种核心技巧拆分为一张独立卡片（生成 3~4 张卡片）。
{evidence_instruction}"""
    else:
        task_instruction = f"""根据用户的特定要求：『{req.custom_prompt}』，从【{title}】中进行针对性提炼，将提炼出的每个重点条目分别生成独立卡片（生成 2~5 张卡片）。
{evidence_instruction}"""

    # 如果有上传的全本文档，作为首要事实依据
    context_prefix = ""
    if full_text:
        context_prefix = f"""【用户已上传全本文档全文（共计 {len(full_text)} 字）】：
===== 以下为原著全本文本内容 =====
{full_text}
===== 原著全本文本结束 =====

请以以上原著全文作为最严密的事实依据进行深度解构！\n\n"""

    prompt = f"""{context_prefix}你正在针对作品【{title}】（{meta}）进行工业级专业叙事拆解。
任务目标：
{task_instruction}

【必须遵守的输出格式】：
严格返回 JSON 数组，严禁生成任何额外解释或 Markdown 格式以外的废话：
[
  {{
    "category": "creation",
    "sub_type": "{dim}",
    "title": "具体角色名或条目标题（如：高启强人物极性档案 / 安欣良心镜像档案）",
    "source": "{title}",
    "scenario": "何时调用 / 适用场景描述（纯文本）",
    "content": "核心拆解内容（排版工整的分段纯文本字符串，严禁输出为对象或子字典）",
    "evidence": "原著或剧集真实名场面情节依据（标注章节场景，纯文本）",
    "tags": ["{title}", "{dim}"],
    "relations": [
      {{"source": "人物A", "target": "人物B", "relation": "关系性质（如：死敌/软肋/借势）", "desc": "博弈详情"}}
    ]
  }}
]"""

    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=300.0)
    cards = clean_and_parse_json(res)

    if not cards:
        print("[Warn] LLM 解析异常或未返回卡片")
        cards = [{
            "category": "creation",
            "sub_type": dim,
            "title": f"【{title}】专项解构",
            "source": title,
            "scenario": "请检查设置中的 API Key 是否有效",
            "content": "未能成功返回解析结果，请确认网络环境或配置后重试。",
            "evidence": "原著依据",
            "tags": [title, dim],
            "relations": []
        }]

    return {"cards": cards}

@app.post("/api/analyze")
@app.post("/api/deep_analyze")
async def analyze_core(req: UniversalAnalyzeRequest):
    text = req.content.strip()
    if not text:
        raise HTTPException(status_code=400, detail="输入不能为空")

    prompt = f"""用户在输入框中输入了素材：
"{text}"

请识别其本质并提炼为 2~3 张高价值独立资产卡片（包括 SOP 技能清单、认知逻辑、人物极性或经典金句）：
以严格的 JSON 数组格式返回：
[
  {{
    "category": "skill 或 knowledge 或 notes 或 creation",
    "sub_type": "character / foreshadow / skill_sop / logic / dialogue",
    "typeName": "分类中文名称",
    "title": "卡片标题（15字以内）",
    "source": "万能随记提炼",
    "scenario": "何时调用 / 适用场景描述",
    "content": "核心内容文本",
    "evidence": "依据片段或逻辑依据（尽量标注章节/场景）",
    "tags": ["标签1", "标签2"],
    "relations": []
  }}
]"""
    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=120.0)
    cards = clean_and_parse_json(res)
    if not cards:
        cards = [{
            "category": "skill",
            "sub_type": "skill_sop",
            "typeName": "我的技能 · SOP",
            "title": f"认知行动模型：{text[:10]}...",
            "source": "随记提炼",
            "scenario": "通用场景应对",
            "content": "E1. 提取核心矛盾\nE2. 设定单向检验点\nE3. 反馈沉淀入库",
            "evidence": "从原料逻辑抽象出的行动闭环",
            "tags": ["SOP", "行动指南"],
            "relations": []
        }]

    return {"cards": cards}

@app.post("/api/asset/save")
def save_asset(req: SaveAssetRequest, request: Request):
    user_id = extract_user_id(request)
    check_space_access(user_id, request)
    db = load_db(user_id)
    new_asset = {
        "id": f"asset-{int(time.time()*1000)}",
        "category": req.category,
        "sub_type": req.sub_type,
        "title": req.title,
        "source": req.source,
        "scenario": req.scenario,
        "content": req.content,
        "evidence": req.evidence,
        "tags": req.tags,
        "relations": req.relations or [],
        "created_at": time.strftime("%Y-%m-%d %H:%M")
    }
    db["assets"].insert(0, new_asset)
    save_db(db, user_id)
    return new_asset

@app.post("/api/asset/delete")
def delete_asset(req: DeleteAssetRequest, request: Request):
    user_id = extract_user_id(request)
    check_space_access(user_id, request)
    db = load_db(user_id)
    original_len = len(db.get("assets", []))
    db["assets"] = [a for a in db.get("assets", []) if a.get("id") != req.id]
    if len(db["assets"]) < original_len:
        save_db(db, user_id)
        return {"status": "success", "deleted_id": req.id}
    else:
        raise HTTPException(status_code=404, detail="未找到该卡片")

@app.post("/api/brainstorm")
async def run_brainstorm(req: BrainstormRequest):
    idea = req.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="想法不能为空")

    prompt = f"""四个具备跨领域顶级专业知识的专家，正在针对用户的奇思妙想展开深度头脑风暴会议：
用户抛出的想法：
"{idea}"

参会专家背景要求：
1. 【创作席·老辣商业编剧】：紧盯黄金钩子、视听语言、戏剧反差与爽感反转。
2. 【决策席·顶级战略操盘手】：关注底层博弈论、杠杆借势、风险隔离与反客为主的现实破局闭环。
3. 【成长席·敏锐社会心理学者】：深挖社会情绪共鸣、大众隐秘痛点与人性自我防御机制。
4. 【哲思席·冷峻荒诞派哲人】：打破常识盲区，提供反直觉、穿透认知的深刻洞见。

请输出这四位专家言之有物的激烈讨论与碰撞，最后由一位专家给出【终极落地综合方案】。
严格以 JSON 数组格式返回每一位专家的发言，方便用户随时提取任意一位专家的观点入库：
[
  {{
    "role": "创作席·商业编剧",
    "avatar_color": "text-cyan-400",
    "content": "专家的深度发言内容..."
  }},
  {{
    "role": "决策席·战略操盘手",
    "avatar_color": "text-emerald-400",
    "content": "专家的深度发言内容..."
  }},
  {{
    "role": "成长席·社会心理学者",
    "avatar_color": "text-amber-400",
    "content": "专家的深度发言内容..."
  }},
  {{
    "role": "哲思席·荒诞派哲人",
    "avatar_color": "text-purple-400",
    "content": "专家的深度发言内容..."
  }},
  {{
    "role": "终极合议落地方案",
    "avatar_color": "text-indigo-400 font-bold",
    "content": "融合各方视角的最终可落地执行大纲与解法..."
  }}
]
只输出合法 JSON 数组！"""

    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=120.0)
    rounds = clean_and_parse_json(res)

    if not rounds:
        rounds = [
            {"role": "创作席·商业编剧", "avatar_color": "text-cyan-400", "content": f"针对『{idea}』：第3秒必须把极端反差砸在脸上！制造双向信息差，让人物在谎言里越陷越深。"},
            {"role": "决策席·战略操盘手", "avatar_color": "text-emerald-400", "content": "关键是利益绑定与沉没成本。利用对手的傲慢，设立单向契约闭环。"},
            {"role": "成长席·社会心理学者", "avatar_color": "text-amber-400", "content": "这触碰了当下群体的情绪痛点，人物的卑微感越真实，反弹爆发力越强。"},
            {"role": "哲思席·荒诞派哲人", "avatar_color": "text-purple-400", "content": "荒诞的最高境界不是编造离奇，而是把真实的现实逻辑推向极致。"},
            {"role": "终极合议落地方案", "avatar_color": "text-indigo-400 font-bold", "content": "综合四方视角：前压后扬，以道具为支点触发反转，形成完整叙事闭环。"}
        ]

    return {"rounds": rounds}

@app.post("/api/gacha")
async def roll_gacha(req: GachaRequest, request: Request):
    user_id = extract_user_id(request)
    check_space_access(user_id, request)
    db = load_db(user_id)
    assets = db.get("assets", [])
    
    if req.anchor_asset_id:
        anchor = next((a for a in assets if a.get("id") == req.anchor_asset_id), None)
    else:
        anchor = None

    if anchor:
        anchor_desc = f"【指定骨架】《{anchor.get('title')}》（出处：{anchor.get('source')}）：{anchor.get('content')}"
        other_pool = [f"《{a.get('title')}》: {a.get('content')}" for a in assets if a.get("id") != req.anchor_asset_id]
        if other_pool:
            sample_other = random.choice(other_pool)
            material_text = f"{anchor_desc} ＋ 【配方原料】{sample_other}"
        else:
            material_text = f"{anchor_desc} ＋ 【社会热点】职场情绪撤退与借力逆袭"
    else:
        pool = [f"《{a.get('title','')}》（出处：{a.get('source','')}）: {a.get('content','')}" for a in assets]
        if not pool:
            pool = ["《狂飙》高启强人物黑化弧线", "《漫长的季节》红毛衣时空伏笔闭环"]
        sampled = random.sample(pool, min(len(pool), 2))
        material_text = " ＋ ".join(sampled)

    form_dict = {
        "novel": ("【SSR · 完整小说大纲】", "提取世界观、三幕式主支线、人物极性与颠覆性反转结尾"),
        "script": ("【SR · 60秒短剧分镜脚本】", "生成含镜头景别与时间戳的影视级分镜（黄金钩子/误解蓄水/核心反转/爆梗金句）"),
        "quote": ("【R · 穿透力刺痛金句】", "提炼 3 句极具毒舌或黑色幽默的影视高光台词与名场面"),
        "foreshadow": ("【SR · 跨时空伏笔因果链】", "设计三段式埋设->呼应->终局回收链路")
    }

    if req.output_form in form_dict:
        drawn_type, instruction = form_dict[req.output_form]
    else:
        drawn_type, instruction = random.choice(list(form_dict.values()))

    prompt = f"""灵感炼金机：
原料（来自已验证资产）：{material_text}
盲盒形态：{drawn_type}
创作要求：{instruction}
请给出高创意密度、视听感极强的落地生成结果："""

    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=120.0)
    if not res:
        res = f"基于原料 [{material_text}]\n抽中形态：{drawn_type}\n（本地演示输出，配置 API 后可全动态生成）"

    return {"type": drawn_type, "materials": material_text, "result": res}

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8899))
    if "PORT" not in os.environ:
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
        except Exception:
            pass
    uvicorn.run(app, host="0.0.0.0", port=port)
