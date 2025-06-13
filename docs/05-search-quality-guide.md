# Search Quality Improvement Guide

This guide helps you diagnose and improve search quality in your Vector Knowledge Engine when you're not finding content that you know exists.

## 🔍 Quick Diagnostic

**Step 1: Run the diagnostic tool**
```bash
task debug:search
```

This will analyze your:
- Raw extracted content quality
- Chunk processing effectiveness  
- Embedding model performance
- Search success rates

**Step 2: Check your current configuration**
```bash
curl https://your-function-app.azurewebsites.net/api/health
```

## 🧬 Common Issues & Solutions

### 1. **Poor Content Extraction**

**Symptoms:**
- Raw content contains HTML remnants (`<div>`, `&nbsp;`, etc.)
- Very short or empty content after extraction
- Missing critical information

**Solutions:**
```bash
# Use improved extraction (if available)
task extract:improved

# Or check your extraction script for HTML cleaning
# Look for BeautifulSoup or regex cleaning issues
```

### 2. **Suboptimal Chunking**

**Symptoms:**
- Very short chunks (<100 characters)
- Context loss between chunks
- Important content split awkwardly

**Solutions:**
```bash
# Use improved chunking strategy
task build-index:improved

# Or adjust chunking parameters
export CHUNK_SIZE=400
export CHUNK_OVERLAP=100
task build-index:improved
```

### 3. **Wrong Embedding Model**

**Symptoms:**
- Good content but poor search results
- Domain-specific queries failing
- General terms work better than specific ones

**Solutions:**
```bash
# Try Q&A optimized model (recommended)
task build-index:qa-model

# Try larger, higher-quality model (slower but better)
task build-index:large-model

# For multilingual content
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2 task build-index:improved
```

### 4. **Confidence Threshold Too High**

**Symptoms:**
- No results for queries you expect to work
- Very few results returned

**Solutions:**
```bash
# Lower the confidence threshold (Azure)
az functionapp config appsettings set \
  --name your-function-app \
  --resource-group your-resource-group \
  --settings CONFIDENCE_THRESHOLD=0.2

# Or test with specific threshold
curl -X POST https://your-function-app.azurewebsites.net/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your test query",
    "confidence_threshold": 0.2,
    "top_k": 10
  }'
```

### 5. **Query Preprocessing Issues**

**Symptoms:**
- Abbreviations or technical terms not matching
- Exact phrase matching fails
- Synonyms not recognized

**Current Improvements:**
- Automatic abbreviation expansion (config → configuration, auth → authentication, etc.)
- Query preprocessing and normalization
- Better text cleaning

**Custom Solutions:**
- Add domain-specific abbreviations to the preprocessing function
- Consider implementing query expansion with synonyms

## 🎯 Recommended Configuration

### **For General Knowledge Bases:**
```bash
export EMBEDDING_MODEL=multi-qa-MiniLM-L6-cos-v1
export CONFIDENCE_THRESHOLD=0.3
export CHUNK_SIZE=400
export CHUNK_OVERLAP=100
```

### **For Technical Documentation:**
```bash
export EMBEDDING_MODEL=all-mpnet-base-v2  # Higher quality
export CONFIDENCE_THRESHOLD=0.25
export CHUNK_SIZE=500
export CHUNK_OVERLAP=150
```

### **For Multilingual Content:**
```bash
export EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
export CONFIDENCE_THRESHOLD=0.3
export CHUNK_SIZE=400
export CHUNK_OVERLAP=100
```

## 📊 Model Comparison

| Model | Best For | Speed | Quality | Size |
|-------|----------|--------|---------|------|
| `all-MiniLM-L6-v2` | General purpose | Fast | Good | Small |
| `multi-qa-MiniLM-L6-cos-v1` | **Q&A Systems** | Fast | **Better for search** | Small |
| `all-mpnet-base-v2` | High quality needs | Slower | **Best** | Medium |
| `paraphrase-multilingual-*` | Multiple languages | Medium | Good | Medium |

**⭐ Recommended**: `multi-qa-MiniLM-L6-cos-v1` for most knowledge bases.

## 🔧 Step-by-Step Improvement Process

### Phase 1: Basic Improvements
```bash
# 1. Use improved index building
task build-index:improved

# 2. Lower confidence threshold
# Update your Azure Function App settings:
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings CONFIDENCE_THRESHOLD=0.3

# 3. Deploy updates
task func:deploy
```

