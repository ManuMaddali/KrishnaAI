from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os
import sys
import signal
import atexit
import socket
import logging
import psutil  # You'll need to install this: pip install psutil
import threading

# Import the Krishna agent
from krishna_agent import KrishnaAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Process management functions
def check_port_in_use(port):
    """Check if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_existing_process(port):
    """Kill any process using the specified port."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                if any(f"--port {port}" in ' '.join(cmd) if cmd else False for cmd in [proc.info['cmdline']]):
                    logger.info(f"Killing existing process {proc.info['pid']} using port {port}")
                    psutil.Process(proc.info['pid']).terminate()
    except Exception as e:
        logger.error(f"Error killing existing process: {e}")

def cleanup():
    """Clean up resources when shutting down."""
    try:
        logger.info("Cleaning up resources...")
        # Close any database connections or release resources here
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Register signal handlers
def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

# Register cleanup to happen at exit
atexit.register(cleanup)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for demo - in production use a database
sessions = {}
messages = {}

# Initialize Krishna agent
krishna_agent = KrishnaAgent()

# Initialize user sessions by loading from the database and filtering out deleted ones
def initialize_sessions():
    global sessions, messages
    try:
        logger.info("Loading existing sessions from database...")
        
        # Get all conversations from the database
        all_sessions = krishna_agent.get_user_sessions('all')
        
        # Get list of deleted sessions
        deleted_sessions = krishna_agent.memory_manager.get_all_deleted_sessions()
        logger.info(f"Found {len(deleted_sessions)} deleted sessions to filter out")
        
        # Filter out deleted sessions
        active_sessions = [s for s in all_sessions if s.get('session_id') not in deleted_sessions]
        
        # Add to in-memory storage
        for session in active_sessions:
            session_id = session.get('session_id')
            if session_id:
                sessions[session_id] = {
                    'created_at': session.get('timestamp', time.strftime('%Y-%m-%dT%H:%M:%SZ'))
                }
                
                # Get messages for this session
                session_messages = krishna_agent.get_conversation_history(session_id)
                if session_messages:
                    messages[session_id] = session_messages
                else:
                    messages[session_id] = []
        
        logger.info(f"Loaded {len(active_sessions)} active sessions from the database")
    except Exception as e:
        logger.error(f"Error initializing sessions from database: {e}")

# Initialize Krishna agent with faster startup
def initialize_agent_in_background():
    global krishna_agent
    try:
        logger.info("Starting Krishna agent initialization in background thread")
        krishna_agent = KrishnaAgent()
        logger.info("Krishna agent initialization completed in background thread")
        
        # Initialize sessions after the agent is ready
        initialize_sessions()
    except Exception as e:
        logger.error(f"Error initializing Krishna agent in background: {e}")

# Start initialization in a background thread
threading.Thread(target=initialize_agent_in_background, daemon=True).start()

@app.route('/reset', methods=['POST'])
def reset_conversation():
    data = request.json
    session_id = data.get('session_id') or str(uuid.uuid4())
    
    sessions[session_id] = {'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')}
    messages[session_id] = []
    
    logger.info(f"Created new session: {session_id}")
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    message = data.get('message', '')
    session_id = data.get('session_id')
    
    # If session ID was provided, check if it's been deleted
    if session_id:
        if krishna_agent.memory_manager.is_session_deleted(session_id):
            # If this session was deleted, create a new one instead
            logger.warning(f"Attempted to use deleted session {session_id}, creating new session")
            session_id = str(uuid.uuid4())
            sessions[session_id] = {'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')}
            messages[session_id] = []
    
    # If no session ID or invalid session ID, create a new one
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')}
        messages[session_id] = []
    
    # Add user message
    messages[session_id].append({
        'id': f"{int(time.time() * 1000)}_user",
        'sender': 'user',
        'content': message,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    })
    
    # Use Krishna agent to generate response
    krishna_response = krishna_agent.process_message(session_id, message)
    
    # If the response is a tuple (which might contain scripture references), extract just the response text
    if isinstance(krishna_response, tuple):
        krishna_response = krishna_response[0]
    
    # Add Krishna's response
    messages[session_id].append({
        'id': f"{int(time.time() * 1000)}_krishna",
        'sender': 'krishna',
        'content': krishna_response,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    })
    
    logger.info(f"Message from session {session_id}: {message}")
    return jsonify({'response': krishna_response, 'session_id': session_id})

