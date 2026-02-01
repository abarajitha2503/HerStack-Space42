from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

DATA_DIR = Path(__file__).resolve().parent / "data"

def create_retriever_for_candidate(cv_text: str, target_role: str):
    """Create retriever with job description + CV"""
    
    embeddings = OllamaEmbeddings(model="mxbai-embed-large")
    documents = []
    
    # Load job description
    role_path = DATA_DIR / "roles" / f"{target_role}.md"
    if role_path.exists():
        job_text = role_path.read_text(encoding="utf-8")
        documents.append(Document(
            page_content=job_text,
            metadata={"source_type": "job_description"}
        ))
    
    # Load company info
    company_path = DATA_DIR / "company.md"
    if company_path.exists():
        company_text = company_path.read_text(encoding="utf-8")
        documents.append(Document(
            page_content=company_text,
            metadata={"source_type": "company_info"}
        ))
    
    # Add CV
    if cv_text:
        documents.append(Document(
            page_content=cv_text,
            metadata={"source_type": "resume"}
        ))
    
    # Split and create vectorstore
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    split_docs = text_splitter.split_documents(documents)
    
    vectorstore = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings
    )
    
    return vectorstore.as_retriever(search_kwargs={"k": 6})