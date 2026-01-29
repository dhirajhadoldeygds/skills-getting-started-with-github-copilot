"""
Tests for the Mergington High School API using pytest and FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities before each test"""
    # Save original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestGetActivities:
    """Test the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Soccer Club" in data
        assert "Art Club" in data
    
    def test_activity_has_required_fields(self, client):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Basketball Team"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)
    
    def test_activities_have_participants_list(self, client):
        """Test that activities with participants are returned correctly"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        
        assert len(chess_club["participants"]) > 0
        assert "michael@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Test the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "student@mergington.edu" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup adds the participant to the activity"""
        email = "test_student@mergington.edu"
        client.post("/activities/Soccer Club/signup", params={"email": email})
        
        response = client.get("/activities")
        soccer_club = response.json()["Soccer Club"]
        assert email in soccer_club["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_email(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "michael@mergington.edu"
        
        # Michael is already signed up for Chess Club
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_different_email_same_activity(self, client):
        """Test that different students can sign up for the same activity"""
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        response1 = client.post("/activities/Art Club/signup", params={"email": email1})
        response2 = client.post("/activities/Art Club/signup", params={"email": email2})
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify both are in the participants list
        activities_response = client.get("/activities")
        art_club = activities_response.json()["Art Club"]
        assert email1 in art_club["participants"]
        assert email2 in art_club["participants"]
    
    def test_signup_same_student_different_activities(self, client):
        """Test that the same student can sign up for multiple activities"""
        email = "versatile_student@mergington.edu"
        
        response1 = client.post("/activities/Basketball Team/signup", params={"email": email})
        response2 = client.post("/activities/Drama Club/signup", params={"email": email})
        
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestRoot:
    """Test the root endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivityValidation:
    """Test activity validation and business logic"""
    
    def test_participant_count_after_signup(self, client):
        """Test that participant count increases after signup"""
        email = "counter@mergington.edu"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()["Drama Club"]["participants"])
        
        # Sign up
        client.post("/activities/Drama Club/signup", params={"email": email})
        
        # Get new count
        response = client.get("/activities")
        new_count = len(response.json()["Drama Club"]["participants"])
        
        assert new_count == initial_count + 1
    
    def test_email_validation_format(self, client):
        """Test signup with various email formats"""
        # Valid email
        response = client.post(
            "/activities/Math Club/signup",
            params={"email": "valid@mergington.edu"}
        )
        assert response.status_code == 200
        
        # The API doesn't validate email format, so other formats will also work
        response = client.post(
            "/activities/Gym Class/signup",
            params={"email": "any_string"}
        )
        assert response.status_code == 200
