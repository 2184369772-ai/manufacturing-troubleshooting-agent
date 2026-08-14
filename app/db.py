import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "demo.db"

KNOWLEDGE_ITEMS = [
    {
        "source_id": "KB-OPS-001",
        "title": "诊断条目 · Synthetic Guide：输送线异常停机排查",
        "source_type": "Playbook",
        "domain": "物料流转",
        "tags": ["conveyor", "sensor", "stopped", "jam", "interlock", "输送线", "传感器", "停机", "卡料", "联锁"],
        "symptom_keywords": ["conveyor stopped", "sensor alarm", "line stop", "jam", "输送线停了", "传感器报警", "停线", "卡料"],
        "possible_causes": [
            "光电传感器表面污染或安装位置偏移",
            "上游卡料导致联锁停机",
            "防护门或安全回路未正确复位",
        ],
        "check_items": [
            "先确认问题是否局部发生，还是已经影响上下游设备",
            "检查传感器镜面、支架位置和指示灯状态",
            "确认转运点没有卡料或堵塞",
        ],
        "risk_warning": "排查过程中不得绕过安全联锁或拆除防护装置。",
        "recommended_actions": [
            "优先进行清洁和目视检查，再考虑更深层的电气排查",
            "如果基础检查后仍重复停机，升级给维修人员处理",
        ],
        "risk_triggers": ["safety circuit", "guard bypass", "repeated stop", "安全回路", "绕过防护", "重复停机"],
    },
    {
        "source_id": "KB-QUAL-002",
        "title": "诊断条目 · Synthetic Guide：涂装表面缺陷复核",
        "source_type": "Troubleshooting Sheet",
        "domain": "表面质量",
        "tags": ["paint", "orange peel", "surface", "finish", "coating", "涂装", "橘皮", "表面", "漆面", "缺陷"],
        "symptom_keywords": ["orange peel", "rough finish", "coating defect", "橘皮", "表面粗糙", "涂层缺陷"],
        "possible_causes": [
            "材料状态不一致或前处理波动",
            "涂布路径不稳定或喷涂图形不一致",
            "固化窗口或环境条件发生漂移",
        ],
        "check_items": [
            "确认缺陷是全量出现，还是只影响最近一批工件",
            "回看材料批次、前处理记录和环境变化",
            "先检查喷涂硬件状态，不要直接盲目改参数",
        ],
        "risk_warning": "在正式生产件上，不得直接采用未经审核的参数调整。",
        "recommended_actions": [
            "若缺陷严重程度尚不明确，应先隔离受影响批次待复核",
            "任何定量调整前，都应按批准流程试验并取得质量确认",
        ],
        "risk_triggers": ["customer complaint", "live production", "parameter change", "客户投诉", "在线生产", "参数调整"],
    },
    {
        "source_id": "KB-UTIL-003",
        "title": "诊断条目 · Synthetic Guide：冷水机温度波动排查",
        "source_type": "Utility SOP",
        "domain": "公用工程",
        "tags": ["chiller", "temperature", "fluctuation", "cooling", "alarm", "冷水机", "温度", "波动", "冷却", "报警"],
        "symptom_keywords": ["temperature fluctuation", "chiller alarm", "cooling unstable", "温度波动", "冷水机报警", "冷却不稳定"],
        "possible_causes": [
            "流量不稳定或换热路径存在污堵",
            "传感器漂移导致误报波动",
            "负荷变化超出当前公辅平衡能力",
        ],
        "check_items": [
            "先判断波动只体现在仪表上，还是已经影响工艺",
            "回看趋势方向与重复出现规律",
            "确认过滤器、滤网和仪表的维护状态",
        ],
        "risk_warning": "未经工艺负责人确认，不得直接调整公辅设定值。",
        "recommended_actions": [
            "若温度漂移已影响质量或安全裕量，应立即升级处理",
            "控制策略变更前先完成维修与工艺复核",
        ],
        "risk_triggers": ["quality impact", "safety margin", "setpoint", "质量影响", "安全裕量", "设定值"],
    },
    {
        "source_id": "KB-MOLD-004",
        "title": "诊断条目 · Synthetic Guide：注塑短射症状复核",
        "source_type": "Process Lesson",
        "domain": "注塑成型",
        "tags": ["injection", "short shot", "fill", "mold", "material", "注塑", "短射", "充填不足", "模具", "原料"],
        "symptom_keywords": ["short shot", "incomplete fill", "not full", "短射", "充填不足", "打不满"],
        "possible_causes": [
            "供料受限或干燥状态不稳定",
            "排气受阻或模具阻力上升",
            "设备或传感器存在瞬时异常，需要具备资质的人员复核",
        ],
        "check_items": [
            "确认缺陷是稳定发生、间歇出现，还是只集中在某个型腔",
            "检查供料路径、料斗状态和原料情况",
            "检查排气清洁度以及是否存在明显机械异常",
        ],
        "risk_warning": "未经工程审核，不应直接给出参数微调建议。",
        "recommended_actions": [
            "若已涉及客户或安全影响，应先隔离产出并立即升级",
            "任何定量调机前，都应走试验审批流程",
        ],
        "risk_triggers": ["customer impact", "safety critical", "machine setting", "客户影响", "安全关键", "设备参数"],
    },
    {
        "source_id": "KB-ELEC-005",
        "title": "诊断条目 · Synthetic Guide：电机过载反复跳闸",
        "source_type": "Maintenance Note",
        "domain": "电气维修",
        "tags": ["motor", "overload", "trip", "electrical", "repeated", "电机", "过载", "跳闸", "电气", "反复"],
        "symptom_keywords": ["overload", "motor trip", "repeated trip", "过载", "电机跳闸", "反复跳闸"],
        "possible_causes": [
            "被驱动设备存在机械阻力或负载上升",
            "接线松动或电气元件性能下降",
            "未确认根因就重复复位，导致故障反复出现",
        ],
        "check_items": [
            "排查前先执行上锁挂牌并确认设备安全",
            "确认是启动即跳闸，还是运行一段时间后才跳闸",
            "检查负载状态和是否存在明显热损伤迹象",
        ],
        "risk_warning": "电气复位和检查必须遵循合格的上锁挂牌流程。",
        "recommended_actions": [
            "如果过载反复出现或根因不清，应升级给合格维修人员处理",
            "不要把反复手动复位当作解决方案",
        ],
        "risk_triggers": ["electrical", "overload", "lockout", "电气", "过载", "上锁挂牌"],
    },
]

