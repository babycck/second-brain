import os
import sys
import json
import random
import time
import re
import urllib.parse
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
    raw = str(user_id).strip()
    try:
        raw = urllib.parse.unquote(raw)
    except Exception:
        pass
    # 剥离 QQ / 微信拦截跳转页带入的冗余文字
    raw = re.sub(r'(申请恢复访问|客服指引|查看规则|非官方页面|已停止访问).*$', '', raw).strip()
    # 识别 QQ 复制剥离了 % 的 hex 编码 (如 E998BFE696AFE58DA1 -> 阿斯卡)
    if re.match(r'^[0-9A-Fa-f]{6,}$', raw) and len(raw) % 2 == 0:
        try:
            decoded = bytes.fromhex(raw).decode('utf-8')
            if decoded:
                raw = decoded
        except Exception:
            pass
    clean = re.sub(r'[^\w\u4e00-\u9fa5_-]', '', raw).strip()
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
            "admin_device_key": "bbk8899",
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
            if "admin_device_key" not in cfg or not cfg["admin_device_key"]:
                cfg["admin_device_key"] = "bbk8899"
            return cfg
    except Exception:
        return {"admin_user": ADMIN_USER, "admin_device_key": "bbk8899", "allowed_spaces": [ADMIN_USER]}

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
    cfg = load_system_config()
    device_token = (
        request.headers.get("X-Admin-Device-Token")
        or request.query_params.get("token")
        or request.query_params.get("key")
        or ""
    ).strip()
    try:
        device_token = urllib.parse.unquote(device_token)
    except Exception:
        pass
    expected_key = cfg.get("admin_device_key", "bbk8899").strip()
    return bool(expected_key and device_token == expected_key)

def check_space_access(user_id: str, request: Request):
    clean_user = sanitize_user_id(user_id)

    # 1. 尝试访问管理员主空间：必须具备管理员专属绑定的设备密钥
    if clean_user in [ADMIN_USER, "admin", "default"]:
        if not is_admin_user(request):
            raise HTTPException(
                status_code=403,
                detail="【权限拒绝】未授权设备，禁止访问该私密空间！"
            )
        return True

    # 2. 访问普通好友空间：必须由管理员预先授权开通
    cfg = load_system_config()
    allowed = cfg.get("allowed_spaces", [])
    target_file = get_user_db_path(clean_user)
    if clean_user not in allowed and not os.path.exists(target_file):
        raise HTTPException(
            status_code=403,
            detail=f"【空间未开通】专属空间『{clean_user}』尚未开通！请联系管理员获取专属访问链接。"
        )
    return True

class UpdateDeviceKeyRequest(BaseModel):
    old_key: str
    new_key: str

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

class BrainstormChatRequest(BaseModel):
    message: str
    locked_work: Optional[str] = ""
    context_doc: Optional[str] = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)
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

