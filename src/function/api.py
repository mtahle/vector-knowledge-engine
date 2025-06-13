from pydantic import BaseModel
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
import tempfile
from azure.storage.blob import BlobServiceClient
import re
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configuration
MODEL_NAME = os.getenv('MODEL_NAME', 'multi-qa-MiniLM-L6-cos-v1')  # Changed to Q&A optimized model
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.3'))  # Lowered default threshold
MAX_RESULTS = int(os.getenv('MAX_RESULTS', '5'))
LOCAL_INDEX_DIR = Path('data/index')

def load_index_data():
    """Load index data from either Azure Storage or local filesystem."""
    storage_connection_string = os.getenv('STORAGE_CONNECTION_STRING')
    container_name = os.getenv('STORAGE_CONTAINER_NAME', 'knowledge-base')
    
    # temp directory for downloaded files if using Azure
    temp_dir = None
    if storage_connection_string:
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory: {temp_dir}")
    
    try:
        if storage_connection_string and container_name:
            print("Using Azure Storage for index data...")
            # Initialise Azure Storage client
            blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
            container_client = blob_service_client.get_container_client(container_name)
            
            # Set paths
            index_path = Path(temp_dir) / 'vector.index'
            chunks_path = Path(temp_dir) / 'chunks.json'
            
            # Download files from Azure Storage
            print(f"Downloading files from Azure Storage container '{container_name}'...")
            
            print("Downloading index file...")
            index_blob = container_client.get_blob_client('index/vector.index')
            with open(index_path, 'wb') as f:
                f.write(index_blob.download_blob().readall())
            
            print("Downloading chunks file...")
            chunks_blob = container_client.get_blob_client('index/chunks.json')
            with open(chunks_path, 'wb') as f:
                f.write(chunks_blob.download_blob().readall())
        else:
            print("Using local filesystem for index data...")
            # Set paths to local directory
            index_path = LOCAL_INDEX_DIR / 'vector.index'
            chunks_path = LOCAL_INDEX_DIR / 'chunks.json'
            
            if not index_path.exists() or not chunks_path.exists():
                raise FileNotFoundError(
                    "Index files not found in local directory. "
                    "Please run the index builder first or provide Azure Storage credentials."
                )
        
        # Load the model
        print(f"Loading model {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        print("Model loaded successfully!")
        
        print("Loading FAISS index...")
        index = faiss.read_index(str(index_path))
        print(f"FAISS index loaded successfully! Size: {index.ntotal}")
        
        # Load chunks
        print("Loading chunks...")
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Chunks loaded successfully! Total chunks: {len(chunks)}")
        
        return model, index, chunks
        
    except Exception as e:
        print(f"Error loading index data: {str(e)}")
        raise

# Initialize resources
print(f"Initializing with MODEL_NAME: {MODEL_NAME}")
model, index, chunks = load_index_data()
print("All resources loaded successfully!")

class SearchQuery(BaseModel):
    query: str
    top_k: int = MAX_RESULTS
    format: Optional[str] = "json"
    confidence_threshold: Optional[float] = CONFIDENCE_THRESHOLD  # Made configurable per request

class SearchResult(BaseModel):
    content: str
    page_title: str
    page_url: str
    score: float
    last_modified: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: str
    confidence_threshold: float = CONFIDENCE_THRESHOLD

def clean_html_content(content: str) -> str:
    """Clean HTML content and convert to plain text."""
    try:
        # Remove Confluence specific macros
        content = re.sub(r'<ac:.*?</ac:.*?>', ' ', content)
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        
        # Convert links to format: [text](url)
        for link in soup.find_all('a'):
            url = link.get('href', '')
            text = link.get_text()
            if url and text:
                link.replace_with(f"[{text}]({url})")
        
        # Get text and clean up whitespace
        text = soup.get_text()
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    except Exception as e:
        print(f"Error cleaning HTML: {str(e)}")
        return content

def format_slack_message(response: SearchResponse) -> Dict:
    """Format the response as a Slack message."""
    # Filter results based on confidence threshold
    valid_results = [r for r in response.results if r.score > response.confidence_threshold]
    
    if not valid_results:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ No relevant results found for: '{response.query}'\n\nTry rephrasing your question or be more specific."
                    }
                }
            ]
        }
    
    # Create blocks for the message
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔍 *Vector Knowledge Engine*\nQuery: '{response.query}'"
            }
        },
        {"type": "divider"}
    ]
    
    # Add each result as a section
    for result in valid_results:
        # Clean and format the content
        content = clean_html_content(result.content)
        
        # Truncate content if too long
        if len(content) > 300:
            content = content[:297] + "..."
            
        blocks.extend([
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{result.page_title}* (Score: {result.score:.2f})\n{content}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"<{result.page_url}|📄 View source>"
                    }
                ]
            },
            {"type": "divider"}
        ])
    
    return {
        "response_type": "in_channel",
        "blocks": blocks
    }

