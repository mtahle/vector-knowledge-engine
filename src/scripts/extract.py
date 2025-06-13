import os
import json
from pathlib import Path
from datetime import datetime
from atlassian import Confluence
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
RAW_DATA_DIR = Path('data/raw')

def setup_confluence():
    """Initialize Confluence client."""
    base_url = os.getenv('CONFLUENCE_URL') or os.getenv('CONFLUENCE_BASE_URL')
    pat = os.getenv('CONFLUENCE_TOKEN') or os.getenv('CONFLUENCE_PAT')
    user = os.getenv('CONFLUENCE_USER')

    if not base_url or not pat or not user:
        raise ValueError("Missing Confluence credentials. Please check your .env file.")

    # Ensure the URL ends with /wiki
    if not base_url.endswith('/wiki'):
        base_url = f"{base_url}/wiki"

    print(f"Connecting to Confluence at: {base_url} as {user}")
    return Confluence(
        url=base_url,
        username=user,
        password=pat
    )

def extract_page_content(page_id, confluence):
    """Extract content from a Confluence page."""
    try:
        # Request both body.storage and version in the expand parameter
        page = confluence.get_page_by_id(page_id, expand='body.storage,version')
        print(f"Page data keys: {page.keys()}")
        
        if 'version' not in page:
            print(f"Page {page_id} does not have a version key. Skipping.")
            return None
            
        if 'body' not in page or 'storage' not in page['body']:
            print(f"Page {page_id} does not have body.storage. Skipping.")
            return None
            
        return {
            'id': page['id'],
            'title': page['title'],
            'url': f"{confluence.url}/pages/viewpage.action?pageId={page['id']}",
            'content': page['body']['storage']['value'],
            'last_modified': page['version']['when']
        }
    except Exception as e:
        print(f"Error extracting page {page_id}: {str(e)}")
        return None

def get_all_pages(confluence):
    """Get all pages from the configured space."""
    try:
        space_key = os.getenv('CONFLUENCE_SPACE')
        if not space_key:
            raise ValueError("CONFLUENCE_SPACE environment variable not set")
            
        print(f"Fetching pages from space: {space_key}")
        pages = confluence.get_all_pages_from_space(
            space=space_key,
            start=0,
            limit=1000,
            expand='version'
        )
        print(f"Found {len(pages)} pages in space {space_key}")
        return pages
    except Exception as e:
        print(f"Error fetching pages from space {space_key}: {str(e)}")
        raise

def save_page(page_data):
    """Save page data to JSON file."""
    if not page_data:
        print("No page data to save. Skipping.")
        return
    
    # Create directory if it doesn't exist
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON
    filename = f"{page_data['id']}.json"
    filepath = RAW_DATA_DIR / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        print(f"Saved page {page_data['id']} to {filepath}")
    except Exception as e:
        print(f"Error saving page {page_data['id']}: {str(e)}")

def main():
    """Main extraction process."""
    print("Starting Confluence content extraction...")
    
    try:
        # Initialize Confluence client
        confluence = setup_confluence()
        
        # Get all pages
        pages = get_all_pages(confluence)
        print(f"Found {len(pages)} pages to process")
        
        # Extract and save each page
        for page in pages:
            print(f"Processing page: {page['title']} (ID: {page['id']})")
            page_data = extract_page_content(page['id'], confluence)
            if page_data:
                save_page(page_data)
            else:
                print(f"Failed to extract page: {page['title']} (ID: {page['id']})")
        
        print("Extraction completed!")
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        raise

if __name__ == "__main__":
    main() 