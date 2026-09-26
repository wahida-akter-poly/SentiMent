import re
from typing import Any, Callable

ASPECT_KEYWORDS = {
    "battery": ("battery", "battery life"),
    "camera": ("camera", "camera quality"),
    "delivery": ("delivery", "shipping", "late delivery"),
    "design": ("design", "appearance"),
    "durability": ("durability", "build quality"),
    "performance": ("performance", "speed"),
    "price": ("price", "cost", "value"),
    "quality": ("quality", "product quality"),
    "refund": ("refund", "return"),
    "service": ("service", "customer service", "support", "staff"),
    "usability": ("usability", "ease of use"),
    "website": ("website", "site"),
    "app": ("app", "application"),
    "packaging": ("packaging",),
    "availability": ("availability",),
}

STOPWORDS = {
    "the","a","an","and","or","but","if","then","than","that","this","with","from","into",
    "your","you","they","them","their","for","not","have","has","had","was","were","will","would",
    "very","more","most","about","over","under","just","also","yet","because","while","when",
}


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", normalize_text(text))
    return [s for s in sentences if s and len(s.strip()) > 1]


def detect_aspects(text: str, sentence_predictor: Callable[[str], Any] | None = None) -> list[dict[str, Any]]:
    normalized = normalize_text(text)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sentence in split_sentences(normalized):
        sentence_lower = sentence.lower()
        for aspect, keywords in ASPECT_KEYWORDS.items():
            if aspect in seen:
                continue
            if any(
                re.search(r"\b" + re.escape(keyword) + r"\b", sentence_lower)
                for keyword in keywords
            ):
                evidence = sentence.strip()
                sentiment = "neutral"
                confidence = 0.0
                if sentence_predictor is not None:
                    prediction = sentence_predictor(sentence)
                    sentiment = getattr(prediction, "sentiment", sentiment)
                    confidence = float(getattr(prediction, "confidence", 0.0))
                results.append({"aspect": aspect, "sentiment": sentiment, "confidence": confidence, "evidence": evidence})
                seen.add(aspect)
    return results


def extract_topics(text: str, aspects: list[dict[str, Any]] | None = None) -> list[str]:
    if aspects:
        return [aspect["aspect"] for aspect in aspects if isinstance(aspect, dict) and aspect.get("aspect")]
    tokens = []
    for token in re.findall(r"[a-zA-Z]+", normalize_text(text).lower()):
        if len(token) > 3 and token not in STOPWORDS:
            tokens.append(token)
    seen: set[str] = set()
    topics: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            topics.append(token)
    return topics[:5]


def derive_mixed_sentiment(sentences: list[dict[str, Any]]) -> str:
    meaningful = [item for item in sentences if item.get("sentiment") in {"positive", "negative"} and item.get("confidence", 0) >= 0.6]
    positive = any(item["sentiment"] == "positive" for item in meaningful)
    negative = any(item["sentiment"] == "negative" for item in meaningful)
    if len(meaningful) >= 2 and positive and negative:
        return "mixed"
    return "neutral"


def build_summary(final_sentiment: str, aspects: list[dict[str, Any]], topics: list[str]) -> str:
    base = f"Overall feedback is {final_sentiment}."
    if aspects:
        aspect_name = str(aspects[0].get("aspect", "product")).capitalize()
        return f"{base} {aspect_name} is a notable theme in the feedback."
    if topics:
        return f"{base} Key themes include {', '.join(topics[:3])}."
    return base


def build_evidence(sentences: list[dict[str, Any]]) -> dict[str, Any]:
    positive = max((obj for obj in sentences if obj.get("sentiment") == "positive"), default=None, key=lambda obj: obj.get("confidence", 0))
    negative = max((obj for obj in sentences if obj.get("sentiment") == "negative"), default=None, key=lambda obj: obj.get("confidence", 0))
    return {
        "strongest_positive": {"text": positive["text"], "confidence": positive["confidence"]} if positive else None,
        "strongest_negative": {"text": negative["text"], "confidence": negative["confidence"]} if negative else None,
    }


def build_analysis_payload(text: str, model_prediction: Any, sentence_predictor: Callable[[str], Any] | None = None) -> dict[str, Any]:
    normalized = normalize_text(text)
    sentences = split_sentences(normalized)
    sentence_results: list[dict[str, Any]] = []
    for sentence in sentences:
        prediction = sentence_predictor(sentence) if sentence_predictor else model_prediction
        sentence_results.append({
            "text": sentence,
            "sentiment": getattr(prediction, "sentiment", model_prediction.sentiment),
            "confidence": float(getattr(prediction, "confidence", model_prediction.confidence)),
        })
    if not sentence_results:
        sentence_results = [{"text": normalized, "sentiment": model_prediction.sentiment, "confidence": float(model_prediction.confidence)}]
    aspects = detect_aspects(normalized, sentence_predictor)
    topics = extract_topics(normalized, aspects)
    final_sentiment = model_prediction.sentiment
    if len(sentence_results) >= 2:
        mixed = derive_mixed_sentiment(sentence_results)
        if mixed == "mixed":
            final_sentiment = "mixed"
    evidence = build_evidence(sentence_results)
    summary = build_summary(final_sentiment, aspects, topics)
    return {
        "model_sentiment": model_prediction.sentiment,
        "sentiment": final_sentiment,
        "confidence": float(model_prediction.confidence),
        "probabilities": dict(model_prediction.probabilities),
        "sentence_results": sentence_results,
        "aspects": aspects,
        "topics": topics,
        "evidence": evidence,
        "summary_text": summary,
        "model_version": getattr(model_prediction, "model_version", "unknown"),
    }
