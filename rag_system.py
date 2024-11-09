import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
import fitz

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize ChromaDB
chroma_client = chromadb.Client()

# Initialize embedding function
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

def get_or_create_collection():
    collection_name = "eu_ai_act"
    try:
        # Try to get existing collection
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    except:
        # Create new collection if it doesn't exist
        collection = chroma_client.create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        
        # Load PDF and add to collection
        try:
            doc = fitz.open("EU_AI_Act.pdf")
            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():  # Only add non-empty pages
                    collection.add(
                        documents=[text],
                        ids=[f"page_{i}"],
                        metadatas=[{"page": i, "source": "EU_AI_Act.pdf"}]
                    )
        except Exception as e:
            print(f"Error loading PDF: {e}")
    
    return collection

def get_relevant_sections(query):
    collection = get_or_create_collection()
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    return results['documents'][0]

def generate_answer(query, return_sources=False):
    try:
        # Get collection
        collection = get_or_create_collection()
        
        # Query collection
        results = collection.query(
            query_texts=[query],
            n_results=3
        )
        
        # Prepare context from results
        relevant_texts = results['documents'][0]
        context = "\n".join(relevant_texts)
        
        # Generate response using OpenAI
        messages = [
            {"role": "system", "content": """You are an AI assistant specialized in the EU AI Act. 
             Provide accurate, clear, and concise answers based on the provided context. 
             When referring to specific parts of the Act, mention this explicitly in your response."""},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\n\nPlease provide a clear answer based on the context, mentioning relevant articles or sections when applicable."}
        ]
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        
        if return_sources:
            return completion.choices[0].message, relevant_texts
        else:
            return completion.choices[0].message
    
    except Exception as e:
        raise Exception(f"Error generating answer: {str(e)}")

def format_source_reference(text):
    """Format the source text for display"""
    # You can add additional formatting logic here
    return text.strip()

if __name__ == "__main__":
    # Test the system
    query = "What is the EU AI Act?"
    answer, sources = generate_answer(query, return_sources=True)
    print("Answer:", answer.content)
    print("\nSources:")
    for i, source in enumerate(sources, 1):
        print(f"\nSource {i}:")
        print(format_source_reference(source))