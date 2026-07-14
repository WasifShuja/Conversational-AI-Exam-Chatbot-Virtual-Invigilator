import os
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import asyncio
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_postgres import PGEngine, PGVectorStore
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from google.genai import types
import time
import pdfplumber
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))



Connection_string=os.getenv("CONNECTION_STRING");
Table_name="knowledge_chunks"
Vector_size=768

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def extract_text(filePath):
    print("Extracting Text...")
    extracted_blocks=[]
    with pdfplumber.open(filePath) as pdf:
        print(f"Document Opened Succesfully. Total Pages to Parsed: {len(pdf.pages)}")
        for pageNo,page in enumerate(pdf.pages):
            text=page.extract_text()
            if(text):
                extracted_blocks.append(text)
            else:
                print(f"Warning: Page No: {pageNo} is unable to read.")
    full_Documents="\n\n".join(extracted_blocks)
    return full_Documents

def process_and_chunk_pdf(file_path):
    raw_text=extract_text(file_path)

    if not raw_text.strip():
        print("Error: File Does not Exists on the file Path")
        return

    token_splitter=RecursiveCharacterTextSplitter(
        
        chunk_size=2000,
        chunk_overlap=200
    )

    raw_chunks = token_splitter.split_text(raw_text)
    document_chunks = [Document(page_content=chunk, metadata={"source": file_path}) for chunk in raw_chunks]
    return document_chunks


def createVectorStore():
    embeddings_model=GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        output_dimensionality=768
        
    )

    db_engine=PGEngine.from_connection_string(url=Connection_string)

    vector_store=PGVectorStore.create_sync(
        engine=db_engine,
        table_name=Table_name,
        embedding_service=embeddings_model
    )
    return vector_store



def embed_chunks(document_chunks):
    embeddings_model=GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        output_dimensionality=768
        
    )


    print("Generating Embedding...")
    db_engine=PGEngine.from_connection_string(url=Connection_string)
    vector_store=PGVectorStore.create_sync(
        engine=db_engine,
        table_name=Table_name,
        embedding_service=embeddings_model
    )

    vector_store.add_documents(document_chunks)


def retrieve_context(query,vector_store,k=2,threshold_score=0.8):
    releventDocuments=vector_store.similarity_search_with_score(query,k=k)
    filteredDocuments=[]
    for releventDocument,score in releventDocuments:
        if(score<=threshold_score):
            filteredDocuments.append(releventDocument)

    return filteredDocuments


def generateAnswers(filterDocuments,query):
    
    llm=ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.0
    )

    if not filterDocuments:
        return f"I'm sorry but no relevent asnwer found in database for query: '{query}'"
    
    releventText = "\n\n".join([doc.page_content for doc in filterDocuments])




    system_instruction="You are a strict technical assitant. Only answer question from the context that is provided to you  " \
    "if the query has something that isnt in the context reply with 'I am sorry but the provided documentation does not contain that information'." \
    
    prompt_content=f"Context Chunks:{releventText}\n\nQuestion:{query}"

    reponse=client.models.generate_content_stream(
        model="gemini-3.5-flash",
        contents=prompt_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,

            temperature=1.0,
            max_output_tokens=1000,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            )
        )
    )

                    

    return reponse



query="tell me about M-20"


print("Retrieving relevant documents...")
start_time=time.time()
releventDocuments=retrieve_context(query,createVectorStore(),4,0.7)
print(f"DataBase retrieval time: {time.time()-start_time} seconds")

start_time=time.time()
print("Retrieving relevant response from LLM...")
releventAnswer=generateAnswers(releventDocuments,query)
print(f"Answer Generation Time: {time.time()-start_time} seconds")

start_time=time.time()
print("Answer:\n\n")
print("----------------------------------------------------------")
print("Waiting For API Connection...")

firstTokenRecieved=False
TFFT=0.0

for chunks in releventAnswer:

    if not firstTokenRecieved:
        TFFT=time.time()-start_time
        print(f"Connection Established! TFFT: {TFFT:.2f} seconds")
        firstTokenRecieved=True

    print(chunks.text,end="",flush=True)

print("\n----------------------------------------------------------")

total_time=time.time()-start_time
print(f"Actual Answer Generation Time: {total_time} seconds")

if(firstTokenRecieved):
    print(f"Actual Time for streaming the response: {total_time-TFFT:.2f} seconds")