def clean_and_parse_dict(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(text, strict=False)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            data = json.loads(text[s:e+1], strict=False)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return None
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

@app.get("/api/admin/check_auth")
def check_admin_auth(request: Request):
    return {"is_admin": is_admin_user(request)}

@app.get("/api/admin/spaces")
def list_spaces(request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="【设备未授权】无权查看管理列表")
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
        raise HTTPException(status_code=403, detail="【设备未授权】无权创建或分享空间！")
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
        raise HTTPException(status_code=403, detail="【设备未授权】无权删除空间！")
    space_name = sanitize_user_id(req.space_name)
    if space_name in [ADMIN_USER, "admin", "default"]:
        raise HTTPException(status_code=400, detail="不可删除主管理员空间")

    cfg = load_system_config()
    cfg["allowed_spaces"] = [s for s in cfg["allowed_spaces"] if s != space_name]
    save_system_config(cfg)
    return {"status": "ok", "deleted_space": space_name}

@app.post("/api/admin/device_key/update")
def update_device_key(req: UpdateDeviceKeyRequest, request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="【设备未授权】无权修改设备密钥")
    cfg = load_system_config()
    cur_key = cfg.get("admin_device_key", "bbk8899").strip()
    if req.old_key.strip() != cur_key:
        raise HTTPException(status_code=400, detail="旧设备密钥不正确，修改失败")
    if not req.new_key.strip():
        raise HTTPException(status_code=400, detail="新密钥不能为空")
    cfg["admin_device_key"] = req.new_key.strip()
    save_system_config(cfg)
    return {"status": "ok", "message": "设备专属密钥修改成功！"}

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

@app.post("/api/brainstorm/chat")
async def brainstorm_chat(req: BrainstormChatRequest, request: Request):
    user_id = extract_user_id(request)
    check_space_access(user_id, request)

    msg = req.message.strip()
    if not msg and not req.context_doc:
        raise HTTPException(status_code=400, detail="对话内容或复盘材料不能为空")

    history_snippets = []
    for h in req.history[-6:]:
        r = h.get("role", "user")
        c = h.get("content", "")
        if r == "user":
            history_snippets.append(f"【用户提出/反驳】：{c}")
        elif r == "council":
            history_snippets.append(f"【圆桌专家发言】：{c}")

    history_text = "\n".join(history_snippets) if history_snippets else "（新开启的复盘对话）"

    doc_context = ""
    if req.context_doc and req.context_doc.strip():
        clipped_doc = req.context_doc.strip()[:15000]
        doc_context = f"\n\n【用户上传的附加复盘剧本/大纲材料】：\n{clipped_doc}\n"

    locked_context = ""
    if req.locked_work and req.locked_work.strip():
        locked_context = f"\n【用户已锁定核心作品全案】：『{req.locked_work.strip()}』\n智囊团全员已获知该作品锁定状态，后续请务必深度围绕该作品的真实凶案手法、核心诡计、时间差逻辑、博弈与名场面进行推演！\n"

    prompt = f"""你是由5位风格鲜明、跨越全生命周期的顶级智囊构成的【AI 专家圆桌复盘委员会】。
当前研讨历史脉络：
{history_text}
{doc_context}
{locked_context}
用户最新抛出的内容/复盘线索/反驳质疑：
"{msg}"

【研讨核心工作准则】：
1. 【作品模糊溯源与全案检索】：
   - 如果用户提到任何真实存在的具体作品（如剧本杀《年轮》《苍岐》《搞钱》《须臾》《死者在幻夜中醒来》、综艺《明星大侦探》《极限挑战》《大侦探》《密室大逃脱》、热门游戏《艾尔登法环》《底特律:变人》《赛博朋克2077》、影视动画或真实社会大案/小红书热点）：
   - 充分调动你的海量知识库，主动调取并精准定位该作品的【核心诡计手法】、【作案时间差/伪证链】、【高光博弈反差】、【规则破坏机制】、【标志性名场面】进行硬核复盘拆解！
   - 即使用户只说了模糊的名字或一句话，也要以行家的敏锐度，把该作品最封神、最精彩的底层机制还原出来。
2. 【高情商机智反驳（绝不人身攻击，幽默且充满干货）】：
   - 如果用户重点引用了某个席位（如 `@【5岁小孩】` 或 `@【80岁老者】`）或提出了质疑反驳：
   - 该席位专家必须优先正面回应，展现各自独特、生动且幽默的人设性格（5岁小孩天真委屈又一语扎心，80岁老者看透世态慈祥通透，星座大师从心理防卫归因切入，老辣编剧拍大腿兴奋改戏，战略家冷静列出博弈成本）；
   - 严禁任何粗鄙、人身攻击词汇，完全是对事不对人的智慧交锋！
3. 【五大常驻席位人设】：
   - 席位 1：【🎬 主创席·老辣编剧】（avatar_color: "text-rose-400"）
     聚焦：黄金前3秒钩子、视听戏剧冲突、叙事视角反转、观众情绪过山车与爽点痛点。
   - 席位 2：【♟️ 决策席·战略操盘手】（avatar_color: "text-cyan-400"）
     聚焦：底层博弈论、利益链捆绑、风险隔离、单向契约、压哨背叛与现实借力打力闭环。
   - 席位 3：【🔮 玄机席·星座/MBTI大师】（avatar_color: "text-purple-400"）
     聚焦：星座星盘特质、MBTI人格暗面（如INTJ隐忍/ENFP黑化）、人设隐秘动机与宿命因果。
   - 席位 4：【🎈 纯真席·5岁小孩】（avatar_color: "text-amber-400"）
     聚焦：天真可爱、零成人阅历、童言无忌、用最纯粹的儿童直觉一语戳破大人的套路与皇帝新装。
   - 席位 5：【🍵 岁月席·80岁老者】（avatar_color: "text-emerald-400"）
     聚焦：活了八十年阅尽沧海桑田、生死百态、人间悲悯、看透名利荒诞，直指人心深处放不下的执念。

【输出格式要求】：
严格输出合法的 JSON 对象，格式如下：
{{
  "detected_work": "识别出的作品名（如：剧本杀《年轮》）或'原创灵感脑洞'",
  "detected_hint": "推测作品一句话简介（如：经典硬核推理剧本杀《年轮》，核心在于时间线伪证与视角盲区闭环）",
  "council_topic": "一句话提炼本次交锋的核心焦点",
  "speeches": [
    {{
      "expert_role": "🎬 主创席·老辣编剧",
      "avatar_color": "text-rose-400",
      "dialogue": "编剧视角的生动发言，老辣直接，直击戏剧高光...",
      "card": {{
        "title": "提炼资产标题（8-16字，如：黄金前三秒反差与叙事视角欺骗）",
        "category": "钩子",
        "content": "抽离出来的可复用创作法则（80-150字）...",
        "scenario": "反转设计、悬疑短剧、名场面开局",
        "source": "作品名",
        "evidence": "剧情或名场面依据",
        "tags": ["反差钩子", "叙事反转"]
      }}
    }},
    {{
      "expert_role": "♟️ 决策席·战略操盘手",
      "avatar_color": "text-cyan-400",
      "dialogue": "操盘手视角的利益与博弈剖析...",
      "card": {{
        "title": "资产标题（如：单向契约陷阱与压哨背叛机制）",
        "category": "对抗",
        "content": "抽离出来的博弈/利益法则...",
        "scenario": "阵营战、利益分配、社交博弈",
        "source": "作品名",
        "evidence": "博弈名场面证据",
        "tags": ["利益博弈", "背叛机制"]
      }}
    }},
    {{
      "expert_role": "🔮 玄机席·星座/MBTI大师",
      "avatar_color": "text-purple-400",
      "dialogue": "星座星盘与MBTI暗面动机剖析...",
      "card": {{
        "title": "资产标题（如：INTJ隐忍型人格的代偿性宿命）",
        "category": "动机",
        "content": "抽离出来的性格与宿命动机法则...",
        "scenario": "人设塑造、黑化动机、深层心理防御",
        "source": "作品名",
        "evidence": "角色心理表现依据",
        "tags": ["MBTI", "性格暗面", "人设玄机"]
      }}
    }},
    {{
      "expert_role": "🎈 纯真席·5岁小孩",
      "avatar_color": "text-amber-400",
      "dialogue": "天真软萌的童言发言，直击大人的逻辑盲区...",
      "card": {{
        "title": "资产标题（如：儿童纯粹直觉与皇帝新装法则）",
        "category": "规则",
        "content": "用最直白的直觉推导出的反常识本质...",
        "scenario": "破除思维定势、降维幽默、直觉解谜",
        "source": "作品名",
        "evidence": "天真直觉对应的真实破绽",
        "tags": ["童言直觉", "反套路"]
      }}
    }},
    {{
      "expert_role": "🍵 岁月席·80岁老者",
      "avatar_color": "text-emerald-400",
      "dialogue": "看尽人间冷暖的慈祥沧桑发言，句句入骨...",
      "card": {{
        "title": "资产标题（如：执念的虚妄与生命因果轮回）",
        "category": "世界观",
        "content": "抽离出来的生命阅历与沉痛洞察法则...",
        "scenario": "终极立意、悲剧内核、历史沉淀",
        "source": "作品名",
        "evidence": "岁月悲悯的现实投射",
        "tags": ["人生哲思", "深层立意"]
      }}
    }}
  ],
  "council_summary": "圆桌专家合议终极落地方案，或下一步演化指引"
}}
注意：不要输出任何 markdown 格式标记（如 ```json），只输出纯 JSON！"""

    res = await call_llm(prompt, req.api_key, req.base_url, req.model, timeout_sec=120.0)
    data = clean_and_parse_dict(res)

    if not data or not isinstance(data, dict) or not data.get("speeches"):
        detected = "作品复盘" if any(k in msg for k in ["剧本杀", "综艺", "电影", "游戏", "年轮"]) else "原创脑洞探讨"
        data = {
            "detected_work": detected,
            "detected_hint": f"针对『{msg[:25]}』的核心机制深度多维复盘",
            "council_topic": f"针对『{msg[:30]}』的深度多维复盘",
            "speeches": [
                {
                    "expert_role": "🎬 主创席·老辣编剧",
                    "avatar_color": "text-rose-400",
                    "dialogue": f"针对『{msg}』：前3秒必须把极端反差砸在脸上！制造双向信息差，让人物在谎言里越陷越深，反转才足够炸裂！",
                    "card": {
                        "title": "黄金前三秒反差与叙事视角欺骗",
                        "category": "钩子",
                        "content": "利用观众对‘既定事实’的盲信作为障眼法，主视角的隐瞒正是揭开反转时最大震撼的来源。",
                        "scenario": "剧情高潮设计、反派反转、爽点爆发",
                        "source": detected,
                        "evidence": "受众情绪震荡与视角反转节点",
                        "tags": ["反差钩子", "叙事反转"]
                    }
                },
                {
                    "expert_role": "♟️ 决策席·战略操盘手",
                    "avatar_color": "text-cyan-400",
                    "dialogue": "光有剧情还不够，底层博弈才是骨架！表面建立不可破的利益同盟，但在倒计时最后一刻完成背叛，这才是利益最大化。",
                    "card": {
                        "title": "单向契约陷阱与压哨背叛机制",
                        "category": "对抗",
                        "content": "表面建立绝对同盟，将关键决定权拖入倒计时最后一刻，利用规则盲区完成背叛以实现通吃。",
                        "scenario": "阵营博弈、谍战交锋、真人秀赛制",
                        "source": detected,
                        "evidence": "利益博弈与背叛闭环",
                        "tags": ["利益博弈", "背叛机制"]
                    }
                },
                {
                    "expert_role": "🔮 玄机席·星座/MBTI大师",
                    "avatar_color": "text-purple-400",
                    "dialogue": "从人设心理学看，这个角色的 INTJ 属性极强！隐忍、理性却偏执，表面是为了大局，骨子里是天蝎座复仇的因果还债。",
                    "card": {
                        "title": "INTJ隐忍型人格的代偿性宿命",
                        "category": "动机",
                        "content": "高智商角色在压抑童年后形成极端的逻辑自洽，一切疯狂行为在他们内心都是正义的因果报偿。",
                        "scenario": "人设塑造、黑化动机、深层心理防御",
                        "source": detected,
                        "evidence": "性格与星盘动机映射",
                        "tags": ["MBTI", "性格暗面", "人设玄机"]
                    }
                },
                {
                    "expert_role": "🎈 纯真席·5岁小孩",
                    "avatar_color": "text-amber-400",
                    "dialogue": "这个叔叔藏得那么累，为什么不直接说实话呢？做错事的小朋友都知道要道歉，大人怎么比我们还害怕承认呀？",
                    "card": {
                        "title": "儿童纯粹直觉与皇帝新装法则",
                        "category": "规则",
                        "content": "当成年人都在复杂的套路和借口中打转时，直白指出最核心的物理事实往往能瞬间击穿一切谎言。",
                        "scenario": "破除思维定势、降维幽默、直觉解谜",
                        "source": detected,
                        "evidence": "童真直觉击穿虚妄谎言",
                        "tags": ["童言直觉", "反套路"]
                    }
                },
                {
                    "expert_role": "🍵 岁月席·80岁老者",
                    "avatar_color": "text-emerald-400",
                    "dialogue": "呵呵呵，老头子我活了八十年才懂，人这一辈子最放不下的不是金银名利，而是那口咽不下的执念啊。争到最后，不过是一抔黄土。",
                    "card": {
                        "title": "执念的虚妄与生命因果轮回",
                        "category": "世界观",
                        "content": "极致悲剧的内核不是坏人作恶，而是好人在命运洪流中拼尽全力守护执念，最终却成为悲剧的一环。",
                        "scenario": "终极立意、悲剧内核、历史沉淀",
                        "source": detected,
                        "evidence": "岁月沉淀的人间悲悯",
                        "tags": ["人生哲思", "深层立意"]
                    }
                }
            ],
            "council_summary": "五大席位达成共识：该议题融合了老辣博弈、玄学性格、童真破局与沧桑立意，具备极高沉淀价值！"
        }

    if req.locked_work and req.locked_work.strip():
        data["detected_work"] = req.locked_work.strip()

    return data

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
