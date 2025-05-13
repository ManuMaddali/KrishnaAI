# KrishnaAI

KrishnaAI is a conversational agent embodying wisdom from ancient Vedic scriptures, designed to provide thoughtful guidance through text-based exchanges. The agent combines modern natural language processing with timeless philosophical insights from the Bhagavad Gita, Srimad Bhagavatam, and Upanishads.

## Features

- **Natural Conversational Interface**: Interact with Krishna through a simple, text-based interface that feels like chatting with a wise friend
- **Scripture Integration**: Responses incorporate insights from Vedic texts without explicit quotations
- **Memory and Context Awareness**: KrishnaAI remembers previous exchanges and can reference past conversations
- **Mood Detection**: Identifies emotional states to provide more empathetic responses
- **Multi-session Support**: Return to previous conversations or start new ones
- **Database Storage**: Conversations persist between sessions using SQLite (development) or PostgreSQL (production)

## Architecture

KrishnaAI is built with the following components:

- **Core Agent**: `KrishnaAgent` class that processes messages and generates responses
- **Memory Management**: `LangChainMemoryManager` for conversation storage and retrieval
- **Scripture Processing**: Integration with scripture sources for relevant wisdom
- **Entity Tracking**: Recognition of people, places, events, and dates mentioned in conversations

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key (set in environment variables)
- LangChain compatible environment

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ManuMaddali/KrishnaAI.git
   cd KrishnaAI
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   export OPENAI_API_KEY="your-api-key"
   ```

4. Run the application:
   ```
   python app.py
   ```

## Technical Implementation

- Built with Python
- Uses LangChain framework for memory management
- Integrates with OpenAI's API for language processing
- Stores conversations in SQLite/PostgreSQL databases
- Includes entity tracking for maintaining conversation context
- Uses pattern recognition for specific response cases

## Usage

KrishnaAI can address:
- Philosophical questions about purpose, meaning, and existence
- Emotional support during challenging times
- Guidance on relationships, work, and personal growth
- Spiritual inquiry and exploration

## Development

The project is organized into several key modules:
- `krishna_agent.py`: Main agent implementation
- `scripture_reader.py`: Base scripture processing
- `scripture_langchain.py`: LangChain implementation for scripture retrieval
- Additional support modules for database handling and utilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the timeless wisdom of Vedic scriptures
- Built with modern AI and NLP technologies 