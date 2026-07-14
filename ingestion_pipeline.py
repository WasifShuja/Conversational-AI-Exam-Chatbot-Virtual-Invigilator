import os
import sys
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import asyncio
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_postgres import PGEngine, PGVectorStore
from langchain_core.documents import Document
from google.genai import types
import time
import pdfplumber
from google import genai
from sqlalchemy.exc import ProgrammingError

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


async def createVectorStore():
    embeddings_model=GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        output_dimensionality=768
        
    )

    db_engine=PGEngine.from_connection_string(url=Connection_string)

    

    vector_store= await PGVectorStore.create(
        engine=db_engine,
        table_name=Table_name,
        embedding_service=embeddings_model
    )
    return vector_store



async def embed_chunks(document_chunks):
    embeddings_model=GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        output_dimensionality=768
        
    )


    print("Generating Embedding...")
    db_engine=PGEngine.from_connection_string(url=Connection_string)


    try:
        await db_engine.ainit_vectorstore_table(
            table_name=Table_name,
            vector_size=Vector_size
        )
    except ProgrammingError as e:
        if not "already exists" in str(e):
            raise e



    vector_store=await PGVectorStore.create(
        engine=db_engine,
        table_name=Table_name,
        embedding_service=embeddings_model
    )

    await vector_store.aadd_documents(document_chunks)


async def retrieve_context(query,vector_store,k=2,threshold_score=0.8):
    releventDocuments=await vector_store.asimilarity_search_with_score(query,k=k)
    filteredDocuments=[]
    for releventDocument,score in releventDocuments:
        if(score<=threshold_score):
            filteredDocuments.append(releventDocument)

    return filteredDocuments


async def generateAnswers(filterDocuments,query):
    
   

    if not filterDocuments:
        return None
    
    releventText = "\n\n".join([doc.page_content for doc in filterDocuments])




    system_instruction="You are a strict technical assitant. Only answer question from the context that is provided to you  " \
    "if the query has something that isnt in the context reply with 'I am sorry but the provided documentation does not contain that information'." \
    
    prompt_content=f"Context Chunks:{releventText}\n\nQuestion:{query}"

    reponse=await client.aio.models.generate_content_stream(
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




async def printAnswer(releventAnswer,start_time):
    
    
    print(f"Answer Generation Time: {time.time()-start_time} seconds")
    start_time=time.time()
    print("Answer:\n\n")
    print("----------------------------------------------------------")

    if releventAnswer is None:
        print("I am sorry but the provided document does not contain that Information.")
        return
    print("Waiting For API Connection...")

    firstTokenRecieved=False
    TFFT=0.0

    async for chunks in releventAnswer:

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


async def GenerateRespone():
    query="tell me about M-20"
    print("Retrieving relevant documents...")
    start_time=time.time()
    vectorStore=await createVectorStore()
    releventDocuments=await retrieve_context(query,vectorStore,4,0.7)
    print(f"DataBase retrieval time: {time.time()-start_time} seconds")
    start_time=time.time()
    print("Retrieving relevant response from LLM...")
    releventAnswer=await generateAnswers(releventDocuments,query)
    await printAnswer(releventAnswer,start_time)
    

async def ingestionPipeline():
    documentChunks=process_and_chunk_pdf('')
    if documentChunks:
        await embed_chunks(documentChunks)


def main():
    asyncio.run(GenerateRespone())

main()


