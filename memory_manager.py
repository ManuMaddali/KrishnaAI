import sqlite3
import json
import os
from datetime import datetime
from langchain.memory import ConversationBufferMemory
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self, db_path="db/krishna_memory.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.lock = threading.RLock()  # Add thread lock for database operations
        self._create_tables()
        self.conversation_memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
        logger.info(f"Memory manager initialized with database at {db_path}")
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create conversations table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                timestamp TEXT,
                message TEXT,
                sender TEXT
            )
            ''')
            
            # Create mood check-ins table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mood_checkins (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                timestamp TEXT,
                mood TEXT,
                notes TEXT
            )
            ''')
            
            # Create spiritual insights table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS spiritual_insights (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                timestamp TEXT,
                insight TEXT,
                context TEXT
            )
            ''')
            
            # Create user_info table for persistent information
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_info (
                id INTEGER PRIMARY KEY,
                key TEXT,
                value TEXT,
                info_type TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            ''')
            
            # Create deleted_sessions table to track deleted conversations
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_sessions (
                id INTEGER PRIMARY KEY,
                session_id TEXT UNIQUE,
                deleted_at TEXT
            )
            ''')
            
            self.conn.commit()
            logger.info("Database tables created/confirmed")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def save_message(self, user_id, message, sender):
        """Save a message to the conversation history"""
        try:
            timestamp = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT INTO conversations (user_id, timestamp, message, sender) VALUES (?, ?, ?, ?)",
                (user_id, timestamp, message, sender)
            )
            self.conn.commit()
            
            # Also add to LangChain memory
            if sender == "user":
                self.conversation_memory.chat_memory.add_user_message(message)
            else:
                self.conversation_memory.chat_memory.add_ai_message(message)
            
            logger.info(f"Saved {sender} message for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
    
    def get_recent_conversations(self, user_id, limit=10):
        """Get recent conversations for a user"""
        try:
            self.cursor.execute(
                "SELECT timestamp, message, sender FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error retrieving conversations: {str(e)}")
            return []
    
    def save_mood(self, user_id, mood, notes=""):
        """Save a mood check-in"""
        try:
            timestamp = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT INTO mood_checkins (user_id, timestamp, mood, notes) VALUES (?, ?, ?, ?)",
                (user_id, timestamp, mood, notes)
            )
            self.conn.commit()
            logger.info(f"Saved mood '{mood}' for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving mood: {str(e)}")
    
    def save_insight(self, user_id, insight, context=""):
        """Save a spiritual insight"""
        try:
            timestamp = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT INTO spiritual_insights (user_id, timestamp, insight, context) VALUES (?, ?, ?, ?)",
                (user_id, timestamp, insight, context)
            )
            self.conn.commit()
            logger.info(f"Saved spiritual insight for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving insight: {str(e)}")
    
    def get_memory_context(self, user_id):
        """Get memory formatted as context for the LLM"""
        try:
            # Get mood history
            with self.lock:
                self.cursor.execute(
                    "SELECT mood, timestamp FROM mood_checkins WHERE user_id = ? ORDER BY timestamp DESC LIMIT 3",
                    (user_id,)
                )
                mood_history = self.cursor.fetchall()
            
            # Format as context
            if not mood_history:
                return ""
                
            context = "Previous moods detected:\n"
            for mood, ts in mood_history:
                date = ts.split("T")[0]
                time = ts.split("T")[1].split(".")[0]
                context += f"- {date} {time}: {mood}\n"
            
            return context
        except Exception as e:
            logger.error(f"Error generating memory context: {str(e)}")
            return ""
    
    def load_conversation_history(self, user_id, limit=20):
        """Load conversation history into memory from database"""
        try:
            # Clear existing memory
            self.chat_memory = []
            
            # Get conversation history ordered by timestamp ascending (oldest first)
            with self.lock:
                self.cursor.execute(
                    "SELECT message, sender FROM conversations WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (user_id, limit)
                )
                history = self.cursor.fetchall()
            
            # Add to memory
            for message, sender in history:
                self.chat_memory.append({"role": "user" if sender == "user" else "assistant", "content": message})
            
            logger.info(f"Loaded {len(history)} messages into conversation memory for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}")
    
    def close(self):
        """Close the database connection"""
        try:
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
    
    def save_user_info(self, key, value, info_type='general'):
        """Save or update persistent user information"""
        try:
            timestamp = datetime.now().isoformat()
            
            with self.lock:
                # Check if this key already exists
                self.cursor.execute(
                    "SELECT id FROM user_info WHERE key = ?",
                    (key,)
                )
                existing = self.cursor.fetchone()
                
                if existing:
                    # Update existing record
                    self.cursor.execute(
                        "UPDATE user_info SET value = ?, info_type = ?, updated_at = ? WHERE key = ?",
                        (value, info_type, timestamp, key)
                    )
                else:
                    # Insert new record
                    self.cursor.execute(
                        "INSERT INTO user_info (key, value, info_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (key, value, info_type, timestamp, timestamp)
                    )
                
                self.conn.commit()
                logger.info(f"Saved user info: {key}={value} (type: {info_type})")
                return True
        except Exception as e:
            logger.error(f"Error saving user info: {str(e)}")
            return False
    
    def get_user_info(self, key=None, info_type=None):
        """Get persistent user information"""
        try:
            with self.lock:
                if key:
                    # Get specific key
                    self.cursor.execute(
                        "SELECT key, value, info_type FROM user_info WHERE key = ?",
                        (key,)
                    )
                    result = self.cursor.fetchone()
                    if result:
                        return {"key": result[0], "value": result[1], "type": result[2]}
                    return None
                elif info_type:
                    # Get all info of a specific type
                    self.cursor.execute(
                        "SELECT key, value FROM user_info WHERE info_type = ?",
                        (info_type,)
                    )
                    results = self.cursor.fetchall()
                    return {row[0]: row[1] for row in results}
                else:
                    # Get all user info
                    self.cursor.execute("SELECT key, value, info_type FROM user_info")
                    results = self.cursor.fetchall()
                    return [{"key": row[0], "value": row[1], "type": row[2]} for row in results]
        except Exception as e:
            logger.error(f"Error retrieving user info: {str(e)}")
            return None
    
    def mark_session_deleted(self, session_id):
        """Mark a session as deleted in the persistent database"""
        try:
            timestamp = datetime.now().isoformat()
            with self.lock:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO deleted_sessions (session_id, deleted_at) VALUES (?, ?)",
                    (session_id, timestamp)
                )
                self.conn.commit()
            logger.info(f"Marked session {session_id} as deleted")
            return True
        except Exception as e:
            logger.error(f"Error marking session as deleted: {str(e)}")
            return False
    
    def is_session_deleted(self, session_id):
        """Check if a session has been previously deleted"""
        try:
            with self.lock:
                self.cursor.execute(
                    "SELECT session_id FROM deleted_sessions WHERE session_id = ?",
                    (session_id,)
                )
                result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if session is deleted: {str(e)}")
            return False
    
    def get_all_deleted_sessions(self):
        """Get a list of all deleted session IDs"""
        try:
            with self.lock:
                self.cursor.execute("SELECT session_id FROM deleted_sessions")
                results = self.cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error retrieving deleted sessions: {str(e)}")
            return []
    
    def delete_message(self, message_id):
        """Delete a specific message by its ID"""
        try:
            with self.lock:
                # Extract the numerical part of the message ID (before the underscore)
                # This is used if message_id is in format "{timestamp}_user" or "{timestamp}_krishna"
                if "_" in message_id:
                    parts = message_id.split("_")
                    if len(parts) > 1 and parts[0].isdigit():
                        # Try to match based on timestamp prefix
                        timestamp_prefix = parts[0]
                        self.cursor.execute(
                            "DELETE FROM conversations WHERE id IN (SELECT id FROM conversations WHERE id = ? OR (timestamp LIKE ?))",
                            (message_id, f"%{timestamp_prefix}%")
                        )
                else:
                    # Try direct ID match
                    self.cursor.execute(
                        "DELETE FROM conversations WHERE id = ?",
                        (message_id,)
                    )
                
                rows_deleted = self.cursor.rowcount
                self.conn.commit()
                
                logger.info(f"Deleted {rows_deleted} message(s) with ID {message_id}")
                return rows_deleted > 0
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            return False

# For testing
if __name__ == "__main__":
    # Create test memory manager
    memory = MemoryManager("db/test_memory.db")
    
    # Test saving and retrieving data
    test_user = "test_user_123"
    memory.save_message(test_user, "Hello Krishna", "user")
    memory.save_message(test_user, "Hello my friend, how are you?", "assistant")
    memory.save_mood(test_user, "anxious", "Feeling worried about work")
    memory.save_insight(test_user, "True peace comes from within", "Discussion about anxiety")
    
    # Print context
    print(memory.get_memory_context(test_user))
    memory.close() 