### Phase 2: Model Optimization
```bash
# Try Q&A optimized model
task build-index:qa-model
task azure:upload-index
task func:deploy

# Test the improvement
curl -X POST https://your-function-app.azurewebsites.net/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query that was failing before"}'
```

### Phase 3: Advanced Optimization
```bash
# If still not satisfied, try larger model
task build-index:large-model
task azure:upload-index

# Fine-tune chunking for your content
export CHUNK_SIZE=500
export CHUNK_OVERLAP=150
task build-index:improved
```

## 🧪 Testing & Validation

### Create Test Queries
1. **Extract actual phrases** from your Confluence pages
2. **Test with different variations**:
   - Full phrases from content
   - Abbreviated versions
   - Question formats
   - Keyword combinations

### Example Test Script
```bash
# Test known content
curl -X POST https://your-function-app.azurewebsites.net/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Azure Functions configuration",
    "top_k": 10,
    "confidence_threshold": 0.2
  }' | jq '.results[] | {score: .score, title: .page_title}'
```

### Success Metrics
- **Recall**: Finding content you know exists
- **Precision**: Relevant results in top 5
- **Response Time**: Under 2 seconds for most queries
- **Confidence Scores**: Above 0.3 for good matches

## 🐛 Advanced Debugging

### Enable Detailed Logging
```bash
# Set debug logging
az functionapp config appsettings set \
  --name "$FUNCTION_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --settings LOG_LEVEL=DEBUG
```

### Analyze Search Patterns
```bash
# Run diagnostic with detailed output
task debug:search > search_analysis.txt

# Check for patterns:
# - HTML remnants in content
# - Very short chunks
# - Embedding model mismatches
# - Low similarity scores
```

### Manual Testing with Local Data
```bash
# Test locally with your data
cd src/scripts
python debug_search.py

# Compare different models
EMBEDDING_MODEL=all-MiniLM-L6-v2 python debug_search.py
EMBEDDING_MODEL=multi-qa-MiniLM-L6-cos-v1 python debug_search.py
```

## 📈 Performance Monitoring

### Key Metrics to Track
1. **Search Success Rate**: % of queries returning relevant results
2. **Average Confidence Score**: Should be >0.4 for good matches
3. **Query Response Time**: Should be <2 seconds
4. **Index Size vs. Quality**: Balance between coverage and precision

### Health Check Information
```bash
curl https://your-function-app.azurewebsites.net/api/health | jq
```

This returns:
- Current model being used
- Index size and configuration
- Confidence threshold settings
- Performance metrics

## 🎯 Quick Wins Checklist

- [ ] **Use Q&A optimized model**: `multi-qa-MiniLM-L6-cos-v1`
- [ ] **Lower confidence threshold**: 0.3 instead of 0.7
- [ ] **Improve chunking**: 400-character chunks with 100-character overlap
- [ ] **Better text cleaning**: Remove HTML remnants and normalize text
- [ ] **Query preprocessing**: Expand abbreviations and technical terms
- [ ] **Search more candidates**: Search 2x desired results, then filter
- [ ] **Test with actual queries**: Use real phrases from your content

## 🆘 Still Having Issues?

### Check These Common Problems:

1. **Empty or corrupted index files**
   ```bash
   # Rebuild from scratch
   task extract
   task build-index:improved
   task azure:upload-index
   ```

2. **Model mismatch between build and runtime**
   ```bash
   # Ensure same model in both places
   echo $EMBEDDING_MODEL  # Check build environment
   curl /api/health | jq .model  # Check runtime
   ```

3. **Azure Storage connection issues**
   ```bash
   # Verify storage access
   az storage blob list --container-name knowledge-base --account-name your-storage
   ```

4. **Insufficient content in chunks**
   ```bash
   # Check chunk quality
   task debug:search
   # Look for "very short chunks" warnings
   ```

### Getting Help

If you're still experiencing issues:

1. **Run the diagnostic**: `task debug:search`
2. **Check the health endpoint**: `/api/health`
3. **Test with low confidence threshold**: 0.1-0.2
4. **Try different embedding models**
5. **Verify your source content quality**

Remember: Vector search works best with **clean, well-structured content** and **domain-appropriate embedding models**. The Q&A optimized model with lower confidence threshold should significantly improve your results! 