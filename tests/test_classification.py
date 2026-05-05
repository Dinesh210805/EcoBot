"""
Integration tests for EcoBot classification pipeline.
Run: pytest tests/ -v

Requires:
  - .env file with valid API keys
  - CLASSIFIER_MODE=groq (no Ollama needed for CI)
"""
import os
import pytest

os.environ.setdefault("CLASSIFIER_MODE", "groq")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_schema(self, client):
        data = client.get("/api/v1/health").json()
        assert "status" in data
        assert "version" in data
        assert "dependencies" in data
        assert "classifier_mode" in data


class TestTextClassification:
    VALID_CATEGORIES = {
        "wet_waste", "dry_waste", "hazardous", "e_waste",
        "sanitary", "construction", "non_recyclable"
    }
    VALID_COLORS = {"green", "blue", "red", "grey", "black"}
    VALID_CONFIDENCE = {"high", "medium", "low"}

    @pytest.mark.parametrize("item,expected_category", [
        ("old newspaper", "dry_waste"),
        ("banana peel", "wet_waste"),
        ("dead AA battery", "hazardous"),
        ("broken Android phone", "e_waste"),
        ("sanitary napkin", "sanitary"),
        ("thermocol packaging", "non_recyclable"),
    ])
    def test_classify_common_items(self, client, item, expected_category):
        resp = client.post("/api/v1/classify/text", json={"text": item})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == expected_category, f"Expected {expected_category} for '{item}', got {data['category']}"

    def test_classify_text_response_schema(self, client):
        resp = client.post("/api/v1/classify/text", json={"text": "plastic bottle"})
        assert resp.status_code == 200
        data = resp.json()

        assert "session_id" in data
        assert "item" in data
        assert data["category"] in self.VALID_CATEGORIES
        assert data["bin_color"] in self.VALID_COLORS
        assert data["confidence"] in self.VALID_CONFIDENCE
        assert isinstance(data["recyclable"], bool)
        assert isinstance(data["preparation_steps"], list)
        assert isinstance(data["special_facility_required"], bool)
        assert data["input_type"] == "text"

    def test_classify_with_location(self, client):
        resp = client.post("/api/v1/classify/text", json={
            "text": "old battery",
            "location": "Mumbai",
            "include_facilities": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "hazardous"

    def test_session_id_returned(self, client):
        resp = client.post("/api/v1/classify/text", json={"text": "cardboard box"})
        data = resp.json()
        assert len(data["session_id"]) == 36  # UUID format

    def test_session_id_persisted(self, client):
        resp = client.post("/api/v1/classify/text", json={
            "text": "glass bottle",
            "session_id": "test-session-123",
        })
        assert resp.json()["session_id"] == "test-session-123"

    def test_empty_text_rejected(self, client):
        resp = client.post("/api/v1/classify/text", json={"text": ""})
        assert resp.status_code == 422

    def test_text_too_long_rejected(self, client):
        resp = client.post("/api/v1/classify/text", json={"text": "a" * 1001})
        assert resp.status_code == 422


class TestBatchClassification:
    def test_batch_classify(self, client):
        resp = client.post("/api/v1/classify/batch", json={
            "items": ["newspaper", "battery", "banana peel", "old phone"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4
        assert data["hazardous_count"] >= 1  # battery + phone should be hazardous

    def test_batch_too_many_items(self, client):
        resp = client.post("/api/v1/classify/batch", json={
            "items": [f"item_{i}" for i in range(21)]
        })
        assert resp.status_code == 422

    def test_batch_empty_list(self, client):
        resp = client.post("/api/v1/classify/batch", json={"items": []})
        assert resp.status_code == 422


class TestFacilities:
    def test_get_categories(self, client):
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        categories = resp.json()
        assert len(categories) == 7
        keys = [c["key"] for c in categories]
        assert "wet_waste" in keys
        assert "e_waste" in keys

    def test_search_facilities_by_city(self, client):
        resp = client.post("/api/v1/facilities", json={"city": "Mumbai"})
        assert resp.status_code == 200
        data = resp.json()
        assert "facilities" in data
        assert "total" in data

    def test_search_facilities_limit(self, client):
        resp = client.post("/api/v1/facilities", json={"city": "Bengaluru", "limit": 2})
        data = resp.json()
        assert len(data["facilities"]) <= 2


class TestChat:
    def test_chat_requires_session_id(self, client):
        # First get a session ID
        clf_resp = client.post("/api/v1/classify/text", json={"text": "newspaper"})
        session_id = clf_resp.json()["session_id"]

        resp = client.post("/api/v1/chat", json={
            "message": "How should I prepare it?",
            "session_id": session_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert len(data["reply"]) > 0

    def test_chat_empty_message_rejected(self, client):
        resp = client.post("/api/v1/chat", json={
            "message": "",
            "session_id": "some-session",
        })
        assert resp.status_code == 422