@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    conversations_list = []
    
    # Get list of deleted session IDs from the database
    deleted_sessions = krishna_agent.memory_manager.get_all_deleted_sessions()
    
    # Get sessions from previous runs that are stored in the database
    db_sessions = krishna_agent.get_user_sessions('all')
    
    # Filter out deleted sessions 
    db_sessions = [s for s in db_sessions if s.get('session_id') not in deleted_sessions]
    
    # Process in-memory sessions first
    for session_id, session_data in sessions.items():
        # Skip if this session has been deleted
        if session_id in deleted_sessions:
            continue
            
        session_messages = messages.get(session_id, [])
        first_user_message = next((m['content'] for m in session_messages if m['sender'] == 'user'), 'New Conversation')
        first_krishna_response = next((m['content'] for m in session_messages if m['sender'] == 'krishna'), '')
        
        conversations_list.append({
            'session_id': session_id,
            'timestamp': session_data.get('created_at'),
            'first_message': first_user_message,
            'first_response': first_krishna_response
        })
    
    # Add database sessions (these might have been from previous runs of the app)
    for session in db_sessions:
        # Skip if this session is already in memory or has been deleted
        if session.get('session_id') in [s['session_id'] for s in conversations_list]:
            continue
            
        conversations_list.append(session)
    
    logger.info(f"Returning {len(conversations_list)} conversations")
    return jsonify({'sessions': conversations_list})

@app.route('/get_conversation_messages', methods=['GET'])
def get_conversation_messages():
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'messages': []})
    
    # Check if this session has been deleted
    if krishna_agent.memory_manager.is_session_deleted(session_id):
        logger.warning(f"Attempted to access deleted session: {session_id}")
        return jsonify({'messages': [], 'error': 'Session has been deleted'})
    
    # First check in-memory messages
    if session_id in messages:
        conversation_messages = messages[session_id]
    else:
        # If not in memory, try to get from database
        conversation_messages = krishna_agent.get_conversation_history(session_id)
    
    logger.info(f"Returning {len(conversation_messages)} messages for session {session_id}")
    return jsonify({'messages': conversation_messages})

@app.route('/delete_conversation', methods=['POST'])
def delete_conversation():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({'success': False, 'error': 'No session ID provided'})
    
    in_memory = False
    # Delete from in-memory storage if it exists there
    if session_id in sessions:
        del sessions[session_id]
        in_memory = True
        
    if session_id in messages:
        del messages[session_id]
        in_memory = True
    
    # Always attempt to delete from the database
    # This handles sessions from previous server runs that are in the database
    # but not in the current server's memory
    success = krishna_agent.delete_conversation(session_id)
    
    if success or in_memory:
        logger.info(f"Deleted session: {session_id}")
        return jsonify({'success': True})
    else:
        # Only return error if neither in memory nor in database
        return jsonify({'success': False, 'error': 'Session not found'})

@app.route('/delete_all_conversations', methods=['POST'])
def delete_all_conversations():
    try:
        # Clear in-memory storage
        sessions.clear()
        messages.clear()
        
        # Call Krishna agent's delete_all_conversations method to clear database and memory
        success = krishna_agent.delete_all_conversations()
        
        if success:
            logger.info("Deleted all conversations successfully")
            return jsonify({'success': True})
        else:
            logger.warning("Partial failure when deleting all conversations")
            return jsonify({'success': True, 'warning': 'Some conversations may not have been deleted'})
    except Exception as e:
        logger.error(f"Error deleting all conversations: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_message', methods=['POST'])
def delete_message():
    data = request.json
    session_id = data.get('session_id')
    message_id = data.get('message_id')
    
    if not session_id or not message_id:
        return jsonify({'success': False, 'error': 'Session ID and Message ID are required'})
    
    # Delete from in-memory storage if it exists there
    if session_id in messages:
        # Find and remove the message by ID
        messages[session_id] = [msg for msg in messages[session_id] if msg.get('id') != message_id]
    
    # Always attempt to delete from the database
    success = krishna_agent.delete_message(session_id, message_id)
    
    logger.info(f"Delete message request: session={session_id}, message={message_id}, success={success}")
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Check if the port is already in use
    if check_port_in_use(port):
        logger.warning(f"Port {port} already in use, attempting to kill existing process...")
        kill_existing_process(port)
        time.sleep(1)  # Give the process time to terminate
        
        # Check again
        if check_port_in_use(port):
            logger.error(f"Port {port} still in use. Please close the application using that port and try again.")
            sys.exit(1)
    
    logger.info(f"Starting Krishna AI server on port {port}...")
    
    try:
        # Make sure we bind to the correct port and make the server visible
        print(f"SERVER STARTING ON PORT {port}")
        sys.stdout.flush()  # Ensure it's immediately visible
        
        # Use only one worker process to avoid multiple processes
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"SERVER FAILED TO START: {e}")
        sys.exit(1) 