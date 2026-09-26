from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from zipfile import BadZipFile

from app.services.text_insights import build_analysis_payload


LABELS = ("positive", "neutral", "negative")


@dataclass(frozen=True)
class Prediction:
    sentiment: str
    confidence: float
    probabilities: dict[str, float]
    model_version: str
    model_sentiment: str | None = None
    sentence_results: list[dict[str, object]] | None = None
    aspects: list[dict[str, object]] | None = None
    topics: list[str] | None = None
    evidence: dict[str, object] | list[dict[str, object]] | None = None
    summary_text: str | None = None

    def __post_init__(self):
        if self.model_sentiment is None:
            object.__setattr__(self, "model_sentiment", self.sentiment)


class ModelAdapter(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def reason(self) -> str | None: ...

    @property
    def model_version(self) -> str | None: ...

    @property
    def labels(self) -> list[str]: ...

    def predict(self, text: str) -> Prediction: ...


class ModelUnavailableError(RuntimeError):
    """Raised when prediction was requested without a usable trained model."""


class UnavailableModelAdapter:
    available = False
    model_version = None
    labels: list[str] = []

    def __init__(self, reason: str):
        self._reason = reason

    @property
    def reason(self) -> str:
        return self._reason

    def predict(self, text: str) -> Prediction:
        raise ModelUnavailableError(self._reason)


class SklearnModelAdapter:
    def __init__(self, artifact: Any):
        self.pipeline = artifact["pipeline"] if isinstance(artifact, dict) else artifact
        metadata = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
        model_version = metadata.get("model_version")
        self._model_version = str(model_version) if model_version else None
        self.metrics = metadata.get("metrics", {})
        classes = metadata.get("labels")
        self._labels = [str(item) for item in classes] if classes else [
            str(item) for item in getattr(self.pipeline, "classes_", LABELS)
        ]
        if not self._labels:
            raise ValueError("The model artifact has no class labels.")

    @property
    def available(self) -> bool:
        return True

    @property
    def reason(self) -> None:
        return None

    @property
    def model_version(self) -> str | None:
        return self._model_version

    @property
    def labels(self) -> list[str]:
        return self._labels

    def _predict_one(self, text: str) -> Prediction:
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = [str(item) for item in getattr(self.pipeline, "classes_", self._labels)]
        scores = {label: 0.0 for label in LABELS}
        for label, value in zip(classes, probabilities):
            if label in scores:
                scores[label] = float(value)
        sentiment = str(self.pipeline.predict([text])[0])
        confidence = scores.get(sentiment, float(max(probabilities)))
        return Prediction(
            sentiment,
            confidence,
            scores,
            self.model_version or "unversioned",
            model_sentiment=sentiment,
        )

    def predict(self, text: str) -> Prediction:
        prediction = self._predict_one(text)
        payload = build_analysis_payload(text, prediction, sentence_predictor=self._predict_one)
        return Prediction(
            payload["sentiment"],
            payload["confidence"],
            payload["probabilities"],
            payload["model_version"],
            model_sentiment=payload["model_sentiment"],
            sentence_results=payload["sentence_results"],
            aspects=payload["aspects"],
            topics=payload["topics"],
            evidence=payload["evidence"],
            summary_text=payload["summary_text"],
        )

    def _detect_aspects(self, text: str) -> list[dict[str, object]]:
        normalized = text.lower()
        aspects = [
            ("battery", ("battery", "battery life")),
            ("camera", ("camera", "camera quality")),
            ("delivery", ("delivery", "shipping", "late delivery")),
            ("design", ("design", "appearance")),
            ("durability", ("durability", "build quality")),
            ("performance", ("performance", "speed")),
            ("price", ("price", "cost", "value")),
            ("quality", ("quality", "product quality")),
            ("refund", ("refund", "return")),
            ("service", ("service", "customer service", "support", "staff")),
            ("usability", ("usability", "ease of use")),
            ("website", ("website", "site")),
            ("app", ("app", "application")),
            ("packaging", ("packaging",)),
            ("availability", ("availability",)),
        ]
        matches = []
        for aspect, keywords in aspects:
            if any(keyword in normalized for keyword in keywords):
                matches.append({"aspect": aspect, "sentiment": "neutral", "confidence": 0.0, "evidence": text.strip()})
        return matches

    def _extract_topics(self, text: str, aspects: list[dict[str, object]]) -> list[str]:
        if aspects:
            return [item["aspect"] for item in aspects if isinstance(item, dict) and item.get("aspect")]
        tokens = [token for token in text.lower().replace("\n", " ").split() if len(token) > 3 and token not in {"with", "this", "that", "from", "into", "your", "very"}]
        unique_tokens = []
        seen = set()
        for token in tokens:
            if token not in seen:
                unique_tokens.append(token)
                seen.add(token)
        return unique_tokens[:5]

    def _build_evidence(self, text: str, sentiment: str, confidence: float) -> dict[str, object]:
        return {"strongest_positive": {"text": text.strip(), "confidence": float(confidence)} if sentiment == "positive" else None,
                "strongest_negative": {"text": text.strip(), "confidence": float(confidence)} if sentiment == "negative" else None}

    def _make_summary(self, sentiment: str, aspects: list[dict[str, object]], topics: list[str]) -> str:
        base = "Overall feedback is " + sentiment + "."
        if aspects:
            top = aspects[0].get("aspect", "product")
            return base + f" {top.capitalize()} is a notable theme in the feedback."
        if topics:
            return base + f" Key themes include {', '.join(topics[:3])}."
        return base

    def _derive_final_sentiment(self, text: str, sentence_results: list[dict[str, object]]) -> str:
        if not sentence_results:
            return "neutral"
        return sentence_results[0]["sentiment"]


def load_model_adapter(path: Path) -> ModelAdapter:
    if not path.exists():
        return UnavailableModelAdapter(
            f"No trained model artifact found at {path}. Train a model before analyzing text."
        )
    try:
        import joblib

        return SklearnModelAdapter(joblib.load(path))
    except (OSError, EOFError, ValueError, KeyError, ImportError, BadZipFile) as exc:
        return UnavailableModelAdapter(f"Model artifact could not be loaded: {exc}")
