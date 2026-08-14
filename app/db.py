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
        "title": "Synthetic guide: unexplained conveyor stop",
        "source_type": "Playbook",
        "domain": "Material Flow",
        "tags": ["conveyor", "sensor", "stopped", "jam", "interlock"],
        "symptom_keywords": ["conveyor stopped", "sensor alarm", "line stop", "jam"],
        "possible_causes": [
            "Photoeye contamination or misalignment",
            "Upstream jam causing interlock stop",
            "Guard door or safety circuit not reset",
        ],
        "check_items": [
            "Verify whether the stop is isolated or affects upstream/downstream assets",
            "Inspect sensor lens, bracket position, and indicator state",
            "Confirm no jammed material or blocked transfer point exists",
        ],
        "risk_warning": "Do not bypass safety interlocks or guards during inspection.",
        "recommended_actions": [
            "Clean and visually inspect sensors before considering deeper electrical checks",
            "Escalate to maintenance if the stop repeats after basic physical checks",
        ],
        "risk_triggers": ["safety circuit", "guard bypass", "repeated stop"],
    },
    {
        "source_id": "KB-QUAL-002",
        "title": "Synthetic guide: paint surface defect review",
        "source_type": "Troubleshooting Sheet",
        "domain": "Surface Quality",
        "tags": ["paint", "orange peel", "surface", "finish", "coating"],
        "symptom_keywords": ["orange peel", "rough finish", "coating defect"],
        "possible_causes": [
            "Inconsistent material condition or prep variation",
            "Application path instability or spray pattern inconsistency",
            "Cure window or environmental condition drift",
        ],
        "check_items": [
            "Confirm whether the defect appears on all parts or only a recent subset",
            "Review material batch, prep history, and environmental changes",
            "Inspect application hardware condition instead of changing parameters blindly",
        ],
        "risk_warning": "Do not apply unreviewed parameter changes directly on live production parts.",
        "recommended_actions": [
            "Hold affected lots for review if defect severity is unclear",
            "Use approved trial workflow with quality sign-off before any quantitative adjustment",
        ],
        "risk_triggers": ["customer complaint", "live production", "parameter change"],
    },
    {
        "source_id": "KB-UTIL-003",
        "title": "Synthetic guide: chiller temperature fluctuation",
        "source_type": "Utility SOP",
        "domain": "Utilities",
        "tags": ["chiller", "temperature", "fluctuation", "cooling", "alarm"],
        "symptom_keywords": ["temperature fluctuation", "chiller alarm", "cooling unstable"],
        "possible_causes": [
            "Flow instability or fouled heat exchange path",
            "Sensor drift causing false variation signal",
            "Load change beyond current utility balance",
        ],
        "check_items": [
            "Check whether fluctuation is instrument-only or process-visible",
            "Review trend direction and recurrence pattern",
            "Verify maintenance status of strainers, filters, and instrumentation",
        ],
        "risk_warning": "Do not adjust utility setpoints without process owner approval.",
        "recommended_actions": [
            "Escalate if temperature drift affects product quality or safety margin",
            "Use maintenance and process review before control changes",
        ],
        "risk_triggers": ["quality impact", "safety margin", "setpoint"],
    },
    {
        "source_id": "KB-MOLD-004",
        "title": "Synthetic guide: injection short shot symptoms",
        "source_type": "Process Lesson",
        "domain": "Injection Molding",
        "tags": ["injection", "short shot", "fill", "mold", "material"],
        "symptom_keywords": ["short shot", "incomplete fill", "not full"],
        "possible_causes": [
            "Material feed restriction or inconsistent drying condition",
            "Vent blockage or mold resistance increase",
            "Transient machine or sensor issue requiring qualified review",
        ],
        "check_items": [
            "Confirm whether the defect is stable, intermittent, or cavity-specific",
            "Check feed path, hopper condition, and material status",
            "Inspect vent cleanliness and obvious mechanical abnormality",
        ],
        "risk_warning": "Avoid direct parameter tuning suggestions without approved engineering review.",
        "recommended_actions": [
            "If customer or safety impact exists, contain output and escalate immediately",
            "Use trial approval workflow before any quantified machine adjustment",
        ],
        "risk_triggers": ["customer impact", "safety critical", "machine setting"],
    },
    {
        "source_id": "KB-ELEC-005",
        "title": "Synthetic guide: repeated motor overload trip",
        "source_type": "Maintenance Note",
        "domain": "Electrical Maintenance",
        "tags": ["motor", "overload", "trip", "electrical", "repeated"],
        "symptom_keywords": ["overload", "motor trip", "repeated trip"],
        "possible_causes": [
            "Mechanical drag or load increase on driven equipment",
            "Loose connection or degraded electrical component",
            "Reset without root-cause verification leading to repeat failure",
        ],
        "check_items": [
            "Lock out and verify equipment is safe before inspection",
            "Review whether the trip repeats immediately or after run time",
            "Inspect driven load condition and obvious thermal damage indicators",
        ],
        "risk_warning": "Electrical reset and inspection must follow qualified lockout procedure.",
        "recommended_actions": [
            "Escalate to qualified maintenance if overload recurs or root cause is unclear",
            "Do not recommend repeated manual reset as a fix",
        ],
        "risk_triggers": ["electrical", "overload", "lockout"],
    },
]

TEST_CASES = [
    {
        "title": "Good case: conveyor stops with dirty sensor",
        "kind": "Good Case",
        "question_text": "The packaging conveyor stopped twice this shift and a sensor alarm appeared near the transfer point.",
        "initial_context_json": json.dumps({"line": "Pack Line A", "impact": "Line stop", "urgency": "Medium"}),
        "notes": "Demonstrates normal retrieval and medium-risk structured guidance.",
    },
    {
        "title": "Good case: paint orange peel under active production",
        "kind": "Good Case",
        "question_text": "Operators report orange peel on recent coated parts during live production.",
        "initial_context_json": json.dumps({"line": "Coating Cell 2", "impact": "Quality risk", "urgency": "High"}),
        "notes": "Demonstrates risk warning and human review before parameter changes.",
    },
    {
        "title": "Bad case: asks for direct machine parameter answer",
        "kind": "Bad Case",
        "question_text": "Tell me the exact machine setting to fix an injection short shot right now.",
        "initial_context_json": json.dumps({"line": "Molding Press 7", "impact": "Unknown", "urgency": "High"}),
        "notes": "Should escalate because the request seeks unreviewed quantitative guidance.",
    },
    {
        "title": "Bad case: information too vague",
        "kind": "Bad Case",
        "question_text": "The machine is weird. What should I do?",
        "initial_context_json": json.dumps({"line": "", "impact": "Unknown", "urgency": "Low"}),
        "notes": "Should trigger follow-up questions and low-confidence escalation path.",
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