def format_teams_message(response: SearchResponse) -> Dict:
    """Format the response as a Teams message."""
    # Filter results based on confidence threshold
    valid_results = [r for r in response.results if r.score > response.confidence_threshold]
    
    if not valid_results:
        return {
            "type": "message",
            "text": f"❌ No relevant results found for: '{response.query}'\n\nTry rephrasing your question or be more specific."
        }
    
    # Create adaptive card format for Teams
    facts = []
    for result in valid_results:
        content = clean_html_content(result.content)
        if len(content) > 200:
            content = content[:197] + "..."
        
        facts.append({
            "title": f"{result.page_title} (Score: {result.score:.2f})",
            "value": content
        })
    
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Medium",
                            "weight": "Bolder",
                            "text": f"🔍 Vector Knowledge Engine"
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Query: '{response.query}'"
                        },
                        {
                            "type": "FactSet",
                            "facts": facts
                        }
                    ],
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.2"
                }
            }
        ]
    }

def preprocess_query(query: str) -> str:
    """Preprocess query for better search quality."""
    # Remove excessive whitespace and clean up
    query = re.sub(r'\s+', ' ', query.strip())
    
    # Expand common abbreviations and technical terms
    abbreviations = {
        'config': 'configuration',
        'setup': 'setup configuration installation',
        'install': 'installation setup configuration',
        'auth': 'authentication authorization',
        'db': 'database',
        'api': 'API application programming interface',
        'url': 'URL web address link',
        'ssl': 'SSL TLS security certificate',
        'cors': 'CORS cross origin resource sharing',
        'env': 'environment variables configuration'
    }
    
    # Simple keyword expansion
    words = query.lower().split()
    expanded_words = []
    for word in words:
        if word in abbreviations:
            expanded_words.extend(abbreviations[word].split())
        else:
            expanded_words.append(word)
    
    return ' '.join(expanded_words)

async def search(query: dict) -> dict:
    try:
        # Create SearchQuery from dict
        search_query = SearchQuery(**query)
        start_time = datetime.now()
        
        # Preprocess the query for better matching
        processed_query = preprocess_query(search_query.query)
        
        # Generate query embedding
        query_embedding = model.encode([processed_query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Normalize the query vector
        faiss.normalize_L2(query_embedding)
        
        # Search with more candidates to improve recall
        search_top_k = max(search_query.top_k * 2, 10)  # Search more, filter later
        scores, indices = index.search(query_embedding, search_top_k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(chunks):  # Ensure index is valid
                # Convert cosine similarity to a more intuitive score (0-1)
                normalized_score = (score + 1) / 2
                
                chunk = chunks[idx]
                results.append(SearchResult(
                    content=chunk['content'],
                    page_title=chunk['page_title'],
                    page_url=chunk['page_url'],
                    score=float(normalized_score),
                    last_modified=chunk.get('last_modified')
                ))
        
        # Filter by confidence threshold and limit results
        confident_results = [r for r in results if r.score >= search_query.confidence_threshold]
        final_results = confident_results[:search_query.top_k]
        
        # Create response
        response = SearchResponse(
            query=search_query.query,
            results=final_results,
            total_results=len(final_results),
            search_time=datetime.now().isoformat(),
            confidence_threshold=search_query.confidence_threshold
        )
        
        # Format response based on requested format
        if search_query.format == "slack":
            return format_slack_message(response)
        elif search_query.format == "teams":
            return format_teams_message(response)
        else:
            return response.model_dump()
    
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise Exception(str(e))

async def ask(text: str, user_id: str, channel_id: str, team_id: str) -> dict:
    """Handle /ask slash command from Slack."""
    try:
        # Create search query with configurable threshold
        query = SearchQuery(
            query=text, 
            confidence_threshold=CONFIDENCE_THRESHOLD
        )
        
        # Preprocess the query for better matching
        processed_query = preprocess_query(query.query)
        
        # Generate query embedding
        query_embedding = model.encode([processed_query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Normalize the query vector
        faiss.normalize_L2(query_embedding)
        
        # Search with more candidates to improve recall
        search_top_k = max(query.top_k * 2, 10)
        scores, indices = index.search(query_embedding, search_top_k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(chunks):  # Ensure index is valid
                # Convert cosine similarity to a more intuitive score (0-1)
                normalized_score = (score + 1) / 2
                
                chunk = chunks[idx]
                results.append(SearchResult(
                    content=chunk['content'],
                    page_title=chunk['page_title'],
                    page_url=chunk['page_url'],
                    score=float(normalized_score),
                    last_modified=chunk.get('last_modified')
                ))
        
        # Filter by confidence threshold and limit results
        confident_results = [r for r in results if r.score >= query.confidence_threshold]
        final_results = confident_results[:query.top_k]
        
        # Create response
        response = SearchResponse(
            query=query.query,
            results=final_results,
            total_results=len(final_results),
            search_time=datetime.now().isoformat(),
            confidence_threshold=query.confidence_threshold
        )
        
        return format_slack_message(response)
    
    except Exception as e:
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ Error processing your request: {str(e)}"
                    }
                }
            ]
        }

async def health_check() -> dict:
    # Load configuration info if available
    config_info = {}
    try:
        config_path = LOCAL_INDEX_DIR / 'index_config.json' if not os.getenv('STORAGE_CONNECTION_STRING') else None
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                config_info = json.load(f)
    except Exception:
        pass  # Ignore config loading errors
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "index_size": len(chunks),
        "model": MODEL_NAME,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_results": MAX_RESULTS,
        "index_config": config_info
    }
