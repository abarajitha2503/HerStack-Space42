import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Embeddings
embeddings = OllamaEmbeddings(model="mxbai-embed-large")

db_location = "./chroma_langchain_db"  # Fixed typo
add_documents = not os.path.exists(db_location)

if add_documents:
    print("Loading PDF...")
    pdf_path = "/Users/abarajithalakshmanan/Welcome to Nyxoria – Connecting Expertise.pdf"
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    
    print(f"Loaded {len(pages)} pages from PDF")
    
    print("Splitting into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
    )
    documents = text_splitter.split_documents(pages)
    
    print(f"Created {len(documents)} document chunks")

vectore_store = Chroma(
    collection_name="fourth_wing_collection",
    persist_directory=db_location,  # Fixed typo
    embedding_function=embeddings
)

if add_documents:
    print("Adding documents to vector store...")
    vectore_store.add_documents(documents=documents)
    print("Done! Database created.")
   
retriever = vectore_store.as_retriever(
    search_kwargs={"k": 10}
)
