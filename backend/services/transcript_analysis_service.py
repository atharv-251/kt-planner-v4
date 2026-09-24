import re


_WORD_RE = re.compile(r"[A-Za-z0-9']+")
_TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->")
_NEGATION_HINTS = (
    "not discussed", "not covered", "did not", "didn't", "no time for",
    "did not get to", "skipped", "postponed", "deferred",
)
_ACTION_HINTS = ("action item", "follow up", "follow-up", "will do", "next step", "will share", "will send")


def analyze_transcript(raw_text: str, expected_topics: list[str]) -> dict[str, object]:
    sentences = _sentences(raw_text)
    covered: list[str] = []
    partially_covered: list[str] = []
    missed: list[str] = []
    lowered = [sentence.lower() for sentence in sentences]

    for topic in expected_topics:
        keywords = [word.lower() for word in _WORD_RE.findall(topic) if len(word) > 2]
        matches = [sentence for sentence in lowered if keywords and all(word in sentence for word in keywords)]
        positive = [sentence for sentence in matches if not any(hint in sentence for hint in _NEGATION_HINTS)]
        if not positive:
            missed.append(topic)
        elif any(any(hint in sentence for hint in _NEGATION_HINTS) for sentence in matches) or sum(len(sentence.split()) for sentence in positive) < 15:
            partially_covered.append(topic)
        else:
            covered.append(topic)

    action_items = [sentence for sentence in sentences if any(hint in sentence.lower() for hint in _ACTION_HINTS)][:10]
    questions = [sentence for sentence in sentences if sentence.endswith("?")]
    confidence = 0.0 if not sentences else round(min(0.97, 0.5 + (0.4 * (len(covered) + len(missed)) / max(len(expected_topics), 1))), 2)
    summary_parts = [" ".join(sentences[:2])]
    if covered:
        summary_parts.append(f"Covered: {', '.join(covered)}.")
    if partially_covered:
        summary_parts.append(f"Partially covered: {', '.join(partially_covered)}.")
    if missed:
        summary_parts.append(f"Not discussed: {', '.join(missed)}.")
    return {
        "topics_covered": covered,
        "topics_partially_covered": partially_covered,
        "topics_missed": missed,
        "questions_raised": len(questions),
        "action_items": action_items,
        "summary": " ".join(part for part in summary_parts if part).strip()[:2000],
        "confidence": confidence,
    }


def _sentences(raw_text: str) -> list[str]:
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT" or stripped.isdigit() or _TIMESTAMP_RE.match(stripped):
            continue
        lines.append(stripped)
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", " ".join(lines)) if sentence.strip()]