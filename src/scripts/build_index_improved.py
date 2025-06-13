import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from tqdm import tqdm
import gc
import psutil
from bs4 import BeautifulSoup
import unicodedata

# Configuration
RAW_DATA_DIR = Path('../../data/raw')
INDEX_DIR = Path('../../data/index')

# Improved chunking parameters
CHUNK_SIZE = 400  # Increased for better context
CHUNK_OVERLAP = 100  # More overlap for context preservation
MIN_CHUNK_SIZE = 100  # Higher minimum for quality chunks
BATCH_SIZE = 10  # Slightly larger batches

# Model options - you can experiment with different models
EMBEDDING_MODELS = {
    'default': 'all-MiniLM-L6-v2',
    'qa-optimized': 'multi-qa-MiniLM-L6-cos-v1',  # Better for Q&A
    'large': 'all-mpnet-base-v2',  # Higher quality, slower
    'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2'  # For multiple languages
}

# Choose model (can be configured via environment variable)
MODEL_NAME = os.getenv('EMBEDDING_MODEL', EMBEDDING_MODELS['qa-optimized'])

def print_memory_usage(note=""):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024  # in MB
    print(f"[MEMORY] {note} RSS: {mem:.2f} MB")

def clean_text_advanced(text: str) -> str:
    """Advanced text cleaning for better quality."""
    if not text:
        return ""
    
    # Remove HTML entities and tags more thoroughly
    soup = BeautifulSoup(text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and clean it
    text = soup.get_text()
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove empty lines and excessive line breaks
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Remove special characters that might interfere
    text = re.sub(r'[^\w\s\.,;:!?\-()[\]{}""''`]', ' ', text)
    
    # Clean up spacing around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'([.,;:!?])\s+', r'\1 ', text)
    
    return text.strip()

def chunk_text_smart(text: str, page_title: str = "") -> List[str]:
    """Smart text chunking with sentence awareness."""
    if not text:
        return []
    
    # Split into sentences first
    sentence_endings = r'[.!?]+(?:\s|$)'
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # If adding this sentence would exceed chunk size
        if len(current_chunk) + len(sentence) > CHUNK_SIZE:
            if current_chunk:
                # Add the current chunk if it's substantial
                if len(current_chunk) >= MIN_CHUNK_SIZE:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                if len(sentence) > MIN_CHUNK_SIZE:
                    current_chunk = sentence
                else:
                    # Keep some context from previous chunk
                    overlap_text = current_chunk[-CHUNK_OVERLAP:] if len(current_chunk) > CHUNK_OVERLAP else current_chunk
                    current_chunk = overlap_text + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Add the last chunk
    if current_chunk and len(current_chunk) >= MIN_CHUNK_SIZE:
        chunks.append(current_chunk.strip())
    
    # If no good chunks were created, fall back to character-based chunking
    if not chunks and len(text) > MIN_CHUNK_SIZE:
        chunks = chunk_text_fallback(text)
    
    return chunks

def chunk_text_fallback(text: str) -> List[str]:
    """Fallback character-based chunking."""
    chunks = []
    text_length = len(text)
    step_size = CHUNK_SIZE - CHUNK_OVERLAP
    
    for start in range(0, text_length, step_size):
        end = min(start + CHUNK_SIZE, text_length)
        chunk = text[start:end]
        
        if len(chunk) >= MIN_CHUNK_SIZE:
            chunks.append(chunk)
        
        if end == text_length:
            break
    
    return chunks

def load_pages() -> List[Dict]:
    """Load JSON files from the raw data directory."""
    pages = []
    print_memory_usage("Before loading pages")
    
    if not RAW_DATA_DIR.exists():
        print(f"❌ Raw data directory {RAW_DATA_DIR} not found!")
        return []
    
    json_files = list(RAW_DATA_DIR.glob('*.json'))
    if not json_files:
        print(f"❌ No JSON files found in {RAW_DATA_DIR}")
        return []
    
    print(f"📁 Found {len(json_files)} JSON files")
    
    for file in json_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                page = json.load(f)
                
                # Validate page structure
                if not isinstance(page, dict):
                    print(f"⚠️  Skipping {file}: Not a valid JSON object")
                    continue
                
                required_fields = ['id', 'title', 'url', 'content']
                missing_fields = [field for field in required_fields if field not in page]
                if missing_fields:
                    print(f"⚠️  Skipping {file}: Missing fields {missing_fields}")
                    continue
                
                pages.append(page)
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing {file}: {e}")
            continue
        except Exception as e:
            print(f"❌ Error loading {file}: {e}")
            continue
    
    print(f"✅ Successfully loaded {len(pages)} pages")
    print_memory_usage("After loading pages")
    return pages

def prepare_chunks_enhanced(pages: List[Dict]) -> List[Dict]:
    """Enhanced chunk preparation with better text processing."""
    chunks = []
    print_memory_usage("Before preparing chunks")
    
    total_pages = len(pages)
    successful_pages = 0
    
    for page_idx, page in enumerate(pages):
        try:
            page_title = page.get('title', 'Unknown')
            page_url = page.get('url', '')
            page_id = page.get('id', f'page_{page_idx}')
            
            print(f"📄 Processing page {page_idx + 1}/{total_pages}: {page_title}")
            
            # Get and clean content
            raw_content = page.get('content', '')
            if not raw_content:
                print(f"⚠️  Page has no content, skipping")
                continue
            
            # Advanced cleaning
            clean_content = clean_text_advanced(raw_content)
            
            if len(clean_content) < MIN_CHUNK_SIZE:
                print(f"⚠️  Page content too short after cleaning ({len(clean_content)} chars), skipping")
                continue
            
            # Smart chunking
            content_chunks = chunk_text_smart(clean_content, page_title)
            
            if not content_chunks:
                print(f"⚠️  No valid chunks created from page")
                continue
            
            print(f"✅ Created {len(content_chunks)} chunks")
            
            # Create chunk objects with enhanced metadata
            for chunk_idx, chunk_content in enumerate(content_chunks):
                chunk_id = f"{page_id}_{chunk_idx}"
                
                chunk_obj = {
                    'id': chunk_id,
                    'page_id': page_id,
                    'page_title': page_title,
                    'page_url': page_url,
                    'chunk_index': chunk_idx,
                    'content': chunk_content,
                    'content_length': len(chunk_content),
                    'last_modified': page.get('last_modified', ''),
                    'source_type': page.get('source_type', 'confluence'),
                    'metadata': page.get('metadata', {})
                }
                
                chunks.append(chunk_obj)
            
            successful_pages += 1
            
            # Memory management
            if page_idx % 10 == 0:
                print_memory_usage(f"After processing {page_idx + 1} pages")
                gc.collect()
                
        except Exception as e:
            print(f"❌ Error processing page {page.get('title', 'Unknown')}: {e}")
            continue
    
    print(f"✅ Successfully processed {successful_pages}/{total_pages} pages")
    print(f"📊 Generated {len(chunks)} total chunks")
    print_memory_usage("After preparing chunks")
    
    return chunks

def build_index_enhanced(chunks: List[Dict]):
    """Enhanced index building with better error handling."""
    if not chunks:
        print("❌ No chunks to index!")
        return
    
    print_memory_usage("Before initializing model")
    
    try:
        # Initialize the sentence transformer model
        print(f"🤖 Loading model: {MODEL_NAME}")
        model = SentenceTransformer(MODEL_NAME)
        print(f"✅ Model loaded successfully")
        print_memory_usage("After initializing model")
        
        # Prepare for batch processing
        index = None
        all_embeddings = []
        processed_chunks = 0
        
        print(f"🔄 Processing {len(chunks)} chunks in batches of {BATCH_SIZE}")
        
        # Process chunks in batches
        for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Creating embeddings"):
            batch = chunks[i:i + BATCH_SIZE]
            texts = [chunk['content'] for chunk in batch]
            
            try:
                # Generate embeddings for the batch
                batch_embeddings = model.encode(
                    texts, 
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # L2 normalization
                )
                
                batch_embeddings = batch_embeddings.astype('float32')
                
                # Initialize index with first batch
                if index is None:
                    dimension = batch_embeddings.shape[1]
                    print(f"📏 Embedding dimension: {dimension}")
                    
                    # Use IndexFlatIP for better cosine similarity search
                    index = faiss.IndexFlatIP(dimension)
                    print(f"🔧 Created FAISS index: IndexFlatIP")
                
                # Add batch to index
                index.add(batch_embeddings)
                processed_chunks += len(batch)
                
                # Store embeddings for analysis if needed
                all_embeddings.append(batch_embeddings)
                
            except Exception as e:
                print(f"❌ Error processing batch {i//BATCH_SIZE + 1}: {e}")
                continue
            
            # Memory cleanup
            del batch_embeddings
            gc.collect()
            
            if i % (BATCH_SIZE * 10) == 0:
                print_memory_usage(f"After processing {processed_chunks} chunks")
        
        if index is None:
            print("❌ Failed to create index - no valid embeddings generated")
            return
        
        print(f"✅ Index created with {processed_chunks} chunks")
        
        # Save index and metadata
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_path = INDEX_DIR / 'vector.index'
        faiss.write_index(index, str(index_path))
        print(f"💾 Saved FAISS index to {index_path}")
        
        # Save chunk metadata with enhanced information
        chunks_with_stats = []
        for chunk in chunks[:processed_chunks]:  # Only include successfully processed chunks
            chunk_with_stats = chunk.copy()
            chunk_with_stats['index_model'] = MODEL_NAME
            chunk_with_stats['chunk_size_config'] = CHUNK_SIZE
            chunk_with_stats['overlap_config'] = CHUNK_OVERLAP
            chunks_with_stats.append(chunk_with_stats)
        
        chunks_path = INDEX_DIR / 'chunks.json'
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_with_stats, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved chunk metadata to {chunks_path}")
        
        # Save configuration for reference
        config = {
            'model_name': MODEL_NAME,
            'chunk_size': CHUNK_SIZE,
            'chunk_overlap': CHUNK_OVERLAP,
            'min_chunk_size': MIN_CHUNK_SIZE,
            'total_chunks': len(chunks_with_stats),
            'embedding_dimension': index.d,
            'index_type': 'IndexFlatIP'
        }
        
        config_path = INDEX_DIR / 'index_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"💾 Saved configuration to {config_path}")
        
        print(f"🎉 Index building completed successfully!")
        print(f"📊 Final stats: {len(chunks_with_stats)} chunks, {index.d}D embeddings")
        
    except Exception as e:
        print(f"❌ Error during index building: {e}")
        raise

def main():
    """Main process to build the enhanced index."""
    print("🚀 ENHANCED INDEX BUILDING")
    print("=" * 50)
    print(f"Model: {MODEL_NAME}")
    print(f"Chunk size: {CHUNK_SIZE} chars")
    print(f"Chunk overlap: {CHUNK_OVERLAP} chars")
    print(f"Min chunk size: {MIN_CHUNK_SIZE} chars")
    print("=" * 50)
    
    print_memory_usage("Start of main")
    
    try:
        # Load pages
        pages = load_pages()
        if not pages:
            print("❌ No pages found to process!")
            return
        
        # Prepare chunks with enhanced processing
        chunks = prepare_chunks_enhanced(pages)
        if not chunks:
            print("❌ No chunks created!")
            return
        
        # Build and save index
        build_index_enhanced(chunks)
        
        print("✅ Enhanced index build completed!")
        print("\n💡 Next steps:")
        print("1. Run 'task debug:search' to analyze the results")
        print("2. Test your search with 'task ask \"your question\"'")
        print("3. Deploy with 'task func:deploy'")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        raise
    finally:
        print_memory_usage("End of main")

if __name__ == "__main__":
    main() 