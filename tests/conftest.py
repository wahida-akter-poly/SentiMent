import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.testing_session_factory = TestingSession

    def override_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.testing_session_factory


class FakeAdapter:
    available = True
    reason = None
    model_version = "test-model"
    labels = ["negative", "neutral", "positive"]
    metrics = {"accuracy": 0.8, "macro_f1": 0.75, "train_rows": 80, "test_rows": 20}

    def predict(self, text):
        from app.services.model_adapter import Prediction
        from app.services.text_insights import build_analysis_payload

        prediction = self._predict_sentence(text)
        payload = build_analysis_payload(text, prediction, sentence_predictor=self._predict_sentence)
        return Prediction(
            payload["sentiment"], payload["confidence"], payload["probabilities"], "test-model",
            model_sentiment=payload["model_sentiment"], sentence_results=payload["sentence_results"],
            aspects=payload["aspects"], topics=payload["topics"], evidence=payload["evidence"],
            summary_text=payload["summary_text"],
        )

    def _predict_sentence(self, text):
        from app.services.model_adapter import Prediction

        lowered = text.lower()
        if "fail prediction" in lowered:
            raise ValueError("test prediction failure")
        if "terrible" in lowered or "bad" in lowered or "late" in lowered or "poor" in lowered:
            label = "negative"
            scores = {"positive": 0.02, "neutral": 0.08, "negative": 0.9}
        elif "excellent" in lowered or "good" in lowered or "great" in lowered or "well" in lowered:
            label = "positive"
            scores = {"positive": 0.9, "neutral": 0.08, "negative": 0.02}
        else:
            label = "neutral"
            scores = {"positive": 0.08, "neutral": 0.84, "negative": 0.08}
        return Prediction(label, scores[label], scores, "test-model")
