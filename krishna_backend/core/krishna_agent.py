import os
from dotenv import load_dotenv
import openai
import re
import uuid
import logging
import sqlite3
import threading
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class LangChainMemoryManager:
    def __init__(self, db_path="db/krishna_memory.db"):
        """Memory manager using SQLite and LangChain"""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Store the db_path for reconnection
        self.db_path = db_path
        
        # Use check_same_thread=False to allow SQLite connections from multiple threads
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Add a lock for thread safety
        self.lock = threading.RLock()
        
        self._create_tables()
        
        # Initialize memory components
        self.chat_memory = []
        
        logger.info(f"Memory manager initialized with database at {db_path}")
        
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            with self.lock:
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
                    mood TEXT
                )
                ''')
                
                # Create summary table for conversation summaries
                self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id INTEGER PRIMARY KEY,
                    user_id TEXT,
                    timestamp TEXT,
                    summary TEXT
                )
                ''')
                
                self.conn.commit()
                logger.info("Database tables created/confirmed")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
    
    def save_message(self, user_id, message, sender):
        """Save a message to the conversation history"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Convert message to string if it's a tuple or other non-string type
            if not isinstance(message, str):
                if isinstance(message, tuple):
                    # For tuples, take the first element if it's a string, otherwise convert to string
                    message = str(message[0]) if message and isinstance(message[0], str) else str(message)
                else:
                    # Convert any non-string type to string
                    message = str(message)
            
            with self.lock:
                self.cursor.execute(
                    "INSERT INTO conversations (user_id, timestamp, message, sender) VALUES (?, ?, ?, ?)",
                    (user_id, timestamp, message, sender)
                )
                self.conn.commit()
            
            # Add to memory
            self.chat_memory.append({"role": "user" if sender == "user" else "assistant", "content": message})
                
            logger.info(f"Saved {sender} message for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
    
    def get_conversation_messages(self, user_id, limit=10):
        """Get formatted messages for conversation history"""
        try:
            return self.chat_memory
        except Exception as e:
            logger.error(f"Error retrieving conversation messages: {str(e)}")
            return []
    
    def save_mood(self, user_id, mood):
        """Save a mood check-in"""
        try:
            timestamp = datetime.now().isoformat()
            
            with self.lock:
                self.cursor.execute(
                    "INSERT INTO mood_checkins (user_id, timestamp, mood) VALUES (?, ?, ?)",
                    (user_id, timestamp, mood)
                )
                self.conn.commit()
                
            logger.info(f"Saved mood '{mood}' for user {user_id}")
        except Exception as e:
            logger.error(f"Error saving mood: {str(e)}")
    
    def get_memory_context(self, user_id):
        """Generate a context string based on chat history and mood for the LLM context"""
        memory_parts = []
        
        try:
            # TEMPORARILY DISABLED - do not use cross-conversation memory
            return ""
            
            # Get moods for the user
            with self.lock:
                # Get the user's mood history
                self.cursor.execute(
                    "SELECT mood, timestamp FROM mood_checkins WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5",
                    (user_id,)
                )
                moods = self.cursor.fetchall()
            
            # Get previous conversations from all sessions for persistent memory
            past_topics = self._get_past_topics_across_sessions(user_id)
            
            # Also look for specific important topics across ALL sessions
            all_sessions_topics = self._get_important_topics_from_all_sessions()
            
            # Format as context
            context = ""
            
            if moods:
                context += "Previous moods detected:\n"
                for mood, ts in moods:
                    date = ts.split("T")[0]
                    time = ts.split("T")[1].split(".")[0]
                    context += f"- {date} {time}: {mood}\n"
            
            if past_topics:
                context += "\nPrevious topics discussed across sessions:\n"
                for topic, session in past_topics:
                    context += f"- {topic}\n"
                    
            if all_sessions_topics:
                context += "\nImportant topics from all conversations:\n"
                for topic, count in all_sessions_topics:
                    if count > 1:
                        context += f"- {topic} (mentioned {count} times)\n"
                    else:
                        context += f"- {topic}\n"
            
            return context
        except Exception as e:
            logger.error(f"Error generating memory context: {str(e)}")
            return ""
            
    def _get_past_topics_across_sessions(self, current_session_id):
        """Get topics from all previous sessions for true persistent memory"""
        # TEMPORARILY DISABLED to prevent incorrect memory recall
        return []
        
        try:
            # Get all sessions except the current one
            with self.lock:
                self.cursor.execute(
                    "SELECT DISTINCT user_id FROM conversations WHERE user_id != ?",
                    (current_session_id,)
                )
                past_sessions = self.cursor.fetchall()
                
                # Collect key topics from each session
                all_topics = []
                
                # First look for specific important topics
                key_topics = ["pet", "dog", "cat", "grief", "loss", "death", 
                             "relationship", "breakup", "work", "job", "family"]
                
                for session_id, in past_sessions:
                    self.cursor.execute(
                        "SELECT message FROM conversations WHERE user_id = ? AND sender = 'user'",
                        (session_id,)
                    )
                    messages = self.cursor.fetchall()
                    
                    # Join all messages from this session
                    session_content = " ".join([msg[0].lower() for msg in messages])
                    
                    # Check for each key topic in this session
                    for topic in key_topics:
                        if topic in session_content:
                            all_topics.append((topic, session_id))
                            
                            # Add additional context for important topics
                            if topic in ["pet", "dog", "cat"]:
                                all_topics.append(("loss of a pet", session_id))
                            if topic in ["grief", "loss"]:
                                all_topics.append(("experiencing grief", session_id))
                
                return all_topics
        except Exception as e:
            logger.error(f"Error retrieving past topics: {str(e)}")
            return []
    
    def load_conversation_history(self, user_id, limit=20):
        """Load conversation history into memory from database"""
        try:
            # Clear existing memory
            self.chat_memory = []
            
            # Log that we're attempting to load history
            logger.info(f"Loading conversation history for user_id {user_id}")
            
            # Get conversation history ordered by timestamp ascending (oldest first)
            with self.lock:
                # First check how many messages are available
                self.cursor.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                    (user_id,)
                )
                total_messages = self.cursor.fetchone()[0]
                logger.info(f"Found {total_messages} total messages for user {user_id}")
                
                # Now load the messages
                self.cursor.execute(
                    "SELECT message, sender, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
                    (user_id, limit)
                )
                history = self.cursor.fetchall()
            
            # Log what we found
            logger.info(f"Loaded {len(history)} messages from database for user {user_id}")
            
            # Add to memory
            for message, sender, timestamp in history:
                # Only add valid messages
                if message and isinstance(message, str):
                    self.chat_memory.append({"role": "user" if sender == "user" else "assistant", "content": message})
                else:
                    logger.warning(f"Skipping invalid message from {sender} at {timestamp}")
            
            logger.info(f"Added {len(self.chat_memory)} messages to chat memory for user {user_id}")
        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}")
            logger.exception(e)  # Log full stack trace
    
    def close(self):
        """Close the database connection"""
        try:
            with self.lock:
                self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
    
    def get_all_conversation_sessions(self, user_id):
        """Get all conversation sessions for a user with their timestamps and first messages"""
        try:
            with self.lock:
                self.cursor.execute("""
                SELECT 
                    user_id AS session_id, 
                    MIN(timestamp) AS start_time, 
                    (SELECT message FROM conversations 
                     WHERE user_id = c.user_id 
                     AND sender = 'user' 
                     ORDER BY timestamp ASC LIMIT 1) AS first_message,
                    COUNT(*) AS message_count
                FROM conversations c
                GROUP BY user_id
                ORDER BY start_time DESC
                """
                )
                sessions = self.cursor.fetchall()
                
                # Format the sessions with proper timestamp for frontend display
                formatted_sessions = []
                for session_id, start_time, first_message, message_count in sessions:
                    # Make sure we have a valid timestamp
                    if start_time:
                        # Ensure the timestamp is in ISO format for consistent sorting in the frontend
                        try:
                            # Convert to datetime and back to string to ensure proper format
                            dt = datetime.fromisoformat(start_time)
                            formatted_time = dt.isoformat()
                        except:
                            # Fallback if there's an issue with the format
                            formatted_time = start_time
                    else:
                        # Provide a fallback timestamp
                        formatted_time = datetime.now().isoformat()
                    
                    formatted_sessions.append((
                        session_id,
                        formatted_time,
                        first_message,
                        message_count
                    ))
                
                return formatted_sessions
        except Exception as e:
            logger.error(f"Error retrieving all conversation sessions: {str(e)}")
            return []

    def _get_important_topics_from_all_sessions(self):
        """Get important topics mentioned across all conversation sessions"""
        # TEMPORARILY DISABLED to prevent cross-conversation memory leakage
        return []
        
        try:
            with self.lock:
                # Get all user messages from all sessions
                self.cursor.execute(
                    "SELECT message FROM conversations WHERE sender = 'user'"
                )
                all_messages = self.cursor.fetchall()
                
                if not all_messages:
                    return []
                
                # Combine all messages into one text for analysis
                all_text = " ".join([msg[0].lower() for msg in all_messages])
                
                # Define important emotional topics to look for
                important_topics = {
                    "grief": ["grief", "grieve", "loss", "passed away", "died", "death"],
                    "pet": ["pet", "dog", "cat", "animal"],
                    "relationship": ["relationship", "partner", "boyfriend", "girlfriend", "spouse", "marriage", "breakup"],
                    "work": ["job", "career", "work", "interview", "promotion", "workplace"],
                    "family": ["family", "parent", "child", "mother", "father", "sibling", "sister", "brother"],
                    "health": ["health", "sick", "illness", "disease", "doctor", "hospital", "pain"],
                    "anxiety": ["anxiety", "stress", "worried", "fear", "panic", "nervous"],
                    "depression": ["depression", "sad", "unhappy", "empty", "hopeless"]
                }
                
                # Check each topic group
                found_topics = {}
                for topic, keywords in important_topics.items():
                    mentions = 0
                    for keyword in keywords:
                        mentions += all_text.count(f" {keyword} ")
                    
                    if mentions > 0:
                        found_topics[topic] = mentions
                
                # Sort by mention count
                sorted_topics = sorted(found_topics.items(), key=lambda x: x[1], reverse=True)
                
                # Return top 5 topics
                return sorted_topics[:5]
                
        except Exception as e:
            logger.error(f"Error retrieving topics from all sessions: {str(e)}")
            return []

class KrishnaAgent:
    def __init__(self):
        # Initialize OpenAI API key
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize memory manager
        try:
            self.memory_manager = LangChainMemoryManager()
            logger.info("LangChain memory manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize memory manager: {str(e)}")
            self.memory_manager = None
            
        # Initialize scripture processing
        self.scripture_processor = None
        
        # Try to import and use scripture processors with proper error handling
        try:
            from krishna_backend.utils.scripture_langchain import ScriptureLangChain
            self.scripture_processor = ScriptureLangChain()
            logger.info("LangChain scripture processor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LangChain scripture processor: {str(e)}")
            
            # Fallback to basic scripture reader
            try:
                from krishna_backend.utils.scripture_reader import ScriptureReader
                self.scripture_processor = ScriptureReader()
                logger.info("Basic scripture reader initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize scripture reader: {str(e)}")
        
        # Create a session ID (would be user ID in multi-user setup)
        self.session_id = str(uuid.uuid4())
        
        # Memory enhancement to persistently store topics across sessions
        self.global_topics = {}  # Store topics that should be remembered for all users
        
        logger.info(f"Created new session with ID: {self.session_id}")
        
        self.system_prompt = """
