import pytest
from datetime import datetime
from models.personality import StudentTestCreate, StudentTest, StudentTestResponse

class TestStudentTestCreate:
    """Test StudentTestCreate model."""
    
    def test_valid_student_test_create(self):
        """Test creating a valid StudentTestCreate instance."""
        data = {
            "user_id": "507f1f77bcf86cd799439011",
            "answers": [1, 2, 1, 2, 1],
            "personality_type": "INTJ",
            "recommended_universities": ["507f1f77bcf86cd799439012"],
            "gpt_summary": "Test personality summary"
        }
        
        test_create = StudentTestCreate(**data)
        assert test_create.user_id == data["user_id"]
        assert test_create.answers == data["answers"]
        assert test_create.personality_type == data["personality_type"]
        assert test_create.recommended_universities == data["recommended_universities"]
        assert test_create.gpt_summary == data["gpt_summary"]

class TestStudentTest:
    """Test StudentTest model."""
    
    def test_valid_student_test(self):
        """Test creating a valid StudentTest instance."""
        data = {
            "user_id": "507f1f77bcf86cd799439011",
            "answers": [1, 2, 1, 2, 1],
            "personality_type": "INTJ",
            "recommended_universities": ["507f1f77bcf86cd799439012"],
            "gpt_summary": "Test personality summary"
        }
        
        test = StudentTest(**data)
        assert test.user_id == data["user_id"]
        assert test.answers == data["answers"]
        assert test.personality_type == data["personality_type"]
        assert test.recommended_universities == data["recommended_universities"]
        assert test.gpt_summary == data["gpt_summary"]
        assert isinstance(test.created_at, datetime)
    
    def test_to_dict(self):
        """Test converting StudentTest to dictionary."""
        data = {
            "user_id": "507f1f77bcf86cd799439011",
            "answers": [1, 2, 1, 2, 1],
            "personality_type": "INTJ",
            "recommended_universities": ["507f1f77bcf86cd799439012"],
            "gpt_summary": "Test personality summary"
        }
        
        test = StudentTest(**data)
        test_dict = test.model_dump(by_alias=True)
        
        assert test_dict["user_id"] == data["user_id"]
        assert test_dict["answers"] == data["answers"]
        assert test_dict["personality_type"] == data["personality_type"]
        assert test_dict["recommended_universities"] == data["recommended_universities"]
        assert test_dict["gpt_summary"] == data["gpt_summary"]
        assert "created_at" in test_dict