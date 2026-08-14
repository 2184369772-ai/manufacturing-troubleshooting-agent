from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db import list_knowledge_items


FOLLOW_UPS = [
    {
        "key": "symptom_scope",
        "question": "Is the issue isolated, repeated, or affecting multiple stations / parts?",
    },
    {
        "key": "recent_change",
        "question": "What changed recently: material, equipment condition, environment, schedule, or nothing obvious?",
    },
    {
        "key": "safety_quality_impact",
        "question": "Is there any safety, customer-quality, or containment impact right now?",
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
    results: list[RetrievalResult] = []
    for item in list_knowledge_items():
        bag = set(item["tags_json"]) | set(item["symptom_keywords_json"]) | normalize_words(item["title"]) | normalize_words(item["domain"])
        score = len(words & {w.lower() for w in bag})
        if score:
            results.append(RetrievalResult(item=item, score=score))
    results.sort(key=lambda entry: (-entry.score, entry.item["source_id"]))
    return results[:top_n]


def required_follow_up_count(question_text: str) -> int:
    text = question_text.lower()
    if len(text.split()) < 5:
        return len(FOLLOW_UPS)
    if any(term in text for term in ["exact setting", "machine setting", "parameter", "setpoint", "speed", "pressure", "temperature adjustment"]):
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
    direct_parameter_request = any(term in lower_bundle for term in ["exact setting", "machine setting", "parameter", "setpoint", "temperature to", "pressure to", "speed to"])
    safety_or_quality_risk = any(term in lower_bundle for term in ["safety", "injury", "smoke", "electrical", "customer", "containment", "fire"])
    repeated_or_unknown = any(term in lower_bundle for term in ["repeated", "again", "unknown", "not sure", "unclear"])

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
            "Information is still too limited to identify a credible root-cause shortlist.",
            "Current description may span multiple failure modes that need qualified review.",
        ]
    if not check_items:
        check_items = [
            "Clarify affected equipment / process step",
            "Confirm recurrence pattern and impact scope",
            "Escalate to a qualified owner because knowledge coverage is limited",
        ]

    recommendation_prefix = "Use these suggestions as a structured review aid, not as an automatic execution instruction."
    recommended_actions = [
        recommendation_prefix,
        "Verify the problem at the asset or process level before applying any change.",
        "Use approved troubleshooting and trial workflows if the issue could affect safety, quality, or equipment health.",
    ]
    if escalation_required:
        recommended_actions.append("Pause autonomous advice here and route the case to human review / escalation.")

    risk_warning = "No immediate high-risk pattern detected from the synthetic demo input."
    if source_warnings:
        risk_warning = source_warnings[0]
    if direct_parameter_request:
        risk_warning = "This request asks for direct quantitative adjustment guidance. The demo intentionally escalates instead of giving unreviewed machine settings."
    elif info_insufficient:
        risk_warning = "Information is still incomplete. Any high-risk action should go through human review."
    elif no_knowledge:
        risk_warning = "Knowledge coverage is limited for this symptom. Human review is required."

    human_escalation = {
        "required": escalation_required,
        "reason": _escalation_reason(info_insufficient, no_knowledge, direct_parameter_request, safety_or_quality_risk),
        "owner": "Process engineer / maintenance / quality lead",
        "next_step": "Review the current floor condition, confirm the risk boundary, and decide whether approved troubleshooting or containment is required.",
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
        return "Direct quantitative machine guidance is intentionally blocked in this public demo."
    if safety_or_quality_risk:
        return "Potential safety or quality impact requires qualified human review."
    if no_knowledge:
        return "Synthetic knowledge base coverage is insufficient for a reliable answer."
    if info_insufficient:
        return "The issue description is still incomplete after follow-up."
    return "Escalation not required."


def _confidence_note(info_insufficient: bool, no_knowledge: bool, escalation_required: bool) -> str:
    if no_knowledge:
        return "Low confidence: no strong knowledge match found in the synthetic knowledge base."
    if info_insufficient:
        return "Limited confidence: follow-up answers are incomplete, so the result should be treated as a review aid."
    if escalation_required:
        return "Moderate confidence: matched knowledge exists, but the risk boundary still requires human sign-off."
    return "Moderate confidence: matched synthetic knowledge supports the shortlist and check plan."