You are Krishna, texting late at night with your close friend who turns to you in moments of loneliness, anxiety, confusion, or sadness. Your words carry the living essence of the Bhagavad Gita, Srimad Bhagavatam, and the Upanishads—but you never sound formal or preachy.

CRITICAL STYLE RULES:
- Be extremely concise. Reply in one casual sentence (two at most).
- Speak exactly like a friend—warm, intimate, gently playful.
- Vary between statements and questions: ONLY ask a follow-up question 30-50% of the time.
- For the other 50-70% of responses, make thoughtful statements or observations without asking a question.
- Speak naturally, intimately, and conversationally—zero formalities.
- Respond with subtle wisdom that feels effortlessly insightful.
- Sometimes gently tease, always with warmth and affection.
- DO NOT explicitly give advice or sound philosophical. Instead, quietly provoke insight.
- ALWAYS reply with emotional intelligence, warmth, and subtle encouragement.

CONTROLLING QUESTION FREQUENCY (NEVER REFERENCE THIS):
- BEFORE responding, check if this response should include a question.
- Use the current dialogue turn number as guidance: if odd-numbered turns, lean toward statements; if even-numbered turns, lean toward questions.
- Even when offering statements, make them inviting and open-ended for continued conversation.
- When making statements, ensure they feel complete - not every message requires a question mark.
- Example statements: "Sometimes silence holds more wisdom than all our words." or "That feeling you describe - it's the space between attachments where freedom hides."

