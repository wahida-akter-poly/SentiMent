from tests.conftest import FakeAdapter
from datetime import datetime

from app.models import Analysis
from app.services.model_adapter import SklearnModelAdapter
from app.services.text_insights import detect_aspects


def add_analysis(client, *, text, sentiment="neutral", source="manual", confidence=0.8,
                 created_at=None, aspects=None, topics=None, model_sentiment=None):
    factory = client.app.state.testing_session_factory
    with factory() as session:
        row = Analysis(
            text=text, source=source, sentiment=sentiment, model_sentiment=model_sentiment or sentiment,
            confidence=confidence,
            probabilities={"positive": 0.1, "neutral": 0.8, "negative": 0.1},
            sentence_results=[], aspects=aspects or [], topics=topics or [], evidence={},
            summary_text=f"Summary for {text}", model_version="test-model",
        )
        if created_at:
            row.created_at = created_at
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def test_analysis_includes_topics_evidence_and_deterministic_summary(client):
    client.app.state.model_adapter = FakeAdapter()
    body = client.post("/api/analyze", json={"text": "The camera is excellent. The battery is terrible."}).json()
    assert {"camera", "battery"}.issubset(set(body["topics"]))
    assert body["evidence"]["strongest_positive"]["text"] == "The camera is excellent."
    assert body["evidence"]["strongest_negative"]["text"] == "The battery is terrible."
    assert body["summary_text"].startswith("Overall feedback is mixed.")


