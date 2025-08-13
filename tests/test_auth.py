import pytest
from utils.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    verify_token,
    create_user,
    authenticate_user,
    get_user_by_username
)
from models.user import User
from datetime import timedelta
from fastapi import HTTPException

class TestPasswordFunctions:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("wrongpassword", hashed) is False

class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_and_verify_token(self):
        """Test JWT token creation and verification"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should be able to extract username
        username = verify_token(token)
        assert username == "testuser"
    
    def test_token_with_expiry(self):
        """Test token with custom expiry"""
        data = {"sub": "testuser"}
        token = create_access_token(data, expires_delta=timedelta(minutes=1))
        
        username = verify_token(token)
        assert username == "testuser"
    
    def test_invalid_token(self):
        """Test invalid token verification"""
        # Invalid token should return None
        assert verify_token("invalid.token.here") is None
        assert verify_token("") is None

class TestUserManagement:
    """Test user creation and authentication"""
    
    def test_create_user(self, test_db):
        """Test user creation"""
        user = create_user(
            db=test_db,
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.hashed_password != "testpassword123"  # Should be hashed
    
    def test_create_duplicate_username(self, test_db):
        """Test creating user with duplicate username"""
        # Create first user
        create_user(
            db=test_db,
            username="testuser",
            email="test1@example.com",
            password="password1"
        )
        
        # Try to create second user with same username
        with pytest.raises(HTTPException) as exc_info:
            create_user(
                db=test_db,
                username="testuser",
                email="test2@example.com",
                password="password2"
            )
        
        assert exc_info.value.status_code == 400
        assert "Username already registered" in str(exc_info.value.detail)
    
    def test_create_duplicate_email(self, test_db):
        """Test creating user with duplicate email"""
        # Create first user
        create_user(
            db=test_db,
            username="user1",
            email="test@example.com",
            password="password1"
        )
        
        # Try to create second user with same email
        with pytest.raises(HTTPException) as exc_info:
            create_user(
                db=test_db,
                username="user2",
                email="test@example.com",
                password="password2"
            )
        
        assert exc_info.value.status_code == 400
        assert "Email already registered" in str(exc_info.value.detail)
    
    def test_authenticate_user(self, test_db):
        """Test user authentication"""
        # Create user
        create_user(
            db=test_db,
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        
        # Test correct authentication
        user = authenticate_user(test_db, "testuser", "testpassword123")
        assert user is not None
        assert user.username == "testuser"
        
        # Test wrong password
        user = authenticate_user(test_db, "testuser", "wrongpassword")
        assert user is None
        
        # Test non-existent user
        user = authenticate_user(test_db, "nonexistent", "anypassword")
        assert user is None
    
    def test_get_user_by_username(self, test_db):
        """Test getting user by username"""
        # Create user
        created_user = create_user(
            db=test_db,
            username="testuser",
            email="test@example.com",
            password="testpassword123"
        )
        
        # Get user by username
        retrieved_user = get_user_by_username(test_db, "testuser")
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == "testuser"
        
        # Non-existent user
        assert get_user_by_username(test_db, "nonexistent") is None
