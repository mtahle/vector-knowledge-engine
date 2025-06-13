import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from datetime import datetime

# Configuration
RAW_DATA_DIR = Path('../../data/raw')
INDEX_DIR = Path('../../data/index')
MODEL_NAME = 'all-MiniLM-L6-v2'

def load_raw_data() -> List[Dict]:
    """Load and analyze raw extracted data."""
    pages = []
    print("🔍 Loading raw data...")
    
    for file in RAW_DATA_DIR.glob('*.json'):
        with open(file, 'r', encoding='utf-8') as f:
            page = json.load(f)
            pages.append(page)
    
    print(f"📊 Found {len(pages)} pages in raw data")
    return pages

def analyze_raw_content(pages: List[Dict]):
    """Analyze the quality of raw extracted content."""
    print("\n📋 RAW CONTENT ANALYSIS")
    print("=" * 50)
    
    total_content_length = 0
    empty_pages = 0
    short_pages = 0
    
    for i, page in enumerate(pages[:5]):  # Show first 5 pages
        content = page.get('content', '')
        content_length = len(content)
        total_content_length += content_length
        
        if content_length == 0:
            empty_pages += 1
        elif content_length < 100:
            short_pages += 1
        
        print(f"\nPage {i+1}: {page.get('title', 'Unknown')}")
        print(f"  URL: {page.get('url', 'N/A')}")
        print(f"  Content length: {content_length} characters")
        print(f"  Content preview: {content[:200]}...")
        
        # Check for HTML remnants
        html_indicators = ['<div>', '<p>', '<span>', '&nbsp;', '&lt;', '&gt;']
        html_found = [indicator for indicator in html_indicators if indicator in content]
        if html_found:
            print(f"  ⚠️  HTML remnants found: {html_found}")
    
    avg_length = total_content_length / len(pages) if pages else 0
    print(f"\n📈 STATISTICS:")
    print(f"  Average content length: {avg_length:.0f} characters")
    print(f"  Empty pages: {empty_pages}")
    print(f"  Short pages (<100 chars): {short_pages}")

def load_chunks() -> List[Dict]:
    """Load processed chunks."""
    chunks_file = INDEX_DIR / 'chunks.json'
    if not chunks_file.exists():
        print("❌ Chunks file not found. Please run 'task build-index' first.")
        return []
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"\n🧩 Loaded {len(chunks)} chunks from index")
    return chunks

def analyze_chunks(chunks: List[Dict]):
    """Analyze chunk quality and distribution."""
    print("\n📋 CHUNK ANALYSIS")
    print("=" * 50)
    
    chunk_lengths = [len(chunk['content']) for chunk in chunks]
    avg_length = np.mean(chunk_lengths)
    min_length = min(chunk_lengths)
    max_length = max(chunk_lengths)
    
    print(f"📊 Chunk Statistics:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Average length: {avg_length:.0f} characters")
    print(f"  Min length: {min_length} characters")
    print(f"  Max length: {max_length} characters")
    
    # Show sample chunks
    print(f"\n🔍 Sample chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i+1} (from: {chunk['page_title']}):")
        print(f"  Length: {len(chunk['content'])} chars")
        print(f"  Content: {chunk['content'][:150]}...")

