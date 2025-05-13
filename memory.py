import uuid
import datetime
import logging

logger = logging.getLogger(__name__)

class Memory:
    def save_message(self, session_id, role, message):
        """Save a message to the database."""
        try:
            # Check if message is a tuple (response, scripture_source, scripture_id)
            if isinstance(message, tuple):
                message = message[0]  # Extract just the message text
                
            # Ensure message is a string
            if not isinstance(message, str):
                message = str(message)
                
            # Generate a unique message ID
            message_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.cursor.execute(
                "INSERT INTO messages (id, session_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (message_id, session_id, role, message, timestamp)
            )
            self.conn.commit()
            logger.info(f"Saved {role} message for user {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return False 