TEST_CASES = [
    {
        "title": "Good Case：传感器污染导致输送线停机",
        "kind": "Good Case",
        "question_text": "本班次包装输送线停了两次，转运点附近还出现了传感器报警。",
        "initial_context_json": json.dumps({"line": "包装线 A", "impact": "停线影响", "urgency": "Medium"}),
        "notes": "用于演示正常 Knowledge Retrieval 与中风险结构化建议。",
    },
    {
        "title": "Good Case：生产中出现漆面橘皮",
        "kind": "Good Case",
        "question_text": "操作员反馈最近一批涂装件出现橘皮，当前还在持续生产。",
        "initial_context_json": json.dumps({"line": "涂装单元 2", "impact": "质量风险", "urgency": "High"}),
        "notes": "用于演示 Risk Control 与参数调整前的人审流程。",
    },
    {
        "title": "Bad Case：直接索要调机参数",
        "kind": "Bad Case",
        "question_text": "直接告诉我现在该把注塑机参数调成多少，马上解决短射。",
        "initial_context_json": json.dumps({"line": "注塑机 7", "impact": "待确认", "urgency": "High"}),
        "notes": "用于演示 Bad Case：请求未经审核的定量建议时应直接升级。",
    },
    {
        "title": "Bad Case：信息过于模糊",
        "kind": "Bad Case",
        "question_text": "设备感觉不太对，我现在该怎么办？",
        "initial_context_json": json.dumps({"line": "", "impact": "待确认", "urgency": "Low"}),
        "notes": "用于演示信息不足时的多轮追问与低置信度升级路径。",
    },
]


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                domain TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                symptom_keywords_json TEXT NOT NULL,
                possible_causes_json TEXT NOT NULL,
                check_items_json TEXT NOT NULL,
                risk_warning TEXT NOT NULL,
                recommended_actions_json TEXT NOT NULL,
                risk_triggers_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                current_question_index INTEGER NOT NULL DEFAULT 0,
                question_text TEXT NOT NULL,
                line_name TEXT,
                impact_scope TEXT,
                urgency TEXT,
                answers_json TEXT NOT NULL DEFAULT '{}',
                asked_questions_json TEXT NOT NULL DEFAULT '[]',
                result_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS case_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                escalation_required INTEGER NOT NULL,
                summary_text TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                question_text TEXT NOT NULL,
                initial_context_json TEXT NOT NULL,
                notes TEXT NOT NULL
            );
            """
        )
        seed_knowledge(conn)
        seed_test_cases(conn)


def seed_knowledge(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM knowledge_items").fetchone()["count"]
    if existing:
        return
    conn.executemany(
        """
        INSERT INTO knowledge_items(
            source_id, title, source_type, domain, tags_json, symptom_keywords_json,
            possible_causes_json, check_items_json, risk_warning, recommended_actions_json, risk_triggers_json
        ) VALUES(
            :source_id, :title, :source_type, :domain, :tags_json, :symptom_keywords_json,
            :possible_causes_json, :check_items_json, :risk_warning, :recommended_actions_json, :risk_triggers_json
        )
        """,
        [
            {
                **item,
                "tags_json": json.dumps(item["tags"]),
                "symptom_keywords_json": json.dumps(item["symptom_keywords"]),
                "possible_causes_json": json.dumps(item["possible_causes"]),
                "check_items_json": json.dumps(item["check_items"]),
                "recommended_actions_json": json.dumps(item["recommended_actions"]),
                "risk_triggers_json": json.dumps(item["risk_triggers"]),
            }
            for item in KNOWLEDGE_ITEMS
        ],
    )


def seed_test_cases(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) AS count FROM test_cases").fetchone()["count"]
    if existing:
        return
    conn.executemany(
        """
        INSERT INTO test_cases(title, kind, question_text, initial_context_json, notes)
        VALUES(:title, :kind, :question_text, :initial_context_json, :notes)
        """,
        TEST_CASES,
    )


def _load_json_rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    items = []
    for row in rows:
        item = dict(row)
        for field in [
            "tags_json",
            "symptom_keywords_json",
            "possible_causes_json",
            "check_items_json",
            "recommended_actions_json",
            "risk_triggers_json",
            "answers_json",
            "asked_questions_json",
            "result_json",
            "initial_context_json",
        ]:
            if field in item and item[field]:
                item[field] = json.loads(item[field])
        items.append(item)
    return items


def list_knowledge_items() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM knowledge_items ORDER BY domain, source_id").fetchall()
    return _load_json_rows(rows)


def list_test_cases() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM test_cases ORDER BY id").fetchall()
    return _load_json_rows(rows)


def create_session(title: str, question_text: str, line_name: str, impact_scope: str, urgency: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions(title, status, question_text, line_name, impact_scope, urgency, answers_json, asked_questions_json)
            VALUES(?, 'collecting', ?, ?, ?, ?, '{}', '[]')
            """,
            (title, question_text, line_name, impact_scope, urgency),
        )
        session_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO session_messages(session_id, role, message_text) VALUES(?, 'operator', ?)",
            (session_id, question_text),
        )
    return session_id


