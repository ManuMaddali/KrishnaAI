import os
import chromadb
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader
from langchain.document_loaders.pdf import PyPDFDirectoryLoader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScriptureRetriever:
    def __init__(self, scripture_dir="scriptures"):
        self.embeddings = OpenAIEmbeddings()
        self.db_path = "db/scripture_vectors"
        os.makedirs(self.db_path, exist_ok=True)
        
        # Check if DB exists, otherwise create it
        if not os.path.exists(f"{self.db_path}/chroma.sqlite3"):
            logger.info("Creating vector database for scriptures...")
            self._create_vector_db(scripture_dir)
            logger.info("Vector database created successfully!")
        else:
            logger.info("Loading existing vector database...")
        
        # Load the vector DB
        self.vectordb = Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings
        )
    
    def _create_vector_db(self, scripture_dir):
        """Create vector store from scripture PDFs"""
        try:
            # Load PDF documents
            loader = PyPDFDirectoryLoader(scripture_dir)
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} documents from {scripture_dir}")
            
            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100
            )
            chunks = text_splitter.split_documents(documents)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # Create and persist vector DB
            vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_path
            )
            vectordb.persist()
            logger.info(f"Vector database persisted to {self.db_path}")
            return vectordb
        except Exception as e:
            logger.error(f"Error creating vector database: {str(e)}")
            raise
    
    def retrieve_relevant_passages(self, query, k=3):
        """Get the most relevant scripture passages for a query"""
        try:
            results = self.vectordb.similarity_search_with_score(query, k=k)
            passages = []
            
            for doc, score in results:
                if score < 0.8:  # Only return relevant matches
                    source = doc.metadata.get("source", "Unknown")
                    passages.append({
                        "content": doc.page_content,
                        "source": source,
                        "score": score
                    })
            
            logger.info(f"Retrieved {len(passages)} relevant passages for query: {query}")
            return passages
        except Exception as e:
            logger.error(f"Error retrieving passages: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    retriever = ScriptureRetriever()
    results = retriever.retrieve_relevant_passages("What is the nature of dharma?")
    for r in results:
        print(f"From {r['source']}:")
        print(r['content'])
        print("-" * 80) 