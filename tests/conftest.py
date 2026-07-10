import os
import tempfile

# Point the app at a fresh temp SQLite file before any app module is imported,
# since app.database builds its engine at import time from settings.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["LOG_DIR"] = tempfile.mkdtemp()

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.models  # noqa: F401 -- registers all models on Base.metadata
from app.api.router import api_router
from app.database import Base, SessionLocal, engine
from app.models.config import GlobalConfig
from app.models.user import User
from app.security import hash_password


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    db.add(GlobalConfig(id=1))
    db.commit()
    db.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


@pytest.fixture
def authed_client(client: TestClient, db) -> TestClient:
    db.add(User(username="admin", password_hash=hash_password("testpass123")))
    db.commit()
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert resp.status_code == 200
    return client
