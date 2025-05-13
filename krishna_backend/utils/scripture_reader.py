import os
import re
import logging
from pypdf import PdfReader

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScriptureReader:
    def __init__(self, scripture_dir="krishna_backend/data/scriptures"):
        """Initialize scripture reader that loads PDFs into memory"""
        self.scripture_dir = scripture_dir
        self.scriptures = {}
        
        # Try fallback path if directory doesn't exist
        if not os.path.exists(self.scripture_dir):
            self.scripture_dir = "scriptures"
            
        self._load_scriptures()
        
    def _load_scriptures(self):
        """Load all scripture PDFs into memory"""
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
                file_path = os.path.join(self.scripture_dir, pdf_file)
                try:
                    # Load PDF content
                    with open(file_path, 'rb') as f:
                        pdf = PdfReader(f)
                        
                        # Extract text from all pages
                        content = ""
                        
                        for i in range(len(pdf.pages)):
                            page = pdf.pages[i]
                            text = page.extract_text()
                            
                            # Basic cleaning of page text
                            text = re.sub(r'\s+', ' ', text).strip()
                            
                            # Fix encoding issues by replacing problematic characters
                            text = text.encode('utf-8', 'replace').decode('utf-8')
                            
                            # Fix missing spaces between words by adding spaces before capital letters in the middle of words
                            text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
                            
                            # Fix common patterns where spaces are missing
                            text = re.sub(r'([.,;:!?])([a-zA-Z])', r'\1 \2', text)
                            
                            # Add spaces between words that are incorrectly joined
                            # This helps with cases like "Thisholyscripture" -> "This holy scripture"
                            word_pattern = re.compile(r'([a-z])([A-Z])')
                            text = word_pattern.sub(r'\1 \2', text)
                            
                            # Add another pass to catch lowercase+uppercase without spaces
                            # This handles cases like "religiousteachings" -> "religious teachings"
                            for i in range(3):  # Multiple passes to catch nested issues
                                text = re.sub(r'([a-z]{3,})([A-Z])', r'\1 \2', text)
                            
                            content += text + "\n\n"
                        
                        # Create scripture entry
                        self.scriptures[pdf_file] = {
                            'name': pdf_file.replace('.pdf', ''),
                            'content': content,
                            'path': file_path
                        }
                        
                        logger.info(f"Loaded {pdf_file} ({len(pdf.pages)} pages)")
                except Exception as e:
                    logger.error(f"Error loading {pdf_file}: {str(e)}")
                    
            logger.info(f"Successfully loaded {len(self.scriptures)} scriptures")
        except Exception as e:
            logger.error(f"Error loading scriptures: {str(e)}")
    
    def find_relevant_passage(self, query):
        """Find the most relevant passage based on keyword matching"""
        if not self.scriptures:
            logger.warning("No scriptures loaded to search")
            return None
            
        query_words = set(re.findall(r'\w+', query.lower()))
        
        best_match = None
        best_score = 0
        best_source = None
        
        for source, scripture in self.scriptures.items():
            content = scripture['content'].lower()
            
            # Simple scoring based on word matching
            score = sum(1 for word in query_words if word in content)
            
            if score > best_score:
                # Find a relevant passage (simple implementation)
                sentences = re.split(r'(?<=[.!?])\s+', content)
                relevant_sentences = []
                
                for sentence in sentences:
                    sentence_score = sum(1 for word in query_words if word.lower() in sentence.lower())
                    if sentence_score > 0:
                        relevant_sentences.append(sentence)
                
                if relevant_sentences:
                    passage = " ".join(relevant_sentences[:3])  # Take up to 3 relevant sentences
                    best_match = passage
                    best_score = score
                    best_source = scripture['name']
        
        if best_match:
            # Return a tuple of (passage, source, page) for compatibility
            return (best_match, best_source, 1)  # Default to page 1
        
        return None
    
    def get_scripture_content(self, scripture_name, page=1):
        """Get content from a specific scripture file and page"""
        # Find the scripture file
        target_file = None
        try:
            for source in self.scriptures:
                # Make case-insensitive comparison and handle both with/without .pdf extension
                if scripture_name.lower().replace('.pdf', '') in source.lower().replace('.pdf', ''):
                    target_file = source
                    break
                    
            if not target_file:
                logger.warning(f"Scripture {scripture_name} not found, checking exact match")
                # Try exact match if fuzzy match didn't work
                for source in self.scriptures:
                    if os.path.basename(source).lower() == scripture_name.lower():
                        target_file = source
                        break

            # One more fallback: Try with .pdf extension added
            if not target_file and not scripture_name.lower().endswith('.pdf'):
                scripture_with_pdf = f"{scripture_name}.pdf"
                for source in self.scriptures:
                    if scripture_with_pdf.lower() == os.path.basename(source).lower():
                        target_file = source
                        break
                
            if not target_file:
                logger.warning(f"Scripture {scripture_name} not found after multiple attempts")
                return None
            
            # Load the PDF
            file_path = os.path.join(self.scripture_dir, target_file)
            with open(file_path, 'rb') as f:
                pdf = PdfReader(f)
                total_pages = len(pdf.pages)
                
                # Ensure page is within range
                if page < 1 or page > total_pages:
                    logger.warning(f"Page {page} out of range for {target_file}")
                    return None
                
                # Extract content from the requested page
                page_obj = pdf.pages[page - 1]
                content = page_obj.extract_text()
                
                if not content or content.strip() == "":
                    logger.warning(f"Extracted empty content from {target_file} page {page}")
                    content = "This page appears to be empty or could not be processed correctly."
                
                return {
                    'content': content,
                    'total_pages': total_pages
                }
        except Exception as e:
            logger.error(f"Error reading scripture {scripture_name}: {str(e)}")
            return None 