def test_mixed_result_keeps_two_sentence_labels_and_three_class_model_output(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post(
        "/api/analyze",
        json={"text": "The camera is excellent. The battery is terrible."},
    )
    body = response.json()
    assert [item["sentiment"] for item in body["sentence_results"]] == ["positive", "negative"]
    assert body["sentiment"] == "mixed"
    assert body["model_sentiment"] in {"positive", "neutral", "negative"}
    assert set(body["probabilities"]) == {"positive", "neutral", "negative"}
    assert "mixed" not in body["probabilities"]


def test_sklearn_adapter_predicts_sentences_and_aspects_independently():
    class TestPipeline:
        classes_ = ["negative", "neutral", "positive"]

        def predict_proba(self, texts):
            value = texts[0].lower()
            if "excellent" in value:
                return [[0.02, 0.08, 0.9]]
            if "terrible" in value:
                return [[0.9, 0.08, 0.02]]
            return [[0.08, 0.84, 0.08]]

        def predict(self, texts):
            probabilities = self.predict_proba(texts)[0]
            index = max(range(len(probabilities)), key=probabilities.__getitem__)
            return [self.classes_[index]]

    adapter = SklearnModelAdapter({
        "pipeline": TestPipeline(),
        "metadata": {
            "model_version": "verified-test-artifact",
            "labels": TestPipeline.classes_,
            "metrics": {"accuracy": 0.91, "macro_f1": 0.89, "train_rows": 90, "test_rows": 10},
        },
    })
    result = adapter.predict("The camera is excellent. The battery is terrible.")
    assert [item["sentiment"] for item in result.sentence_results] == ["positive", "negative"]
    assert result.sentiment == "mixed"
    assert result.model_sentiment in {"positive", "neutral", "negative"}
    assert "mixed" not in result.probabilities
    assert {item["aspect"]: item["sentiment"] for item in result.aspects} == {
        "camera": "positive", "battery": "negative",
    }
    assert adapter.metrics["accuracy"] == 0.91


def test_non_mixed_prediction_and_aspect_detection_exclude_unrelated_topics(client):
    client.app.state.model_adapter = FakeAdapter()
    body = client.post("/api/analyze", json={"text": "The camera is excellent. Great image."}).json()
    assert body["sentiment"] == body["model_sentiment"] == "positive"
    assert [item["aspect"] for item in body["aspects"]] == ["camera"]
    assert detect_aspects("I am happy with the result.") == []


def test_health_reports_model_state(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_does_not_fabricate_when_model_unavailable(client):
    response = client.post("/api/analyze", json={"text": "A real review"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MODEL_UNAVAILABLE"
    assert client.get("/api/analyses").json()["total"] == 0


def test_successful_prediction_is_persisted(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post("/api/analyze", json={"text": "A good review", "source": "manual"})
    assert response.status_code == 201
    body = response.json()
    assert body["sentiment"] == "positive"
    assert body["confidence"] == 0.9
    assert client.get("/api/analyses").json()["total"] == 1


def test_one_multi_sentence_analysis_request_persists_one_parent_row(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post(
        "/api/analyze",
        json={"text": "The camera is excellent. The battery is terrible."},
    )
    assert response.status_code == 201
    assert len(response.json()["sentence_results"]) == 2
    saved = client.get("/api/analyses").json()
    assert saved["total"] == 1
    assert saved["items"][0]["id"] == response.json()["id"]


def test_summary_is_explicitly_empty_without_records(client):
    summary = client.get("/api/dashboard/summary").json()
    assert summary["has_data"] is False
    assert summary["total"] == 0
    assert summary["average_confidence"] is None
    assert summary["percentages"]["positive"] is None
    assert summary["by_source"] == []
    assert summary["trend"] == []
    assert summary["top_aspects"] == []
    assert summary["top_topics"] == []
    assert summary["top_complaints"] == []


def test_unavailable_model_status_uses_unavailable_values(client):
    body = client.get("/api/model/status").json()
    assert body["available"] is False
    assert body["model_version"] is None
    assert body["labels"] == []
    assert body["accuracy"] is None
    assert body["macro_f1"] is None
    assert body["train_rows"] is None
    assert body["test_rows"] is None


def test_text_length_is_capped_at_5000_characters(client):
    long_text = "A" * 5001
    response = client.post("/api/analyze", json={"text": long_text})
    assert response.status_code == 422
    assert "5000" in response.json()["detail"][0]["msg"]


def test_batch_analysis_persists_multiple_records(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post(
        "/api/analyze/batch",
        json={"items": [{"text": "First review"}, {"text": "Second review", "source": "storefront"}]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["total"] == 2
    assert client.get("/api/analyses").json()["total"] == 2


def test_batch_analysis_keeps_successes_when_one_prediction_fails(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post("/api/batch/analyze", json={"items": [
        {"text": "Good review"}, {"text": "Fail prediction here"}, {"text": "Bad review"},
    ]})
    assert response.status_code == 201
    body = response.json()
    assert (body["processed"], body["skipped"], body["total"]) == (2, 1, 2)
    assert body["errors"][0]["index"] == 2
    assert client.get("/api/analyses").json()["total"] == 2


def test_invalid_csv_upload_is_rejected(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post("/api/analyses/upload", files={"file": ("bad.csv", "Name,Source\nA,web", "text/csv")})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_CSV"


def test_csv_upload_persists_rows_and_source_tags(client):
    client.app.state.model_adapter = FakeAdapter()
    response = client.post("/api/analyses/upload", files={
        "file": ("reviews.csv", "Review,Source\nGreat camera,store\nTerrible battery,web", "text/csv")
    })
    assert response.status_code == 200
    assert response.json()["processed"] == 2
    assert {item["source"] for item in client.get("/api/analyses").json()["items"]} == {"store", "web"}


def test_summary_filters_support_source_and_sentiment(client):
    client.app.state.model_adapter = FakeAdapter()
    client.post("/api/analyze", json={"text": "Good product", "source": "website"})
    client.post("/api/analyze", json={"text": "Bad product", "source": "support"})

    summary = client.get("/api/dashboard/summary?source=website&sentiment=positive").json()
    assert summary["total"] == 1
    assert summary["counts"]["positive"] == 1
    assert summary["by_source"][0]["source"] == "website"


def test_analysis_history_filters_by_sentiment_source_and_text(client):
    add_analysis(client, text="camera works well", sentiment="positive", source="storefront")
    add_analysis(client, text="battery failed", sentiment="negative", source="support")
    assert client.get("/api/analyses?sentiment=positive").json()["total"] == 1
    assert client.get("/api/analyses?source=support").json()["items"][0]["text"] == "battery failed"
    assert client.get("/api/analyses?q=CAMERA").json()["total"] == 1


def test_analysis_history_filters_inclusive_start_and_end_dates(client):
    add_analysis(client, text="inside range", created_at=datetime(2025, 5, 15, 12))
    add_analysis(client, text="before range", created_at=datetime(2025, 5, 14, 23, 59))
    assert client.get("/api/analyses?start=2025-05-15&end=2025-05-15").json()["total"] == 1


def test_csv_export_has_content_type_headers_rows_and_filters(client):
    add_analysis(client, text="camera export row", sentiment="positive", source="web",
                 created_at=datetime(2025, 5, 15, 12))
    add_analysis(client, text="other export row", sentiment="negative", source="store",
                 created_at=datetime(2025, 5, 15, 12))
    response = client.get(
        "/api/analyses/export.csv?sentiment=positive&source=web&q=camera&start=2025-05-15&end=2025-05-15"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]
    assert "id,text,source,sentiment,confidence,model_version,created_at" in response.text
    assert "camera export row" in response.text
    assert "other export row" not in response.text


def test_populated_analytics_calculates_counts_sources_trend_and_rankings(client):
    add_analysis(client, text="late delivery one", sentiment="negative", source="web", confidence=0.6,
                 created_at=datetime(2025, 5, 15), aspects=[{"aspect": "delivery", "sentiment": "negative"}],
                 topics=["delivery", "shipping"])
    add_analysis(client, text="late delivery two", sentiment="negative", source="web", confidence=0.8,
                 created_at=datetime(2025, 5, 15, 10), aspects=[{"aspect": "delivery", "sentiment": "negative"}],
                 topics=["delivery"])
    add_analysis(client, text="camera good", sentiment="positive", source="store", confidence=1.0,
                 created_at=datetime(2025, 5, 16), aspects=[{"aspect": "camera", "sentiment": "positive"}],
                 topics=["camera"])
    result = client.get("/api/analytics/summary").json()
    assert result["total"] == 3
    assert result["counts"] == {"positive": 1, "neutral": 0, "negative": 2, "mixed": 0}
    assert result["percentages"]["negative"] == 66.67
    assert result["average_confidence"] == 0.8
    assert result["by_source"] == [{"source": "web", "count": 2}, {"source": "store", "count": 1}]
    assert result["trend"][0]["negative"] == 2
    assert result["top_aspects"][0] == {"name": "delivery", "count": 2}
    assert result["top_topics"][0] == {"name": "delivery", "count": 2}
    assert result["top_complaints"] == [{"name": "delivery", "count": 2}]
    period = client.get(
        "/api/analytics/summary?start=2025-05-15&end=2025-05-15"
    ).json()
    assert period["total"] == 2
    assert len(period["trend"]) == 1


def test_three_persisted_negative_delivery_aspects_count_as_three_complaints(client):
    for index in range(3):
        add_analysis(client, text=f"delivery complaint {index}", sentiment="negative",
                     aspects=[{"aspect": "delivery", "sentiment": "negative"}])
    response = client.get("/api/analytics/summary")
    assert response.json()["top_complaints"] == [{"name": "delivery", "count": 3}]


def test_analytics_search_filter_uses_database_rows(client):
    add_analysis(client, text="camera is excellent", sentiment="positive")
    add_analysis(client, text="battery is poor", sentiment="negative")
    result = client.get("/api/analytics/summary?q=camera").json()
    assert result["total"] == 1
    assert result["counts"]["positive"] == 1


def test_model_status_returns_actual_metadata_values(client):
    class Pipeline:
        classes_ = ["negative", "neutral", "positive"]

    client.app.state.model_adapter = SklearnModelAdapter({
        "pipeline": Pipeline(),
        "metadata": {
            "model_version": "verified-model-v1",
            "labels": Pipeline.classes_,
            "metrics": {
                "accuracy": 0.8,
                "macro_f1": 0.75,
                "train_rows": 80,
                "test_rows": 20,
            },
        },
    })
    body = client.get("/api/model/status").json()
    assert body["model_version"] == "verified-model-v1"
    assert set(body["labels"]) == {"positive", "neutral", "negative"}
    assert body["accuracy"] == 0.8
    assert body["macro_f1"] == 0.75
    assert body["train_rows"] == 80
    assert body["test_rows"] == 20


def test_openapi_lists_required_api_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/analyze", "/api/batch/analyze", "/api/analyses", "/api/analyses/export.csv",
            "/api/model/status", "/api/dashboard/summary", "/api/analytics/summary"}.issubset(paths)


def test_frontend_pages_are_served(client):
    paths = (
        "/", "/pages/home/index.html", "/pages/dashboard/index.html",
        "/pages/text-analysis/index.html", "/pages/batch-analysis/index.html",
        "/pages/analytics/index.html", "/pages/about-project/index.html",
        "/pages/batch-analysis/batch-analysis.css",
        "/pages/batch-analysis/batch-analysis.js",
        "/pages/text-analysis/text-analysis.css",
        "/pages/text-analysis/text-analysis.js",
        "/pages/analytics/analytics.css", "/pages/analytics/analytics.js",
        "/pages/about-project/about-project.css",
        "/pages/about-project/about-project.js",
        "/assets/scripts/shared/app-interactions.js",
    )
    for path in paths:
        assert client.get(path).status_code == 200