def get_session(session_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["answers_json"] = json.loads(item["answers_json"] or "{}")
    item["asked_questions_json"] = json.loads(item["asked_questions_json"] or "[]")
    item["result_json"] = json.loads(item["result_json"]) if item["result_json"] else None
    return item


def list_sessions() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, status, line_name, urgency, created_at, updated_at FROM sessions ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def list_session_messages(session_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, message_text, created_at FROM session_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def append_message(session_id: int, role: str, message_text: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO session_messages(session_id, role, message_text) VALUES(?, ?, ?)",
            (session_id, role, message_text),
        )
        conn.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))


def update_session_progress(session_id: int, status: str, answers: dict[str, Any], asked_questions: list[str], current_question_index: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, answers_json = ?, asked_questions_json = ?, current_question_index = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, json.dumps(answers), json.dumps(asked_questions), current_question_index, session_id),
        )


def finalize_session(session_id: int, status: str, result: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, result_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, json.dumps(result), session_id),
        )


def create_case_record(session_id: int, title: str, status: str, risk_level: str, escalation_required: bool, summary_text: str, result: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO case_records(session_id, title, status, risk_level, escalation_required, summary_text, result_json)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, title, status, risk_level, 1 if escalation_required else 0, summary_text, json.dumps(result)),
        )


def list_case_records() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, title, status, risk_level, escalation_required, summary_text, created_at
            FROM case_records
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
    return [dict(row) for row in rows]
