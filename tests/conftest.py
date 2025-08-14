import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from unittest.mock import AsyncMock, patch

from main import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB database for testing."""
    with patch('db.mongo.db') as mock_db:
        # Mock collections
        mock_db.student_personality_tests = AsyncMock()
        mock_db.universities = AsyncMock()
        mock_db.users = AsyncMock()
        yield mock_db

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def sample_university_data():
    """Sample university data for testing."""
    return {
        "name": "Test University",
        "location": "Test City",
        "ranking": 100,
        "programs": ["Computer Science", "Engineering"],
        "personality_types": ["INTJ", "ENTP"]
    }

@pytest.fixture
def sample_test_data():
    """Sample personality test data for testing."""
    return {
        "user_id": "507f1f77bcf86cd799439011",
        "answers": ["A", "B", "A", "B", "A"],
        "personality_type": "INTJ",
        "recommended_universities": ["507f1f77bcf86cd799439012"],
        "gpt_summary": "Test personality summary"
    }