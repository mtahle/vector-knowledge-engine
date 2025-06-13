import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm
import gc  # For garbage collection
import psutil  # For memory usage logging

# Configuration
RAW_DATA_DIR = Path('data/raw')
INDEX_DIR = Path('data/index')
CHUNK_SIZE = 200  # Reduced chunk size
CHUNK_OVERLAP = 20  # Reduced overlap
BATCH_SIZE = 5  # Smaller batch size

def print_memory_usage(note=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024  # in MB
    print(f"[MEMORY] {note} RSS: {mem:.2f} MB")

def load_pages() -> List[Dict]:
    """Load JSON files from the raw data directory."""
    pages = []
    print_memory_usage("Before loading pages")
    
    for file in RAW_DATA_DIR.glob('*.json'):
        print(f"Loading file: {file}")
        try:
            with open(file, 'r', encoding='utf-8') as f:
                page = json.load(f)
                # Print page size
                page_size = len(json.dumps(page)) / 1024  # in KB
                print(f"Page size: {page_size:.2f} KB")
                pages.append(page)
        except Exception as e:
            print(f"Error loading {file}: {str(e)}")
            continue
    
    print_memory_usage("After loading pages")
    return pages

def chunk_text(text: str) -> List[str]:
    """Split text into overlapping chunks."""
    if not text:
        return []
    
    print("Starting chunking process...")
    print(f"First 100 characters of content: {text[:100]}")
    
    chunks = []
    text_length = len(text)
    print(f"Total text length: {text_length}")
    
    try:
        # Calculate step size (chunk size minus overlap)
        step_size = CHUNK_SIZE - CHUNK_OVERLAP
        
        # Create chunks with proper overlap
        for start in range(0, text_length, step_size):
            end = min(start + CHUNK_SIZE, text_length)
            chunk = text[start:end]
            
            # Only add chunk if it's not empty and not too small
            if len(chunk) > 50:  # Minimum chunk size threshold
                chunks.append(chunk)
            
            if len(chunks) % 100 == 0:
                print(f"Created {len(chunks)} chunks so far...")
            
            # Break if we've reached the end
            if end == text_length:
                break
    
    except Exception as e:
        print(f"Error during chunking: {str(e)}")
        return []
    
    print(f"Finished chunking. Created {len(chunks)} chunks.")
    return chunks

def prepare_chunks(pages: List[Dict]) -> List[Dict]:
    """Prepare chunks from pages with metadata."""
    chunks = []
    print_memory_usage("Before preparing chunks")
    
    for page in pages:
        try:
            print(f"Processing page: {page.get('title', 'Unknown')}")
            
            # Get and validate content
            content = page.get('content', '')
            content_length = len(content)
            print(f"Content length: {content_length} characters")
            
            # Skip if content is too large
            if content_length > 1000000:  # 1MB limit
                print(f"Warning: Content too large ({content_length} chars), skipping page")
                continue
            
            # Split content into chunks
            content_chunks = chunk_text(content)
            print(f"Created {len(content_chunks)} chunks")
            
            # Create chunk objects with metadata
            for i, chunk in enumerate(content_chunks):
                chunks.append({
                    'id': f"{page['id']}_{i}",
                    'page_id': page['id'],
                    'page_title': page['title'],
                    'page_url': page['url'],
                    'chunk_index': i,
                    'content': chunk,
                    'last_modified': page['last_modified']
                })
                if i % 10 == 0:
                    print(f"Processed {i} chunks...")
                    print_memory_usage(f"After chunk {i}")
        except Exception as e:
            print(f"Error processing page {page.get('title', 'Unknown')}: {str(e)}")
            continue
    
    print_memory_usage("After preparing chunks")
    return chunks

def build_index(chunks: List[Dict]):
    """Build and save the FAISS index."""
    print_memory_usage("Before initializing model")
    
    # Initialize the sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print_memory_usage("After initializing model")
    
    # Create FAISS index (initialize after first batch to get dimension)
    index = None
    first_batch = True
    
    # Process chunks in batches and add to index incrementally
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Processing batches"):
        print_memory_usage(f"Before batch {i//BATCH_SIZE + 1}")
        
        batch = chunks[i:i + BATCH_SIZE]
        texts = [chunk['content'] for chunk in batch]
        
        # Generate embeddings for the batch
        batch_embeddings = model.encode(texts, show_progress_bar=False)
        batch_embeddings = np.array(batch_embeddings).astype('float32')
        
        # Initialize index with first batch
        if first_batch:
            dimension = batch_embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            first_batch = False
        
        # Add batch to index
        index.add(batch_embeddings)
        
        # Clear memory
        del batch_embeddings
        gc.collect()
        print_memory_usage(f"After batch {i//BATCH_SIZE + 1}")
    
    # Save index and metadata
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(index, str(INDEX_DIR / 'vector.index'))
    
    # Save chunk metadata
    with open(INDEX_DIR / 'chunks.json', 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print(f"Index built with {len(chunks)} chunks")
    print(f"Index saved to {INDEX_DIR}")

def main():
    """Main process to build the index."""
    print("Starting index build process...")
    print_memory_usage("Start of main")
    
    # Load pages
    pages = load_pages()
    print(f"Loaded {len(pages)} pages")
    
    # Prepare chunks
    chunks = prepare_chunks(pages)
    print(f"Created {len(chunks)} chunks")
    
    # Build and save index
    build_index(chunks)
    
    print("Index build completed!")
    print_memory_usage("End of main")

if __name__ == "__main__":
    main() 