from flask import Flask, request, render_template, jsonify, session, send_from_directory
from flask_cors import CORS
import os
import uuid
from dotenv import load_dotenv
import atexit
import logging
from datetime import datetime, timedelta
import sys
import re
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import time
import importlib.util
from typing import Tuple, Dict, List, Any, Optional, Union
from collections import defaultdict, Counter
import json

# Add parent directory to sys.path to allow imports from the krishna_backend package
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import KrishnaAgent from core module
from krishna_backend.core.krishna_agent import KrishnaAgent
from krishna_backend.core.config import config

# Import custom validators
from krishna_backend.core.validators import validate_message, validate_session_id, sanitize_user_input

# Set debug mode
config.DEBUG_MODE = True

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize the Flask app with static folder configuration
app = Flask(__name__, 
           static_folder=os.path.join(os.path.dirname(__file__), '..', '..', 'static'),
           static_url_path='/static',
           template_folder=os.path.join(os.path.dirname(__file__), '..', '..', 'templates'))

# Configure secure CORS settings using the config
CORS(app, 
     resources={r"/*": {"origins": config.CORS_ALLOWED_ORIGINS}}, 
     supports_credentials=True)

# Set a secret key for session management from config
app.secret_key = config.FLASK_SECRET_KEY

# Configure session security settings
app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = config.SESSION_COOKIE_SAMESITE

# Fix for running behind proxies
app.wsgi_app = ProxyFix(app.wsgi_app)

# Initialize the Krishna agent
krishna = KrishnaAgent()
logger.info("Krishna agent initialized")

# In-memory rate limiting store (simple implementation)
rate_limits = {}

# Rate limiting decorator
def rate_limit(limit_per_minute=5):
    """Rate limiting decorator for endpoints"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            
            # Check if this IP is in the rate limit store
            current_time = time.time()
            if client_ip in rate_limits:
                # Get request history
                request_history = rate_limits[client_ip]
                
                # Remove requests older than 1 minute
                request_history = [t for t in request_history if current_time - t < 60]
                
                # Check if limit exceeded
                if len(request_history) >= limit_per_minute:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429
                
                # Add current request time
                request_history.append(current_time)
                rate_limits[client_ip] = request_history
            else:
                # First request from this IP
                rate_limits[client_ip] = [current_time]
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Helper function to get or create a session
def get_or_create_session():
    """Get the current session ID or create a new one"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    if 'session_id' not in session:
        session['session_id'] = session['user_id']
        
    return session.get('session_id')

# Routes for static files and service worker
@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/service-worker.js')
def serve_service_worker():
    """Serve service worker at root for proper scope"""
    return send_from_directory(app.static_folder, 'service-worker.js')

@app.route('/manifest.json')
def serve_manifest():
    """Serve manifest.json at root for PWA installation"""
    return send_from_directory(app.static_folder, 'manifest.json')

@app.route('/')
def home():
    # Always create a new session when landing on the home page
    new_session_id = str(uuid.uuid4())
    session.clear()  # Clear any existing session data
    session['user_id'] = new_session_id
    session['session_id'] = new_session_id
    session['is_new_conversation'] = True
    logger.info(f"Created new session on home page visit: {new_session_id}")
    return render_template('chat.html')

