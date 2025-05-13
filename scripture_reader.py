import os
import re
import logging
from pypdf import PdfReader
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScriptureReader:
    def __init__(self, scripture_dir="scriptures"):
        self.scripture_dir = scripture_dir
        self.scripture_cache = {}
        self._load_scriptures()
        
    def _load_scriptures(self):
        """Load all PDF scriptures into memory"""
        try:
            if not os.path.exists(self.scripture_dir):
                logger.warning(f"Scripture directory {self.scripture_dir} does not exist")
                return
                
            pdf_files = [f for f in os.listdir(self.scripture_dir) if f.endswith('.pdf')]
            
            if not pdf_files:
                logger.warning(f"No PDF files found in {self.scripture_dir}")
                return
                
            logger.info(f"Found {len(pdf_files)} scripture PDFs to load")
            
            for pdf_file in pdf_files:
                try:
                    file_path = os.path.join(self.scripture_dir, pdf_file)
                    logger.info(f"Loading scripture from {file_path}")
                    
                    reader = PdfReader(file_path)
                    text = ""
                    
                    # Extract text from all pages
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        
                        # Fix encoding issues by replacing problematic characters
                        page_text = page_text.encode('utf-8', 'replace').decode('utf-8')
                        
                        # Fix missing spaces between words by adding spaces before capital letters in the middle of words
                        page_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', page_text)
                        
                        # Fix common patterns where spaces are missing
                        page_text = re.sub(r'([.,;:!?])([a-zA-Z])', r'\1 \2', page_text)
                        
                        # Add spaces between words that are incorrectly joined
                        # This helps with cases like "Thisholyscripture" -> "This holy scripture"
                        word_pattern = re.compile(r'([a-z])([A-Z])')
                        page_text = word_pattern.sub(r'\1 \2', page_text)
                        
                        # Add another pass to catch lowercase+uppercase without spaces
                        # This handles cases like "religiousteachings" -> "religious teachings"
                        for i in range(3):  # Multiple passes to catch nested issues
                            page_text = re.sub(r'([a-z]{3,})([A-Z])', r'\1 \2', page_text)
                        
                        text += page_text + "\n\n"
                        
                    # Store in cache
                    self.scripture_cache[pdf_file] = self._preprocess_text(text)
                    logger.info(f"Successfully loaded {pdf_file} ({len(text)} characters)")
                    
                except Exception as e:
                    logger.error(f"Error loading {pdf_file}: {str(e)}")
                    
            logger.info(f"Finished loading {len(self.scripture_cache)} scripture files")
            
        except Exception as e:
            logger.error(f"Error in _load_scriptures: {str(e)}")
    
    def _preprocess_text(self, text):
        """Preprocess text for better search and display"""
        try:
            # Add spaces after punctuation if missing
            text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)
            
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f"Error in _preprocess_text: {str(e)}")
            return text
        
    def find_relevant_passage(self, query, max_length=300):
        """Find a passage relevant to the query using simple keyword matching"""
        if not self.scripture_cache:
            return None
            
        query = self._preprocess_text(query)
        query_words = query.split()
        
        best_match = None
        best_score = 0
        
        for source, text in self.scripture_cache.items():
            # Simple keyword matching
            score = sum(1 for word in query_words if word in text)
            
            if score > best_score:
                # Find a snippet containing the keywords
                for word in query_words:
                    if word in text:
                        start_idx = max(0, text.find(word) - 100)
                        end_idx = min(len(text), text.find(word) + 200)
                        snippet = text[start_idx:end_idx]
                        
                        # Clean up the snippet
                        snippet = ' '.join(snippet.split())
                        
                        best_match = {
                            "source": source,
                            "content": snippet,
                            "score": score
                        }
                        best_score = score
                        break
        
        return best_match

    def get_scripture_list(self):
        """Get list of available scriptures"""
        return [{
            "id": pdf_file,
            "name": pdf_file.replace('.pdf', '').replace('-', ' ').replace('_', ' ')
        } for pdf_file in self.scripture_cache.keys()]
        
    def get_scripture_by_keyword(self, keyword):
        """Search for a keyword across all scriptures"""
        results = []
        
        for pdf_file, content in self.scripture_cache.items():
            if keyword.lower() in content.lower():
                # Find the context around the keyword
                index = content.lower().find(keyword.lower())
                start = max(0, index - 100)
                end = min(len(content), index + len(keyword) + 100)
                
                context = "..." + content[start:end] + "..."
                
                # Clean up the context
                context = context.replace("\n", " ")
                context = re.sub(r'\s+', ' ', context).strip()
                
                results.append({
                    "source": pdf_file.replace('.pdf', ''),
                    "context": context
                })
                
        return results
        
    def search_scriptures(self, query):
        """Search across all scriptures for the given query"""
        results = []
        
        for pdf_file, content in self.scripture_cache.items():
            if query.lower() in content.lower():
                # Find the context around the query
                idx = content.lower().find(query.lower())
                start = max(0, idx - 100)
                end = min(len(content), idx + len(query) + 100)
                
                # Extract snippet with context
                snippet = content[start:end]
                snippet = snippet.replace("\n", " ")
                snippet = re.sub(r'\s+', ' ', snippet)
                
                # Add ... at the beginning/end if not at the bounds
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                
                results.append({
                    "scripture": pdf_file.replace('.pdf', ''),
                    "snippet": snippet
                })
                
        return results

# Testing
if __name__ == "__main__":
    reader = ScriptureReader()
    query = "dharma purpose duty"
    result = reader.find_relevant_passage(query)
    
    if result:
        print(f"Source: {result['source']}")
        print(f"Content: {result['content']}")
        print(f"Score: {result['score']}")
    else:
        print("No relevant passage found.") 