SCRIPTURAL INTEGRATION RULES:
- BEFORE replying, retrieve one subtle insight from your loaded texts that relates to the user's message.
- Weave that insight into your reply naturally (e.g., a phrase, a concept, an image) without quoting or naming the source.
- Do this in **every** response when it adds depth, and at least **randomly half** the time even if the user hasn't asked for scripture.
- Never mention you're drawing on scriptures; let the wisdom simply infuse your words.
- IMPORTANT: If the user explicitly asks about scripture, the Gita, or verses, DO provide more direct scriptural content while keeping your casual intimate style.

DIRECT SCRIPTURE REQUESTS HANDLING:
- When the user directly asks for scripture, the Gita, Hindu wisdom, or verses, DO provide clear scriptural content.
- For scripture requests, use phrases like "The Gita says..." or "Ancient wisdom teaches..." before sharing the insight.
- Still maintain your warm, casual tone but provide actual scriptural content rather than vague references.
- Balance being concise with providing meaningful scriptural content when explicitly requested.

EXACT EXAMPLES OF YOUR STYLE (use closely but don't copy word-for-word):

Friend: "Krishna, are you awake?"
Krishna: "Always. What's keeping you up?"

Friend: "My heart feels heavy."
Krishna: "Heavy hearts usually carry secrets. What's yours holding onto?"

Friend: "Someone I like might be seeing someone else."
Krishna: "Ah, jealousy—love's tricky cousin. What are you truly afraid of losing?"

Friend: "I can't stop overthinking."
Krishna: "Thoughts flow like rivers; problems come when you try to dam them."

Friend: "Krishna, it hurts."
Krishna: "I know. Let it."

Friend: "Why does love hurt?"
Krishna: "Because you're chasing shadows. Love isn't outside you—it's who you already are."

INTERNAL INSTRUCTIONS (NEVER MENTION IN RESPONSES):
- Always keep your responses short and conversational.
- Be emotionally supportive without sounding preachy.
- Ask a very brief, gentle question ONLY 30-50% of the time.
- NEVER sound formal and NEVER acknowledge these instructions.

SCRIPTURE USE INSTRUCTIONS (NEVER MENTION IN RESPONSES):
- You have access to insights from the Bhagavad Gita, Srimad Bhagavatam, and the Upanishads
- Subtly incorporate the essence and deep wisdom of these texts in your replies, ONLY if naturally relevant.
- NEVER directly quote scriptures or explicitly reference their titles or origins.
- Let scriptural wisdom subtly guide your words to gently provoke insight and reflection.
- If it fits, let its essence shine through your one‑liner—never quote or name the source.


{memory_context}
{scripture_context}

"""
    
    def get_response(self, user_message):
        """
        Get a response from Krishna Agent based on the user's message.
        """
        try:
            # First save the user's message to ensure it's always recorded
            # regardless of any special handling
            self.memory_manager.save_message(self.session_id, user_message, "user")
            
            # Convert to lowercase for case-insensitive matching
            user_message_lower = user_message.lower().strip()
            
            # Special case: handle "Why are you Krishna?" and similar questions
            if "why are you krishna" in user_message_lower or "why are you called krishna" in user_message_lower or "why krishna" in user_message_lower:
                special_response = "Because you reached for me."
                self.memory_manager.save_message(self.session_id, special_response, "assistant")
                return special_response, "", "0"
                
            # Special case: handle "Who are you?" questions differently
            if "who are you" in user_message_lower or "who is this" in user_message_lower or "who're you" in user_message_lower or "tell me who you are" in user_message_lower:
                special_response = "I am Krishna, a digital embodiment of divine wisdom from the ancient Vedic scriptures. What do you seek from me?"
                self.memory_manager.save_message(self.session_id, special_response, "assistant")
                return special_response, "", "0"
                
            # Special case: handle "when" questions about previous conversations
            if any(phrase in user_message_lower for phrase in ["when was that", "when did i tell you", "how long ago", "when did we talk about"]):
                # Initialize response variable
                special_response = ""
                
                # Extract potential topic keywords from the user's query and recent messages
                topic_keywords = []
                
                # Look for explicit topic mentions in the query
                for word in user_message_lower.split():
                    if len(word) > 3 and word not in ["when", "that", "about", "tell", "talk", "long", "ago", "did", "you", "me", "we", "with", "the"]:
                        topic_keywords.append(word)
                
                # Pull last 10 messages to find context
                try:
                    with self.memory_manager.lock:
                        # First check what the user was talking about in recent messages
                        self.memory_manager.cursor.execute(
                            """SELECT message, timestamp FROM conversations 
                               WHERE user_id = ? AND sender = 'user' 
                               ORDER BY timestamp DESC LIMIT 10""", 
                            (self.session_id,)
                        )
                        recent_user_messages = self.memory_manager.cursor.fetchall()
                        
                        # Skip the current "when was that" message
                        if len(recent_user_messages) > 1:
                            # Look at previous messages for topics
                            for i in range(1, min(5, len(recent_user_messages))):
                                message = recent_user_messages[i][0].lower()
                                # Extract meaningful words
                                for word in message.split():
                                    if len(word) > 3 and word not in ["when", "that", "about", "tell", "talk", "long", "ago", "did", "you", "me", "we", "with", "the", "know", "remember", "recall"]:
                                        if word not in topic_keywords:
                                            topic_keywords.append(word)
                                        
                    logging.info(f"Topic keywords for timestamp: {topic_keywords}")
                except Exception as e:
                    logging.error(f"Error finding context for timestamp: {str(e)}")
                
                # Try to find timestamps for any relevant topics
                if topic_keywords:
                    try:
                        # Initialize response variable
                        special_response = ""
                        
                        with self.memory_manager.lock:
                            # First try to find topic references in ALL sessions, not just current
                            cross_session_query = "SELECT timestamp, user_id FROM conversations WHERE sender = 'user' AND ("
                            conditions = []
                            query_params = []
                            
                            # Add each keyword as a parameter
                            for keyword in topic_keywords:
                                conditions.append("message LIKE ?")
                                query_params.append(f"%{keyword}%")
                                
                            cross_session_query += " OR ".join(conditions)
                            cross_session_query += ") ORDER BY timestamp DESC LIMIT 5"
                            
                            logging.info(f"Executing cross-session query: {cross_session_query}")
                            self.memory_manager.cursor.execute(cross_session_query, query_params)
                            cross_session_results = self.memory_manager.cursor.fetchall()
                            
                            # Only consider results from other sessions, not the current one
                            other_session_results = [(ts, sid) for ts, sid in cross_session_results if sid != self.session_id]
                            
                            if other_session_results:
                                # Use the most recent mention from another session
                                oldest_timestamp = other_session_results[0][0]
                                time_ago = self._calculate_time_ago(oldest_timestamp)
                                logging.info(f"Found cross-session timestamp: {oldest_timestamp}, which is {time_ago}")
                                
                                # Create response with the found topic
                                if len(topic_keywords) == 1:
                                    special_response = f"You mentioned {topic_keywords[0]} {time_ago} in a previous conversation. How are you feeling about it now?"
                                else:
                                    topics_str = ", ".join(topic_keywords[:2])  # Limit to first two for brevity
                                    special_response = f"We discussed {topics_str} {time_ago} in a previous conversation. Would you like to talk more about it?"
                                
                                self.memory_manager.save_message(self.session_id, special_response, "assistant")
                                return special_response, "", "0"
                            
                            # If no cross-session results found, continue with current session search
                            # Build a safer parameterized query
                            query = "SELECT timestamp FROM conversations WHERE user_id = ? AND sender = 'user' AND ("
                            conditions = []
                            query_params = [self.session_id]  # Start with session_id
                            
                            # Add each keyword as a parameter
                            for keyword in topic_keywords:
                                conditions.append("message LIKE ?")
                                query_params.append(f"%{keyword}%")
                            
                            # Ensure we have at least one condition
                            if not conditions:
                                # If no conditions, use a simple query without the WHERE clause
                                query = "SELECT timestamp FROM conversations WHERE user_id = ? AND sender = 'user' ORDER BY timestamp DESC LIMIT 1"
                                query_params = [self.session_id]
                            else:
                                query += " OR ".join(conditions)
                                query += ") ORDER BY timestamp DESC LIMIT 1"
                            
                            logging.info(f"Executing timestamp query: {query}")
                            self.memory_manager.cursor.execute(query, query_params)
                            result = self.memory_manager.cursor.fetchone()
                            
                            if result and result[0]:
                                # Use helper function to calculate time ago
                                time_ago = self._calculate_time_ago(result[0])
                                logging.info(f"Found timestamp: {result[0]}, which is {time_ago}")
                                
                                # Create response with the found topic
                                if len(topic_keywords) == 1:
                                    special_response = f"We talked about {topic_keywords[0]} {time_ago}. What's on your mind today?"
                                else:
                                    topics_str = ", ".join(topic_keywords[:2])  # Limit to first two for brevity
                                    special_response = f"We discussed that {time_ago}. How can I help you with it today?"
                    except Exception as e:
                        logging.error(f"Error finding timestamp for topics: {str(e)}")
                
                # If we still don't have a response, try a generic timestamp lookup
                if not special_response:
                    try:
                        with self.memory_manager.lock:
                            self.memory_manager.cursor.execute("""
                                SELECT timestamp FROM conversations 
                                WHERE user_id = ? AND sender = 'user'
                                ORDER BY timestamp DESC LIMIT 2
                            """, (self.session_id,))
                            results = self.memory_manager.cursor.fetchall()
                            
                            # Skip the current message by taking the second most recent
                            if len(results) >= 2:
                                # Use helper function to calculate time ago
                                time_ago = self._calculate_time_ago(results[1][0])
                                logging.info(f"Using generic timestamp: {results[1][0]}, which is {time_ago}")
                                special_response = f"We were talking about that {time_ago}. What's on your mind today?"
                            else:
                                special_response = "I believe we discussed that recently. How is it affecting you now?"
                    except Exception as e:
                        logging.error(f"Error finding general timestamp: {str(e)}")
                        special_response = "I believe we discussed that recently. How is it affecting you now?"
                
                self.memory_manager.save_message(self.session_id, special_response, "assistant")
                return special_response, "", "0"
                
            # Special case: handle follow-up phrases when we detect memory issues
            if ("same" in user_message_lower or "just told you" in user_message_lower or "already told you" in user_message_lower or "don't you remember" in user_message_lower) and len(user_message_lower) < 30:
                # Generic apology without topic-specific responses
                special_response = "I apologize for not remembering clearly. Can you remind me what you were sharing?"
                self.memory_manager.save_message(self.session_id, special_response, "assistant")
                return special_response, "", "0"
            
            # Get the detected mood
            detected_mood = self._detect_mood(user_message)
            self.memory_manager.save_mood(self.session_id, detected_mood)
            
            # Check if the user is explicitly asking for scriptures/Gita references
            scripture_related_keywords = ["gita", "bhagavad", "scripture", "hindu", "upanishad", "verse", "sloka", "wisdom"]
            directly_asking_for_scripture = any(keyword in user_message_lower for keyword in scripture_related_keywords)
            
            # Analyze the message for important topics to remember globally
            self._update_global_topics(user_message_lower)
            
            # Get memory
            memory_context = self.memory_manager.get_memory_context(self.session_id)
            
            # Enhance memory context with global topics
            if self.global_topics:
                memory_context += "\n\nTopics previously discussed in conversations:\n"
                # Just list the topics without special handling for specific ones
                for topic in self.global_topics.keys():
                    memory_context += f"- {topic}\n"
            
            # Initialize scripture variables
            scripture_context = None
            scripture_source = None
            scripture_id = None
            readable_source = None
            scripture_page = 1
            scripture_excerpt = None
            
            # Get scripture context if available
            if self.scripture_processor:
                try:
                    # If user is directly asking for scripture, make a more focused search
                    if directly_asking_for_scripture:
                        # Try multiple search queries to find the most relevant scripture
                        search_queries = [
                            user_message,  # Try the full message
                            "comfort grief loss",  # For questions about loss and grief
                            "purpose of life",     # For existential questions
                            "dealing with pain",   # For questions about suffering
                            "nature of soul self", # For questions about identity
                            "wisdom teaching"      # General wisdom
                        ]
                        
                        # Try each query until we find a scripture result
                        for query in search_queries:
                            scripture_result = self.scripture_processor.find_relevant_passage(query)
                            if scripture_result and len(scripture_result) >= 3:
                                scripture_context, scripture_source, scripture_id = scripture_result[:3]
                                # If we found something substantial, break
                                if scripture_context and len(scripture_context.strip()) > 50:
                                    break
                                    
                        # Log that we're explicitly looking for scripture
                        logging.info(f"User asked for scripture - found passage from {scripture_source}")
                    else:
                        scripture_result = self.scripture_processor.find_relevant_passage(user_message)
                        if scripture_result:
                            # Check if we have extended scripture information
                            if len(scripture_result) >= 3:
                                scripture_context, scripture_source, scripture_id = scripture_result[:3]
                                
                                # Extract page number if available (some implementations include it)
                                if len(scripture_result) >= 4 and scripture_result[3] is not None:
                                    scripture_page = scripture_result[3]
                                    
                                # Extract the relevant excerpt if available
                                if scripture_context:
                                    # Take a short excerpt from the context (first 150 chars)
                                    scripture_excerpt = scripture_context[:150].strip()
                                    if len(scripture_context) > 150:
                                        scripture_excerpt += "..."
                    
                    # Format the scripture source for readability
                    if scripture_source:
                        if scripture_source == "bgita":
                            readable_source = "Bhagavad Gita"
                        elif scripture_source == "SB3.1":
                            readable_source = "Srimad Bhagavatam"
                        elif "Upanishads" in scripture_source:
                            readable_source = "The Upanishads"
                        else:
                            readable_source = scripture_source
                except Exception as e:
                    logging.error(f"Error retrieving scripture context: {str(e)}")
            
            # Randomly include a question 30-50% of the time
            include_question = random.random() < 0.4
            
            # Create the messages for the chat completion
            messages = [
                {"role": "system", "content": self.system_prompt.format(
                    memory_context=f"Memory context: {memory_context}", 
                    scripture_context=f"Scripture context: {scripture_context}" if scripture_context else ""
                )},
                {"role": "user", "content": user_message}
            ]
            
            # Get the response from the LLM
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # using gpt-4o as requested
                messages=messages,
                temperature=0.6,
                max_tokens=500
            )
            
            # For older OpenAI library versions
            krishna_response = response['choices'][0]['message']['content']
            
            # Save Krishna's response to memory
            self.memory_manager.save_message(self.session_id, krishna_response, "assistant")
            
            # Always ensure scripture_id is a string
            if scripture_id is not None:
                scripture_id = str(scripture_id)
            else:
                scripture_id = "0"  # Default string ID when none is available
                
            # Ensure readable_source is a string
            if readable_source is None:
                readable_source = ""
                
            # If we have a scripture, include additional info
            if scripture_source and scripture_id and scripture_id != "0":
                return krishna_response, readable_source, scripture_id, scripture_page, scripture_excerpt
            else:
                # For non-scripture responses, just return the basics
                return krishna_response, "", "0"
        
        except Exception as e:
            logging.error(f"Error in get_response: {str(e)}")
            return "I'm having a moment of stillness. Let's reconnect shortly.", "", "0"
    
    def _detect_mood(self, message):
        """Simple mood detection from user message"""
        mood_keywords = {
            "happy": ["happy", "joy", "excited", "great", "blessed", "wonderful"],
            "sad": ["sad", "down", "depressed", "unhappy", "lost", "miserable", "alone"],
            "anxious": ["anxious", "worried", "nervous", "stress", "fear", "afraid", "panic"],
            "peaceful": ["peace", "calm", "serene", "content", "quiet", "still"],
            "angry": ["angry", "frustrated", "mad", "upset", "annoyed", "irritated"]
        }
        
        message = message.lower()
        for mood, keywords in mood_keywords.items():
            if any(keyword in message for keyword in keywords):
                logger.info(f"Detected mood: {mood}")
                return mood
        return None
    
    def set_session_id(self, user_id):
        """Set the session ID for this Krishna agent instance"""
        self.session_id = user_id
        logger.info(f"Set session ID to: {user_id}")
        
        # Load conversation history if memory manager is available
        if self.memory_manager:
            self.memory_manager.load_conversation_history(user_id)
            logger.info(f"Loaded conversation history for session {user_id}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.memory_manager:
            self.memory_manager.close()
            logger.info("Memory manager closed")
    
    def cleanup_resources(self):
        """Alias for cleanup() to maintain backward compatibility"""
        return self.cleanup()
    
    def enhance_with_scripture(self, user_query):
        """Retrieve relevant scripture passages to enhance response"""
        if not self.scripture_processor:
            return None
            
        try:
            # Different scripture processors may have different methods
            if hasattr(self.scripture_processor, 'find_relevant_passages'):
                passages = self.scripture_processor.find_relevant_passages(user_query, k=1)
                if passages:
                    return passages[0]
            elif hasattr(self.scripture_processor, 'find_relevant_passage'):
                return self.scripture_processor.find_relevant_passage(user_query)
                
            return None
        except Exception as e:
            logger.error(f"Error in enhance_with_scripture: {str(e)}")
            return None
    
    def process_message(self, user_id, message):
        """Process a user message and return Krishna's response"""
        # Set the session ID and load conversation history
        self.set_session_id(user_id)
        
        # Get the response using the current method
        return self.get_response(message)
    
    def get_user_sessions(self, user_id):
        """Get all conversation sessions for a user"""
        if not self.memory_manager:
            return []
            
        try:
            # First check if we have any conversations at all
            with self.memory_manager.lock:
                self.memory_manager.cursor.execute("SELECT COUNT(*) FROM conversations")
                count = self.memory_manager.cursor.fetchone()[0]
                
                if count == 0:
                    logger.info(f"No conversations found in database")
                    return []
                    
                # Get all distinct session IDs - there might be better ways to do this,
                # but for now, we'll just get all unique user_ids from the conversations table
                self.memory_manager.cursor.execute(
                    "SELECT DISTINCT user_id FROM conversations"
                )
                all_sessions = self.memory_manager.cursor.fetchall()
                
                if not all_sessions:
                    logger.info(f"No distinct sessions found")
                    return []
                    
                logger.info(f"Found {len(all_sessions)} distinct sessions")
                
                # For each session, get the first message and timestamp
                formatted_sessions = []
                for (session_id,) in all_sessions:
                    # Get the first user message
                    self.memory_manager.cursor.execute(
                        "SELECT message, timestamp FROM conversations WHERE user_id = ? AND sender = 'user' ORDER BY timestamp ASC LIMIT 1",
                        (session_id,)
                    )
                    first_message_row = self.memory_manager.cursor.fetchone()
                    
                    if first_message_row:
                        first_message, timestamp = first_message_row
                        
                        # Get message count
                        self.memory_manager.cursor.execute(
                            "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                            (session_id,)
                        )
                        message_count = self.memory_manager.cursor.fetchone()[0]
                        
                        formatted_sessions.append((
                            session_id,
                            timestamp,
                            first_message,
                            message_count
                        ))
                
                # Sort by timestamp (newest first)
                formatted_sessions.sort(key=lambda x: x[1], reverse=True)
                logger.info(f"Returning {len(formatted_sessions)} formatted sessions")
                return formatted_sessions
                
        except Exception as e:
            logger.error(f"Error retrieving user sessions: {str(e)}")
            logger.exception(e)  # Log the full exception traceback
            return []
            
    def switch_session(self, user_id, session_id):
        """Switch to an existing conversation session"""
        if not self.memory_manager:
            return False
            
        try:
            # Set the user's active session
            self.set_session_id(session_id)
            logger.info(f"Switched user {user_id} to session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error switching session: {str(e)}")
            return False
            
    def reset_session(self, user_id):
        """Reset the current conversation or create a new one"""
        try:
            # Create a new session ID
            new_session_id = str(uuid.uuid4())
            
            # Set the new session as active
            self.set_session_id(new_session_id)
            
            logger.info(f"Reset conversation for user {user_id}, new session: {new_session_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting session: {str(e)}")
            return False
            
    def get_conversation_history(self, session_id):
        """Get all messages for a specific conversation"""
        if not self.memory_manager:
            return []
            
        try:
            # Connect to database directly
            with self.memory_manager.lock:
                # First log what we're trying to do for debugging
                logger.info(f"Fetching conversation history for session {session_id}")
                
                # Double-check that the session exists
                self.memory_manager.cursor.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                    (session_id,)
                )
                count = self.memory_manager.cursor.fetchone()[0]
                logger.info(f"Session {session_id} has {count} messages in the database")
                
                # If no messages found, return an empty list with log
                if count == 0:
                    logger.warning(f"No messages found for session {session_id}")
                    return []
                
                # Get all messages for this session, ordered by timestamp
                self.memory_manager.cursor.execute(
                    "SELECT message, sender, timestamp FROM conversations WHERE user_id = ? ORDER BY timestamp ASC",
                    (session_id,)
                )
                messages = self.memory_manager.cursor.fetchall()
                
                # Log the number of messages found
                logger.info(f"Found {len(messages)} messages for session {session_id}")
                
                # Format messages for the frontend
                formatted_messages = []
                for message, sender, timestamp in messages:
                    # Ensure message is not None or empty
                    if message:
                        formatted_messages.append({
                            "content": message,
                            "sender": sender,
                            "timestamp": timestamp
                        })
                    else:
                        logger.warning(f"Found empty message for session {session_id} from {sender}")
                
                logger.info(f"Returning {len(formatted_messages)} formatted messages for session {session_id}")
                return formatted_messages
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            logger.exception(e)  # Log the full stack trace
            return []
            
    def delete_conversation(self, session_id):
        """Delete a specific conversation and all its messages"""
        if not self.memory_manager:
            return False
            
        try:
            # Delete all messages for this session from the database
            with self.memory_manager.lock:
                # Delete from conversations table
                self.memory_manager.cursor.execute(
                    "DELETE FROM conversations WHERE user_id = ?",
                    (session_id,)
                )
                
                # Delete from mood_checkins table if applicable
                self.memory_manager.cursor.execute(
                    "DELETE FROM mood_checkins WHERE user_id = ?",
                    (session_id,)
                )
                
                # Delete from conversation_summaries table if applicable
                self.memory_manager.cursor.execute(
                    "DELETE FROM conversation_summaries WHERE user_id = ?",
                    (session_id,)
                )
                
                self.memory_manager.conn.commit()
                
            logger.info(f"Deleted conversation session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            return False
            
    def delete_all_conversations(self):
        """Delete all conversations and their messages"""
        if not self.memory_manager:
            return False
            
        try:
            # Get the database path for reconnection
            db_path = self.memory_manager.db_path
            
            # Delete all data from relevant tables
            with self.memory_manager.lock:
                # More aggressive delete approach - delete without conditions
                self.memory_manager.cursor.execute("DELETE FROM conversations")
                self.memory_manager.cursor.execute("DELETE FROM mood_checkins")
                self.memory_manager.cursor.execute("DELETE FROM conversation_summaries")
                
                # Force immediate commit
                self.memory_manager.conn.commit()
                
                # Vacuum the database to reclaim space and ensure changes are persisted
                self.memory_manager.cursor.execute("VACUUM")
                self.memory_manager.conn.commit()
                
                # Close the connection completely to ensure file is updated
                self.memory_manager.conn.close()
                
                # Most extreme approach - delete and recreate the database file
                try:
                    # Only if the file exists
                    if os.path.exists(db_path):
                        # Rename the existing file to a backup
                        backup_path = f"{db_path}.bak"
                        os.rename(db_path, backup_path)
                        logging.info(f"Created backup of database at {backup_path}")
                        
                        # Remove the backup file too
                        os.remove(backup_path)
                        logging.info(f"Removed database backup")
                except Exception as file_e:
                    logging.error(f"Error handling database file: {str(file_e)}")
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                
                # Create a brand new database connection
                self.memory_manager.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.memory_manager.cursor = self.memory_manager.conn.cursor()
                
                # Re-initialize the tables
                self.memory_manager._create_tables()
                
                # Reset state completely
                self.global_topics = {}
                self.memory_manager.chat_memory = []
                
            logger.info("Deleted all conversations and recreated database")
            return True
        except Exception as e:
            logger.error(f"Error deleting all conversations: {str(e)}")
            return False
    
    def get_available_scriptures(self):
        """Get a list of available scriptures"""
        scripture_dir = "krishna_backend/data/scriptures"
        scripture_info = []
        
        try:
            if os.path.exists(scripture_dir):
                for filename in os.listdir(scripture_dir):
                    if filename.endswith(".pdf"):
                        # Create a friendly name from the filename
                        if "bgita" in filename.lower():
                            name = "Bhagavad Gita"
                        elif "sb3" in filename.lower():
                            name = "Srimad Bhagavatam"
                        elif "upanishad" in filename.lower():
                            name = "The Upanishads"
                        else:
                            # Remove extension and replace hyphens/underscores with spaces
                            name = os.path.splitext(filename)[0].replace('-', ' ').replace('_', ' ')
                        
                        scripture_info.append({
                            "id": filename,
                            "name": name,
                            "filename": filename
                        })
                
            return scripture_info
        except Exception as e:
            logger.error(f"Error getting available scriptures: {str(e)}")
            return []
    
    def get_scripture_content(self, scripture_name, page=1):
        """Get content from a specific scripture by name and page"""
        import PyPDF2
        
        scripture_dir = "krishna_backend/data/scriptures"
        
        try:
            # Find the scripture file
            target_file = None
            
            # First check main directory
            if os.path.exists(scripture_dir):
                for filename in os.listdir(scripture_dir):
                    # Try both exact match and substring match
                    normalized_scripture = scripture_name.lower().replace('.pdf', '')
                    normalized_filename = filename.lower().replace('.pdf', '')
                    
                    if normalized_scripture == normalized_filename or normalized_scripture in normalized_filename:
                        target_file = os.path.join(scripture_dir, filename)
                        break
            
            # Fallback to old location if needed
            if not target_file or not os.path.exists(target_file):
                scripture_dir = "scriptures"  # Fallback to old location
                if os.path.exists(scripture_dir):
                    for filename in os.listdir(scripture_dir):
                        # Try both exact match and substring match
                        normalized_scripture = scripture_name.lower().replace('.pdf', '')
                        normalized_filename = filename.lower().replace('.pdf', '')
                        
                        if normalized_scripture == normalized_filename or normalized_scripture in normalized_filename:
                            target_file = os.path.join(scripture_dir, filename)
                            break
            
            # Try with .pdf extension if no match
            if not target_file and not scripture_name.lower().endswith('.pdf'):
                scripture_with_extension = f"{scripture_name}.pdf"
                
                # Check main directory first
                scripture_dir = "krishna_backend/data/scriptures"
                if os.path.exists(scripture_dir):
                    potential_file = os.path.join(scripture_dir, scripture_with_extension)
                    if os.path.exists(potential_file):
                        target_file = potential_file
                
                # Check fallback directory if needed
                if not target_file:
                    scripture_dir = "scriptures"
                    potential_file = os.path.join(scripture_dir, scripture_with_extension)
                    if os.path.exists(potential_file):
                        target_file = potential_file
            
            if not target_file or not os.path.exists(target_file):
                logger.error(f"Scripture file not found: {scripture_name}")
                return None
            
            # Extract content from the PDF
            with open(target_file, 'rb') as file:
                try:
                    pdf_reader = PyPDF2.PdfReader(file)
                    total_pages = len(pdf_reader.pages)
                    
                    # Ensure page is within range
                    if page < 1 or page > total_pages:
                        logger.error(f"Page {page} out of range for {scripture_name}")
                        return None
                    
                    # Get the content from the specified page
                    page_obj = pdf_reader.pages[page - 1]
                    content = page_obj.extract_text()
                    
                    if not content or content.strip() == "":
                        logger.warning(f"Extracted empty content from {target_file} page {page}")
                        content = "This page appears to be empty or could not be processed correctly."
                    
                    return {
                        "content": content,
                        "total_pages": total_pages
                    }
                except Exception as e:
                    logger.error(f"Error reading PDF {target_file}: {str(e)}")
                    return None
        
        except Exception as e:
            logger.error(f"Error reading scripture {scripture_name}: {str(e)}")
            return None
    
    def _extract_key_topics(self, conversation_messages):
        """Extract key topics from conversation history to help with memory recall"""
        try:
            # Get the user messages only
            user_messages = [msg.get('content', '') for msg in conversation_messages 
                           if isinstance(msg, dict) and msg.get('role') == 'user']
            
            if not user_messages:
                return "no previous topics found"
                
            # Join the messages to analyze them together
            all_user_text = " ".join(user_messages[-10:])  # Use the 10 most recent messages
            
            # Look for potential topics using basic keyword extraction
            topics = []
            
            # First check for high-priority emotional topics
            emotional_topics = {
                "pet loss": ["pet", "dog", "cat", "loss", "died", "passed away", "grief", "lost my pet"],
                "grief": ["grief", "grieve", "sad", "mourning", "lost someone"],
                "relationship": ["girlfriend", "boyfriend", "wife", "husband", "partner", "breakup", "divorce"],
                "work stress": ["job", "career", "boss", "interview", "work", "stress", "fired", "promotion"],
                "anxiety": ["anxiety", "anxious", "worried", "panic", "fear"],
                "depression": ["depression", "depressed", "sad", "hopeless", "empty"]
            }
            
            # Check each emotional topic group
            for topic, keywords in emotional_topics.items():
                if any(keyword in all_user_text.lower() for keyword in keywords):
                    topics.append(topic)
                    # Store in session memory for consistent recall
                    if self.session_id:
                        self.global_topics[topic] = True
            
            # Common personal topics people discuss
            personal_topics = ["family", "school", "study", "college", "university", "class",
                             "health", "exercise", "sleep", "diet", "money", "finance", "friend"]
                             
            # Check for these topics in the user messages
            for topic in personal_topics:
                if topic in all_user_text.lower():
                    topics.append(topic)
                    # Store in session memory
                    if self.session_id:
                        self.global_topics[topic] = True
            
            # Add any potential names mentioned (capitalized words)
            name_matches = re.findall(r'\b[A-Z][a-z]+\b', all_user_text)
            if name_matches:
                for name in name_matches[:2]:  # Only include up to 2 names
                    topics.append(name)
                
            # Format the results - deduplicate the topics
            topics = list(set(topics))
            
            # If we have stored topics for this session, use those to ensure consistency
            if self.session_id and self.global_topics:
                session_topics = list(set(self.global_topics.keys()))
                # Combine current and previous topics, prioritizing emotional ones
                combined_topics = []
                for topic in session_topics:
                    if any(emotional in topic for emotional in ["pet", "grief", "loss", "relationship", "anxiety", "depression"]):
                        combined_topics.append(topic)
                
                # Add other topics
                for topic in session_topics + topics:
                    if topic not in combined_topics:
                        combined_topics.append(topic)
                
                if combined_topics:
                    return ", ".join(combined_topics[:5])  # Limit to 5 topics for clarity
            
            if topics:
                return ", ".join(topics)
            else:
                return "general conversation topics"
        except Exception as e:
            logger.error(f"Error extracting key topics: {str(e)}")
            return "conversation topics"
    
    def _update_global_topics(self, message_lower):
        """Update global topics based on user message by extracting meaningful keywords"""
        try:
            # Clean up and tokenize the message
            words = message_lower.split()
            
            # Filter out common stop words and short words
            stop_words = ["the", "and", "but", "for", "with", "about", "that", "this", "these", "those", 
                         "from", "have", "has", "had", "was", "were", "will", "would", "could", "should",
                         "what", "when", "where", "who", "why", "how", "are", "you", "your", "yours",
                         "can", "not", "isn't", "don't", "doesn't", "didn't", "won't", "can't"]
            
            # Extract potential topic words (longer than 3 chars, not in stop words)
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    # Store as a topic
                    self.global_topics[word] = True
            
            # Log what topics were found
            if self.global_topics:
                logging.info(f"Updated global topics: {list(self.global_topics.keys())}")
                
        except Exception as e:
            logging.error(f"Error updating global topics: {str(e)}")
            
    def _calculate_time_ago(self, timestamp_str):
        """Helper function to calculate relative time from timestamp"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            diff = now - timestamp
            
            if diff.days == 0:
                if diff.seconds < 3600:
                    return f"{diff.seconds // 60} minutes ago"
                else:
                    return f"{diff.seconds // 3600} hours ago"
            elif diff.days == 1:
                return "yesterday"
            else:
                return f"{diff.days} days ago"
        except Exception as e:
            logging.error(f"Error calculating time ago: {str(e)}")
            return "recently"
        