@app.route('/ask', methods=['POST'])
@rate_limit(limit_per_minute=20)
def ask():
    """Process a message from the user and get Krishna's response"""
    data = request.json
    user_message = data.get('message', '')
    
    # If first message in a session, ALWAYS create a new session ID
    if 'is_first_message' in data and data['is_first_message'] == True:
        new_session_id = str(uuid.uuid4())
        session['session_id'] = new_session_id
        session_id = new_session_id
        logger.info(f"Created new session for first message: {session_id}")
    # If client provided a session_id, use it
    elif data.get('session_id'):
        session_id = data.get('session_id')
        session['session_id'] = session_id
        logger.info(f"Using provided session_id: {session_id}")
    # Otherwise use current session or create new one
    else:
        if 'session_id' in session:
            session_id = session['session_id']
            logger.info(f"Using existing session from cookie: {session_id}")
        else:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            logger.info(f"Created new session because none existed: {session_id}")
    
    # Save this session ID for future requests
    session['session_id'] = session_id
    
    # Validate and sanitize input
    is_valid, sanitized_message = validate_message(user_message)
    if not is_valid:
        return jsonify({'error': sanitized_message}), 400
    
    try:
        # Process message with Krishna agent
        response = krishna.process_message(session_id, sanitized_message)
        
        # Initialize scripture variables
        scripture_source = ""
        scripture_id = "0"
        scripture_page = 1
        scripture_excerpt = None
        
        # Extract response data based on its format (tuple vs string)
        if isinstance(response, tuple):
            if len(response) >= 5:  # New format with page and excerpt
                krishna_response, scripture_source, scripture_id, scripture_page, scripture_excerpt = response
            elif len(response) >= 3:  # Old format with just source and id
                krishna_response, scripture_source, scripture_id = response
            else:
                krishna_response = response[0] if response else "I'm having a moment of stillness."
        else:
            krishna_response = response
        
        # Ensure scripture_id is a string
        scripture_id = str(scripture_id)
        
        # Build the response data
        response_data = {
            'response': krishna_response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add scripture data if available
        if scripture_source and scripture_id and scripture_id != "0":
            response_data['scripture'] = {
                'source': scripture_source,
                'id': scripture_id,
                'page': scripture_page
            }
            
            # Include excerpt if available
            if scripture_excerpt:
                response_data['scripture']['excerpt'] = scripture_excerpt
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({'error': 'Failed to process message', 'details': str(e)}), 500

@app.route('/reset', methods=['POST'])
@rate_limit(limit_per_minute=10)
def reset_conversation():
    """Reset or create a new conversation session"""
    data = request.json or {}
    
    # ALWAYS create a new session ID unless explicitly instructed to switch to a specific one
    if data.get('session_id'):
        # If a specific session ID is provided, switch to that (used for loading previous conversations)
        session_id = data.get('session_id')
        is_valid, session_id_result = validate_session_id(session_id)
        if not is_valid:
            return jsonify({'error': session_id_result}), 400
        logger.info(f"Switching to existing session: {session_id}")
    else:
        # Create a new session ID for a fresh start
        session_id = str(uuid.uuid4())
        logger.info(f"Creating new session on reset: {session_id}")
    
    # Update Flask session
    session['session_id'] = session_id
    session['is_new_conversation'] = True
    
    try:
        # Reset the conversation in the Krishna agent
        success = krishna.reset_session(session_id)
        if success:
            return jsonify({'success': True, 'session_id': session_id})
        else:
            return jsonify({'error': 'Failed to reset conversation'}), 500
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        return jsonify({'error': 'Failed to reset conversation', 'details': str(e)}), 500

@app.route('/get_conversations')
@rate_limit(limit_per_minute=20)
def get_conversations():
    """Get all conversation sessions for the current user"""
    try:
        # DEBUG: Dump every conversation in the database, regardless of user ID
        logger.info("Getting ALL conversations from database")
        
        # Connect directly to the database for diagnostic purposes
        db_path = "db/krishna_memory.db"
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all distinct session IDs
        cursor.execute("SELECT DISTINCT user_id FROM conversations")
        sessions = cursor.fetchall()
        
        formatted_sessions = []
        for (session_id,) in sessions:
            # Get the first user message for each session
            cursor.execute(
                "SELECT message, timestamp FROM conversations WHERE user_id = ? AND sender = 'user' ORDER BY timestamp ASC LIMIT 1",
                (session_id,)
            )
            first_message = cursor.fetchone()
            
            if first_message:
                message, timestamp = first_message
                
                # Format for the frontend
                formatted_sessions.append({
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "first_message": message
                })
        
        conn.close()
        
        logger.info(f"Found {len(formatted_sessions)} total conversations")
        return jsonify({"sessions": formatted_sessions})
        
    except Exception as e:
        logger.error(f"Error in get_conversations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_conversation_messages', methods=['GET'])
@rate_limit(limit_per_minute=30)
def get_conversation_messages():
    """Get messages from a specific conversation session"""
    session_id = request.args.get('session_id')
    
    # Validate session ID
    if session_id:
        is_valid, session_id_result = validate_session_id(session_id)
        if not is_valid:
            return jsonify({'error': session_id_result}), 400
    else:
        return jsonify({'error': 'No session ID provided'}), 400
    
    try:
        # Get messages from Krishna agent
        messages = krishna.get_conversation_history(session_id)
        
        # Log for debugging
        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
        if len(messages) == 0:
            logger.warning(f"No messages found for session {session_id}")
        
        return jsonify({'messages': messages})
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        return jsonify({'error': 'Failed to get conversation messages', 'details': str(e)}), 500

@app.route('/delete_conversation', methods=['POST'])
@rate_limit(limit_per_minute=30)
def delete_conversation():
    """Delete a specific conversation session"""
    data = request.json or {}
    session_id = data.get('session_id')
    
    # Validate session ID
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
        
    is_valid, session_id_result = validate_session_id(session_id)
    if not is_valid:
        return jsonify({'error': session_id_result}), 400
    
    try:
        # Delete the conversation from Krishna agent
        success = krishna.delete_conversation(session_id)
        
        # Clear the session if it's the current one
        if session.get('session_id') == session_id:
            session.pop('session_id', None)
            
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': 'Failed to delete conversation', 'details': str(e)}), 500

@app.route('/delete_all_conversations', methods=['POST'])
def delete_all_conversations():
    """Delete all conversations for the current user"""
    try:
        # Force delete all conversations without user_id check
        success = krishna.delete_all_conversations()
        
        # Force create a new clean session
        new_session_id = str(uuid.uuid4())
        session['session_id'] = new_session_id
        krishna.reset_session(new_session_id)  # Reset to ensure clean state
        
        # Explicitly clear rate limits too to avoid lingering issues
        global rate_limits
        rate_limits = {}
        
        # Return with 'clear_local_storage' flag to instruct the frontend
        # to also clear its local cached conversations
        return jsonify({
            "success": True, 
            "message": "All conversations deleted", 
            "new_session_id": new_session_id,
            "clear_local_storage": True
        })
    except Exception as e:
        logger.error(f"Error deleting all conversations: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_scriptures', methods=['GET'])
def get_scriptures():
    """Get list of available scriptures"""
    try:
        scriptures = krishna.get_available_scriptures()
        return jsonify({"scriptures": scriptures})
    except Exception as e:
        logger.error(f"Error retrieving scriptures: {str(e)}")
        return jsonify({"error": "Could not retrieve scriptures"}), 500

@app.route('/get_scripture_content', methods=['GET'])
def get_scripture_content():
    """Get content from a specific scripture by name and page"""
    scripture_name = request.args.get('name')
    page = request.args.get('page', 1, type=int)
    
    if not scripture_name:
        return jsonify({"error": "No scripture name provided"}), 400
    
    try:
        content = krishna.get_scripture_content(scripture_name, page)
        if content:
            return jsonify({
                "name": scripture_name,
                "page": page,
                "content": content["content"],
                "total_pages": content["total_pages"]
            })
        else:
            return jsonify({"error": "Scripture not found or page out of range"}), 404
    except Exception as e:
        logger.error(f"Error retrieving scripture content: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_scripture/<scripture_id>', methods=['GET'])
def get_scripture_by_id(scripture_id):
    """Get content from a specific scripture by ID and page"""
    page = request.args.get('page', 1, type=int)
    anchor = request.args.get('anchor')
    
    try:
        content = krishna.get_scripture_content(scripture_id, page)
        if content:
            # Enhanced text processing
            raw_content = content["content"]
            
            # Fix encoding issues safely
            try:
                raw_content = raw_content.encode('utf-8', 'replace').decode('utf-8')
            except Exception as e:
                logger.error(f"Error fixing encoding: {str(e)}")
            
            # Simpler, more robust text processing
            # Replace multiple spaces and newlines with single space
            cleaned_content = ' '.join(raw_content.split())
            
            # Only do minimal text processing to avoid issues
            try:
                # Add spaces between words that are incorrectly joined
                cleaned_content = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned_content)
                # Fix common patterns where spaces are missing
                cleaned_content = re.sub(r'([.,;:!?])([a-zA-Z])', r'\1 \2', cleaned_content)
            except Exception as e:
                logger.error(f"Error in text processing: {str(e)}")
                # Use the original content with just basic whitespace normalization
                cleaned_content = ' '.join(raw_content.split())
            
            # Split into reasonable size paragraphs
            paragraphs = []
            current_para = []
            word_count = 0
            
            # Split by sentences for natural paragraphs
            try:
                sentences = cleaned_content.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                
                for sentence in sentences:
                    if not sentence.strip():
                        continue
                        
                    # Add sentence to current paragraph
                    current_para.append(sentence)
                    word_count += len(sentence.split())
                    
                    # If we've reached a reasonable paragraph length, or found a good break point
                    if word_count >= 100 or (word_count >= 50 and sentence.endswith(('.', '!', '?'))):
                        paragraphs.append(' '.join(current_para))
                        current_para = []
                        word_count = 0
                
                # Add any remaining content as the final paragraph
                if current_para:
                    paragraphs.append(' '.join(current_para))
            except Exception as e:
                logger.error(f"Error splitting into paragraphs: {str(e)}")
                # Fallback: use the entire content as a single paragraph
                paragraphs = [cleaned_content]
            
            # Ensure we have at least one paragraph
            if not paragraphs:
                paragraphs = [cleaned_content]
                
            # Create verse objects with paragraph text
            verses = [{"verse_num": i+1, "text": paragraph, "anchor": f"verse_{i+1}"} for i, paragraph in enumerate(paragraphs)]
            
            return jsonify({
                "success": True,
                "title": scripture_id.replace('.pdf', '').replace('-', ' ').replace('_', ' '),
                "page": page,
                "verses": verses,
                "total_pages": content["total_pages"]
            })
        else:
            return jsonify({"success": False, "message": "Scripture not found or page out of range"}), 404
    except Exception as e:
        logger.error(f"Error retrieving scripture content: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Legacy endpoint for compatibility with older clients"""
    data = request.json
    user_message = data.get("message", "")
    session_id = get_or_create_session()
    
    try:
        # Get response from Krishna
        response = krishna.process_message(session_id, user_message)
        
        # Initialize scripture variables
        scripture_source = ""
        scripture_id = "0"
        scripture_page = 1
        scripture_excerpt = None
        
        # Handle different response formats properly
        if isinstance(response, tuple):
            if len(response) >= 5:  # New format with page and excerpt
                krishna_response, scripture_source, scripture_id, scripture_page, scripture_excerpt = response
            elif len(response) >= 3:  # Old format for backward compatibility
                krishna_response, scripture_source, scripture_id = response
            else:
                krishna_response = response[0] if response else "I'm having a moment of stillness."
        else:
            krishna_response = response
            
        # Ensure scripture_id is a string
        scripture_id = str(scripture_id)
        
        # Create JSON response
        response_data = {
            "message": krishna_response,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add scripture data only if there's actual content
        if scripture_source and scripture_source.strip() and scripture_id and scripture_id.strip() and scripture_id != "0":
            scripture_data = {
                "source": scripture_source,
                "id": scripture_id,
                "page": scripture_page
            }
            
            # Include excerpt if available
            if scripture_excerpt:
                scripture_data["excerpt"] = scripture_excerpt
                
            response_data["scripture"] = scripture_data
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/conversation', methods=['GET'])
def debug_conversation():
    """Debug endpoint to get raw conversation data for a session"""
    if not config.DEBUG_MODE:
        return jsonify({"error": "Debug endpoints disabled in production"}), 403
        
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400
        
    try:
        # Connect to the database directly for diagnostic purposes
        import sqlite3
        db_path = "db/krishna_memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get raw data about this session
        cursor.execute(
            "SELECT id, user_id, timestamp, message, sender FROM conversations WHERE user_id = ? ORDER BY timestamp ASC",
            (session_id,)
        )
        raw_messages = cursor.fetchall()
        
        # Format for output
        messages = []
        for msg_id, user_id, timestamp, message, sender in raw_messages:
            messages.append({
                "id": msg_id,
                "user_id": user_id,
                "timestamp": timestamp,
                "message": message,
                "sender": sender
            })
            
        # Count total messages in the database
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_messages = cursor.fetchone()[0]
        
        # Get all unique session IDs
        cursor.execute("SELECT DISTINCT user_id FROM conversations")
        all_sessions = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "session_id": session_id,
            "message_count": len(messages),
            "messages": messages,
            "total_messages_in_db": total_messages,
            "all_sessions": all_sessions
        })
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error. Krishna is meditating on the issue."}), 500

def cleanup_resources():
    """Clean up resources when the application exits"""
    try:
        if krishna:
            krishna.cleanup()
        logger.info("Resources cleaned up.")
    except Exception as e:
        logger.error(f"Error cleaning up resources: {str(e)}")

# Register cleanup to happen at program exit
atexit.register(cleanup_resources)

def run_app(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask application"""
    try:
        # Get port from environment variable if available
        port = int(os.environ.get("PORT", port))
        
        # Start the server with appropriate settings
        # Only enable debug in development, not in production
        app.run(host=host, port=port, debug=debug, ssl_context=None)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        
if __name__ == '__main__':
    run_app() 