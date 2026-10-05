import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
# ... (остальной код тестов без изменений)
def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "up"

def test_create_patient():
    response = client.post("/api/v1/patients")
    assert response.status_code == 200
    assert response.json()["id"] > 0

def test_analyze_with_patient_id():
    response = client.post("/api/v1/patients")
    patient_id = response.json()["id"]
    
    response = client.post("/api/v1/analyze", json={
        "patient_id": patient_id,
        "protocol_text": "УЗИ малого таза. Полип эндометрия."
    })
    assert response.status_code == 200
    assert response.json()["patient_id"] == patient_id
    assert response.json()["engine"] == "rules-nlp-0.1"
    assert response.json()["decision"] == "consultation"
    assert len(response.json()["findings"]) > 0
    assert len(response.json()["routes"]) > 0

def test_analyze_empty_text_returns_422():
    response = client.post("/api/v1/analyze", json={
        "patient_id": 1,
        "protocol_text": ""
    })
    assert response.status_code == 422

def test_analyze_missing_patient_id_returns_422():
    response = client.post("/api/v1/analyze", json={
        "protocol_text": "УЗИ малого таза. Полип эндометрия."
    })
    assert response.status_code == 422