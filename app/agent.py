from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db import list_knowledge_items


FOLLOW_UPS = [
    {
        "key": "symptom_scope",
        "question": "这个问题是偶发、重复出现，还是已经影响多个工位 / 多个零件？",
    },
    {
        "key": "recent_change",
        "question": "最近有没有变化，例如原料、设备状态、环境、排产，或者看起来没有明显变化？",
    },
    {
        "key": "safety_quality_impact",
        "question": "当前是否已经涉及安全、客户质量，或者需要隔离 / 围堵处理？",
    },
]


@dataclass
class RetrievalResult:
    item: dict[str, Any]
    score: int


def normalize_words(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {word for word in cleaned.split() if len(word) > 2}


def retrieve_knowledge(question_text: str, answers: dict[str, str], top_n: int = 3) -> list[RetrievalResult]:
    corpus = " ".join([question_text] + [str(v) for v in answers.values()])
    words = normalize_words(corpus)
    lowered_corpus = corpus.lower()
    results: list[RetrievalResult] = []
    for item in list_knowledge_items():
        bag = set(item["tags_json"]) | set(item["symptom_keywords_json"]) | normalize_words(item["title"]) | normalize_words(item["domain"])
        lowered_bag = {w.lower() for w in bag}
        score = len(words & lowered_bag)
        score += sum(1 for term in lowered_bag if len(term) >= 2 and term in lowered_corpus)
        if score:
            results.append(RetrievalResult(item=item, score=score))
    results.sort(key=lambda entry: (-entry.score, entry.item["source_id"]))
    return results[:top_n]


def required_follow_up_count(question_text: str) -> int:
    text = question_text.lower()
    if len(text.split()) < 5:
        return len(FOLLOW_UPS)
    if any(term in text for term in ["exact setting", "machine setting", "parameter", "setpoint", "speed", "pressure", "temperature adjustment", "精确参数", "直接参数", "调机参数", "设定值", "速度", "压力", "温度调整"]):
        return 1
    return 2


def next_follow_up(question_text: str, answers: dict[str, str], asked_questions: list[str]) -> dict[str, str] | None:
    needed = required_follow_up_count(question_text)
    if len(asked_questions) >= needed:
        return None
    for item in FOLLOW_UPS:
        if item["key"] not in answers:
            return item
    return None


def build_result(question_text: str, line_name: str, impact_scope: str, urgency: str, answers: dict[str, str]) -> dict[str, Any]:
    retrieved = retrieve_knowledge(question_text, answers)
    lower_bundle = " ".join([question_text, line_name, impact_scope, urgency] + list(answers.values())).lower()

    info_insufficient = len(answers) < required_follow_up_count(question_text)
    no_knowledge = len(retrieved) == 0
    direct_parameter_request = any(term in lower_bundle for term in ["exact setting", "machine setting", "parameter", "setpoint", "temperature to", "pressure to", "speed to", "精确参数", "调机参数", "直接给参数", "设定值", "温度调到", "压力调到", "速度调到"])
    safety_or_quality_risk = any(term in lower_bundle for term in ["safety", "injury", "smoke", "electrical", "customer", "containment", "fire", "安全", "受伤", "冒烟", "电气", "客户", "隔离", "起火"])
    repeated_or_unknown = any(term in lower_bundle for term in ["repeated", "again", "unknown", "not sure", "unclear", "重复", "再次", "不清楚", "不确定", "未知"])

    risk_level = "Low"
    if direct_parameter_request or safety_or_quality_risk:
        risk_level = "High"
    elif info_insufficient or repeated_or_unknown or urgency.lower() == "high":
        risk_level = "Medium"

    escalation_required = direct_parameter_request or safety_or_quality_risk or info_insufficient or no_knowledge

    possible_causes: list[str] = []
    check_items: list[str] = []
    knowledge_sources: list[dict[str, Any]] = []
    source_warnings: list[str] = []

    for hit in retrieved:
        item = hit.item
        for value in item["possible_causes_json"]:
            if value not in possible_causes:
                possible_causes.append(value)
        for value in item["check_items_json"]:
            if value not in check_items:
                check_items.append(value)
        knowledge_sources.append(
            {
                "source_id": item["source_id"],
                "title": item["title"],
                "source_type": item["source_type"],
                "domain": item["domain"],
                "relevance_score": hit.score,
            }
        )
        if item["risk_warning"] not in source_warnings:
            source_warnings.append(item["risk_warning"])

    if not possible_causes:
        possible_causes = [
            "当前信息仍不足，暂时无法形成可信的原因候选清单。",
            "现有描述可能覆盖了多种失效模式，需要具备资质的人员进一步确认。",
        ]
    if not check_items:
        check_items = [
            "先明确受影响的设备 / 工序位置",
            "确认问题是否重复发生以及影响范围",
            "由于知识覆盖不足，升级给具备资质的负责人处理",
        ]

    recommendation_prefix = "以下内容仅作为结构化复核参考，不应被视为自动执行指令。"
    recommended_actions = [
        recommendation_prefix,
        "在进行任何调整前，先从设备或工序层面核实现场现象。",
        "如果问题可能影响安全、质量或设备健康，应遵循批准后的排查与试验流程。",
    ]
    if escalation_required:
        recommended_actions.append("在此停止自主建议，转入人工审核 / 升级流程。")

    risk_warning = "根据当前 Synthetic Data 输入，暂未识别出明确的即时高风险模式。"
    if source_warnings:
        risk_warning = source_warnings[0]
    if direct_parameter_request:
        risk_warning = "当前请求直接索要定量调机建议。这个 Demo 会主动升级，而不会输出未经审核的设备参数。"
    elif info_insufficient:
        risk_warning = "当前信息仍不完整。任何高风险动作都应先经过人工审核。"
    elif no_knowledge:
        risk_warning = "针对该症状的知识覆盖不足，需要人工复核。"

    human_escalation = {
        "required": escalation_required,
        "reason": _escalation_reason(info_insufficient, no_knowledge, direct_parameter_request, safety_or_quality_risk),
        "owner": "Process engineer / maintenance / quality lead",
        "next_step": "请先核实当前现场状态，确认风险边界，再决定是否需要按批准流程进行排查或隔离处理。",
    }

    return {
        "possible_causes": possible_causes[:5],
        "check_items": check_items[:6],
        "knowledge_sources": knowledge_sources,
        "risk_level": risk_level,
        "risk_warning": risk_warning,
        "human_escalation": human_escalation,
        "recommended_actions": recommended_actions,
        "confidence_note": _confidence_note(info_insufficient, no_knowledge, escalation_required),
    }


def _escalation_reason(info_insufficient: bool, no_knowledge: bool, direct_parameter_request: bool, safety_or_quality_risk: bool) -> str:
    if direct_parameter_request:
        return "公开 Demo 会主动拦截直接的定量调机建议。"
    if safety_or_quality_risk:
        return "当前可能涉及安全或质量影响，需要具备资质的人员审核。"
    if no_knowledge:
        return "当前 Synthetic Data 知识库覆盖不足，无法给出可靠结论。"
    if info_insufficient:
        return "经过追问后，问题描述仍然不完整。"
    return "当前无需人工升级。"


def _confidence_note(info_insufficient: bool, no_knowledge: bool, escalation_required: bool) -> str:
    if no_knowledge:
        return "低置信度：当前未在 Synthetic Data 知识库中检索到高匹配条目。"
    if info_insufficient:
        return "有限置信度：补充追问信息仍不完整，因此结果更适合作为复核辅助。"
    if escalation_required:
        return "中等置信度：虽然已匹配到相关知识，但风险边界仍要求人工确认。"
    return "中等置信度：已匹配到 Synthetic Data 知识，可支持形成初步原因清单与检查计划。"
