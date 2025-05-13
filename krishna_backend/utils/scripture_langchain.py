import os
import logging
from pypdf import PdfReader
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
try:
    from langchain.vectorstores import FAISS
    from langchain.embeddings import OpenAIEmbeddings
    # Test if OpenAI API key is configured
    import openai
    # Ensure API key is available, don't rely on specific error attributes
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set")
    VECTORDB_AVAILABLE = True
except (ImportError, ValueError, AttributeError) as e:
    VECTORDB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Vector database functionality disabled: {str(e)}")
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ScriptureLangChain:
    def __init__(self, scripture_dir="krishna_backend/data/scriptures"):
        self.scripture_dir = scripture_dir
        
        # Try fallback path if directory doesn't exist
        if not os.path.exists(self.scripture_dir):
            self.scripture_dir = "scriptures"
            
        self.documents = []
        self.vectorstore = None
        self._load_scriptures()
        
    def _load_scriptures(self):
        """Load scripture PDFs using LangChain document loaders"""
        try:
            if not os.path.exists(self.scripture_dir):
                logger.warning(f"Scripture directory {self.scripture_dir} does not exist")
                return
                
            pdf_files = [f for f in os.listdir(self.scripture_dir) if f.endswith('.pdf')]
            
            if not pdf_files:
                logger.warning(f"No PDF files found in {self.scripture_dir}")
                return
                
            logger.info(f"Found {len(pdf_files)} scripture PDFs to load with LangChain")
            
            # Process each PDF file
            for pdf_file in pdf_files:
                try:
                    file_path = os.path.join(self.scripture_dir, pdf_file)
                    logger.info(f"Loading scripture from {file_path}")
                    
                    # Use LangChain's PyPDFLoader
                    loader = PyPDFLoader(file_path)
                    # Load all pages, no limit
                    pages = loader.load_and_split()
                    
                    # Add source metadata
                    for page in pages:
                        page.metadata["source"] = pdf_file
                        page.metadata["source_display"] = pdf_file.replace(".pdf", "")
                    
                    # Add to documents collection
                    self.documents.extend(pages)
                    logger.info(f"Successfully loaded {pdf_file} ({len(pages)} pages)")
                    
                except Exception as e:
                    logger.error(f"Error loading {pdf_file}: {str(e)}")
            
            # Split the documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            split_docs = text_splitter.split_documents(self.documents)
            logger.info(f"Split scripture documents into {len(split_docs)} chunks")
            
            # Create vector store if available
            if VECTORDB_AVAILABLE:
                try:
                    embeddings = OpenAIEmbeddings()
                    self.vectorstore = FAISS.from_documents(split_docs, embeddings)
                    logger.info(f"Created FAISS vector store with {len(split_docs)} chunks")
                except Exception as e:
                    logger.error(f"Error creating vector store: {str(e)}")
                    # Fall back to simple storage without embeddings
                    self.documents = split_docs
            else:
                logger.info("Vector database not available, using basic keyword matching")
                self.documents = split_docs
                
        except Exception as e:
            logger.error(f"Error in _load_scriptures: {str(e)}")
    
    def find_relevant_passages(self, query, k=2):
        """Find relevant passages using semantic search"""
        try:
            if self.vectorstore:
                # Use semantic search with the vector store
                results = self.vectorstore.similarity_search_with_score(query, k=k)
                
                passages = []
                for doc, score in results:
                    if score < 1.0:  # Lower score is better in FAISS
                        passages.append({
                            "content": doc.page_content,
                            "source": doc.metadata.get("source_display", doc.metadata.get("source", "Unknown")),
                            "score": score,
                            "page": doc.metadata.get("page", 0)
                        })
                
                logger.info(f"Found {len(passages)} relevant passages for query: {query}")
                return passages
            else:
                # Fallback to keyword matching
                logger.warning("Vector store not available, using basic keyword matching")
                return self._keyword_fallback(query, k)
                
        except Exception as e:
            logger.error(f"Error in find_relevant_passages: {str(e)}")
            return []
    
    def _keyword_fallback(self, query, k=2):
        """Fallback method using basic keyword matching"""
        if not self.documents:
            return []
            
        query_terms = query.lower().split()
        matches = []
        
        for doc in self.documents:
            content = doc.page_content.lower()
            score = sum(1 for term in query_terms if term in content)
            if score > 0:
                matches.append((doc, score))
        
        # Sort by score and take top k
        matches.sort(key=lambda x: x[1], reverse=True)
        
        passages = []
        for doc, score in matches[:k]:
            passages.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source_display", doc.metadata.get("source", "Unknown")),
                "score": score,
                "page": doc.metadata.get("page", 0)
            })
            
        return passages
        
    def find_relevant_passage(self, query):
        """
        Find a single relevant passage, compatible with ScriptureReader format.
        Returns a tuple of (passage_text, source, page_id).
        """
        try:
            passages = self.find_relevant_passages(query, k=1)
            if passages:
                passage = passages[0]
                return (passage["content"], passage["source"], passage["page"])
            return None
        except Exception as e:
            logger.error(f"Error in find_relevant_passage: {str(e)}")
            return None 