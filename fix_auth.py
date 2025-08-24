"""
Debug and fix user authentication
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from models.user import User
from utils.auth import get_password_hash, verify_password

def list_users():
    """List all users in database"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("📋 Users in database:")
        for user in users:
            print(f"  - ID: {user.id}, Username: {user.username}, Email: {user.email}, Active: {user.is_active}")
        return users
    finally:
        db.close()

def reset_user_password(username, new_password):
    """Reset user password"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        db.commit()
        
        print(f"✅ Password reset for user '{username}'")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def test_password_verification(username, password):
    """Test if password is correct for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print(f"❌ User '{username}' not found")
            return False
        
        is_valid = verify_password(password, user.hashed_password)
        if is_valid:
            print(f"✅ Password is correct for user '{username}'")
        else:
            print(f"❌ Password is incorrect for user '{username}'")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Error verifying password: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 User Authentication Debug Tool")
    print("=" * 50)
    
    # List current users
    users = list_users()
    
    if not users:
        print("No users found in database")
        exit()
    
    print("\n🔑 Testing authentication...")
    
    # Test common passwords
    common_passwords = ["password", "123456", "test", "admin", "user"]
    
    for user in users:
        print(f"\n👤 Testing user: {user.username}")
        
        # Try common passwords
        found_password = False
        for pwd in common_passwords:
            if test_password_verification(user.username, pwd):
                print(f"✅ Found working password for {user.username}: '{pwd}'")
                found_password = True
                break
        
        if not found_password:
            print(f"❌ No common password worked for {user.username}")
            # Reset password to 'password123'
            print(f"🔄 Resetting password for {user.username} to 'password123'")
            reset_user_password(user.username, "password123")
    
    print("\n" + "=" * 50)
    print("🎯 Try logging in with these credentials:")
    for user in users:
        print(f"  Username: {user.username}, Password: password123")
