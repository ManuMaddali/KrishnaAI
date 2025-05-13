"""
Input validation and sanitization utilities for Krishna AI.
"""
import re
import html
import logging

logger = logging.getLogger(__name__)

def sanitize_user_input(text):
    """
    Sanitize user input to prevent injection attacks and remove problematic characters.
    
    Args:
        text (str): The input text to sanitize
        
    Returns:
        str: The sanitized text
    """
    if not text:
        return ""
    
    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception as e:
            logger.error(f"Could not convert input to string: {e}")
            return ""
    
    # Limit text length
    if len(text) > 5000:
        text = text[:5000]
    
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    # Escape HTML to prevent XSS
    text = html.escape(text)
    
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove excessive spaces
    text = re.sub(r' {3,}', '  ', text)
    
    # Trim whitespace
    text = text.strip()
    
    return text

def validate_session_id(session_id):
    """
    Validate a session ID to ensure it's a properly formatted UUID.
    
    Args:
        session_id (str): The session ID to validate
        
    Returns:
        tuple: (is_valid, message_or_value)
    """
    if not session_id:
        return False, "Session ID cannot be empty"
    
    # Check if it's a UUID-like string
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.IGNORECASE)
    
    if not uuid_pattern.match(session_id):
        logger.warning(f"Invalid session ID format: {session_id}")
        return False, "Invalid session ID format"
    
    return True, session_id

def validate_message(message, max_length=1000):
    """
    Validate a user message to ensure it meets requirements.
    
    Args:
        message (str): The message to validate
        max_length (int): Maximum allowed message length
        
    Returns:
        tuple: (is_valid, message_or_value)
    """
    if not message:
        return False, "Message cannot be empty"
    
    if not isinstance(message, str):
        return False, "Message must be a string"
    
    if len(message) > max_length:
        return False, f"Message exceeds maximum length ({max_length} characters)"
    
    # Sanitize the message
    sanitized = sanitize_user_input(message)
    
    if not sanitized:
        return False, "Message contains only invalid characters"
    
    return True, sanitized 