def test_search_with_known_content(chunks: List[Dict]):
    """Test search with content we know exists."""
    print("\n🔍 SEARCH TESTING")
    print("=" * 50)
    
    # Load model and index
    try:
        model = SentenceTransformer(MODEL_NAME)
        index_file = INDEX_DIR / 'vector.index'
        
        if not index_file.exists():
            print("❌ Vector index not found. Please run 'task build-index' first.")
            return
        
        index = faiss.read_index(str(index_file))
        print(f"✅ Loaded model and index (size: {index.ntotal})")
        
        # Extract some actual content for testing
        test_queries = []
        for chunk in chunks[:10]:  # Take first 10 chunks
            content = chunk['content']
            if len(content) > 50:
                # Create a query from part of the content
                words = content.split()[:10]  # First 10 words
                test_query = ' '.join(words)
                test_queries.append({
                    'query': test_query,
                    'expected_page': chunk['page_title'],
                    'expected_chunk_id': chunk['id']
                })
        
        print(f"\n🧪 Testing {len(test_queries)} queries...")
        
        successful_matches = 0
        for i, test in enumerate(test_queries[:3]):  # Test first 3
            query = test['query']
            expected_page = test['expected_page']
            
            print(f"\nTest {i+1}:")
            print(f"  Query: {query}")
            print(f"  Expected page: {expected_page}")
            
            # Generate query embedding
            query_embedding = model.encode([query])[0]
            query_embedding = np.array([query_embedding]).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = index.search(query_embedding, 5)
            
            print(f"  Top 5 results:")
            found_expected = False
            for j, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(chunks):
                    result_chunk = chunks[idx]
                    normalized_score = (score + 1) / 2
                    print(f"    {j+1}. Score: {normalized_score:.3f} | Page: {result_chunk['page_title']}")
                    
                    if result_chunk['page_title'] == expected_page:
                        found_expected = True
                        successful_matches += 1
            
            if not found_expected:
                print(f"    ❌ Expected page '{expected_page}' not found in top 5")
            else:
                print(f"    ✅ Found expected page")
        
        success_rate = successful_matches / len(test_queries[:3]) * 100
        print(f"\n📊 Success rate: {success_rate:.1f}% ({successful_matches}/{len(test_queries[:3])})")
        
    except Exception as e:
        print(f"❌ Error during search testing: {str(e)}")

def analyze_embedding_model():
    """Analyze the embedding model characteristics."""
    print("\n🤖 EMBEDDING MODEL ANALYSIS")
    print("=" * 50)
    
    try:
        model = SentenceTransformer(MODEL_NAME)
        
        # Test different types of content
        test_texts = [
            "How to configure Azure Functions",
            "Azure Functions configuration guide",
            "Setting up serverless functions in Azure",
            "Installation and setup procedures",
            "Technical documentation for developers"
        ]
        
        embeddings = model.encode(test_texts)
        
        print(f"Model: {MODEL_NAME}")
        print(f"Embedding dimension: {embeddings.shape[1]}")
        print(f"Embedding type: {embeddings.dtype}")
        
        # Calculate similarities between test texts
        print(f"\n🔗 Similarity matrix for test queries:")
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(embeddings)
        
        for i, text1 in enumerate(test_texts):
            print(f"\n  '{text1[:30]}...':")
            for j, text2 in enumerate(test_texts):
                if i != j:
                    print(f"    vs '{text2[:30]}...': {similarities[i][j]:.3f}")
        
    except Exception as e:
        print(f"❌ Error analyzing embedding model: {str(e)}")

def suggest_improvements():
    """Provide actionable suggestions for improvement."""
    print("\n💡 IMPROVEMENT SUGGESTIONS")
    print("=" * 50)
    
    suggestions = [
        "1. 📝 **Content Extraction**: Check if HTML is properly cleaned from Confluence",
        "2. 🧩 **Chunk Size**: Experiment with larger chunks (400-600 chars) for better context",
        "3. 🔄 **Chunk Overlap**: Increase overlap to 50-100 chars to preserve context",
        "4. 🎯 **Embedding Model**: Try domain-specific models like 'multi-qa-MiniLM-L6-cos-v1'",
        "5. 📊 **Confidence Threshold**: Lower the threshold from 0.7 to 0.5 or 0.3",
        "6. 🔍 **Query Preprocessing**: Add query expansion or synonyms",
        "7. 📚 **Content Quality**: Filter out very short chunks (<50 chars)",
        "8. 🎭 **Multiple Models**: Use ensemble of different embedding models",
        "9. 🔧 **Index Type**: Try IndexIVFFlat for better recall on large datasets",
        "10. 📈 **Evaluation**: Create a test set of known queries and expected results"
    ]
    
    for suggestion in suggestions:
        print(f"  {suggestion}")

def main():
    """Main diagnostic function."""
    print("🚀 VECTOR KNOWLEDGE ENGINE DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load and analyze data
    pages = load_raw_data()
    if pages:
        analyze_raw_content(pages)
    
    chunks = load_chunks()
    if chunks:
        analyze_chunks(chunks)
        test_search_with_known_content(chunks)
    
    analyze_embedding_model()
    suggest_improvements()
    
    print(f"\n✅ Diagnostic complete! Check the analysis above for issues.")

if __name__ == "__main__":
    main() 