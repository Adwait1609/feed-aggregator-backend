import pytest
from utils.text_processing import clean_text, truncate_text

class TestTextProcessing:
    """Test text processing utilities"""
    
    def test_clean_text_removes_html(self):
        """Test HTML tag removal"""
        html_text = "<p>This is <strong>bold</strong> text with <a href='#'>links</a></p>"
        expected = "This is bold text with links"
        
        result = clean_text(html_text)
        assert result == expected
    
    def test_clean_text_removes_extra_whitespace(self):
        """Test extra whitespace removal"""
        messy_text = "This   has    lots  of\n\n\nwhitespace\t\ttabs"
        expected = "This has lots of whitespace tabs"
        
        result = clean_text(messy_text)
        assert result == expected
    
    def test_clean_text_removes_special_chars(self):
        """Test special character removal (except basic punctuation)"""
        special_text = "Hello! This has @#$%^&*() special chars... but keeps basic punctuation-marks."
        expected = "Hello! This has  special chars... but keeps basic punctuation-marks."
        
        result = clean_text(special_text)
        assert result == expected
    
    def test_clean_text_handles_none(self):
        """Test handling None input"""
        result = clean_text(None)
        assert result == ""
    
    def test_clean_text_handles_empty_string(self):
        """Test handling empty string"""
        result = clean_text("")
        assert result == ""
    
    def test_truncate_text_basic(self):
        """Test basic text truncation"""
        long_text = "This is a very long text that should be truncated at some point to fit within the specified limit"
        
        result = truncate_text(long_text, max_length=50)
        
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...")
        assert not result.endswith(" ...")  # Should not have space before ellipsis
    
    def test_truncate_text_short_text(self):
        """Test truncation with text shorter than limit"""
        short_text = "This is short"
        
        result = truncate_text(short_text, max_length=50)
        
        assert result == short_text
        assert not result.endswith("...")
    
    def test_truncate_text_exact_length(self):
        """Test truncation with text exactly at limit"""
        text = "This text is exactly fifty characters in length!"
        
        result = truncate_text(text, max_length=len(text))
        
        assert result == text
        assert not result.endswith("...")
    
    def test_truncate_text_word_boundary(self):
        """Test that truncation respects word boundaries"""
        text = "This is a test of word boundary respect in truncation"
        
        result = truncate_text(text, max_length=25)
        
        # Should not end with a partial word
        assert not result.rstrip("...").endswith("boundar")
        assert result.endswith("...")
    
    def test_truncate_text_default_length(self):
        """Test truncation with default max length"""
        long_text = "A" * 250  # 250 characters
        
        result = truncate_text(long_text)
        
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

class TestConfigSettings:
    """Test configuration settings"""
    
    def test_settings_import(self):
        """Test that settings can be imported and have expected values"""
        from utils.config import Settings
        
        # Test default values
        settings = Settings()
        assert settings.api_title == "News Aggregator API"  # From .env file
        assert settings.api_version == "1.0.0"
        assert settings.log_level == "INFO"
        assert settings.feed_crawl_interval_minutes == 30
        assert "sqlite" in settings.database_url

class TestDependencies:
    """Test FastAPI dependencies"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token"""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from utils.dependencies import get_current_user
        from unittest.mock import MagicMock
        
        # Mock invalid credentials
        mock_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        mock_db = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)
