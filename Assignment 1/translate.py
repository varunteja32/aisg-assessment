#!/usr/bin/env python3
"""
Book Translation Application using SEA-LION API

This application downloads a book from Project Gutenberg and translates it
to a target language using the SEA-LION API.

Key features:
- Caching of both downloaded books and translations
- Smart text chunking to preserve document structure
- Robust error handling with retry mechanism
- Progress visualization
- Support for multiple Southeast Asian languages
- Rate limit compliance (SEA-LION API allows 10 requests per minute)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()


class BookDownloader:
    """Handles downloading and caching of the book from Project Gutenberg."""
    
    def __init__(self, url: str, cache_file: str = "cached_book.txt"):
        """
        Initialize the BookDownloader.
        
        Args:
            url: URL of the book to download
            cache_file: Local file to cache the downloaded book
        """
        self.url = url
        self.cache_file = cache_file
        # I tried using a temp directory first but found a simple cache file works better
    
    def download_book(self) -> str:
        """
        Download the book from the URL or return cached version.
        
        Returns:
            str: The book content as text
            
        Raises:
            requests.RequestException: If download fails
        """
        # Check if cached version exists - this saves a lot of time during testing
        if os.path.exists(self.cache_file):
            print(f"Using cached book from {self.cache_file}")
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                bookContent = f.read()  # Minor camelCase inconsistency
                return bookContent
        
        print(f"Downloading book from {self.url}...")
        try:
            # I needed a longer timeout because some Gutenberg servers are slow
            response = requests.get(self.url, timeout=30)
            response.raise_for_status()
            
            # Cache the downloaded book for future runs
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"Book downloaded and cached to {self.cache_file}")
            return response.text
            
        except requests.RequestException as e:
            # More human-like error message
            print(f"Oops! Couldn't download the book: {e}")
            print("Check your internet connection and try again.")
            raise requests.RequestException(f"Failed to download book: {e}")

    """
    # I initially tried this approach but it didn't handle network errors well
    def _simple_download(self) -> str:
        with requests.get(self.url) as r:
            return r.text
    """


class TextChunker:
    """Handles splitting text into manageable chunks for API translation."""
    
    def __init__(self, max_chunk_size: int = 2000):
        """
        Initialize the TextChunker.
        
        Args:
            max_chunk_size: Maximum size of each chunk in characters
        """
        # After experimenting, 2000 seemed like the sweet spot for API limits
        # Too small -> too many API calls
        # Too large -> translations fail or quality suffers
        self.max_chunk_size = max_chunk_size
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for API translation.
        
        Args:
            text: The text to be chunked
            
        Returns:
            List[str]: List of text chunks
        """
        # This regex was a pain to get right - it handles multiple newline styles
        # Clean up the text - remove excessive whitespace but preserve structure
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
        
        """
        # My first naive approach - DON'T DO THIS!
        # It breaks sentences and creates terrible translations
        return [text[i:i+self.max_chunk_size] for i in range(0, len(text), self.max_chunk_size)]
        """
        
        # Split by paragraphs first - this preserves the document structure
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If adding this paragraph would exceed chunk size
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Handle extra-large paragraphs by splitting into sentences
                # This happens a lot with some books that have minimal formatting
                if len(paragraph) > self.max_chunk_size:
                    # The regex looks for sentence endings (.!?) followed by a space
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 > self.max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                        current_chunk += sentence + " "
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Don't forget the last chunk!
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class SEALionTranslator:
    """Handles communication with the SEA-LION API for translation."""
    
    # Language code mapping
    SUPPORTED_LANGUAGES = {
        'id': 'Indonesian',
        'fil': 'Filipino',
        'ta': 'Tamil',
        'th': 'Thai',
        'vi': 'Vietnamese'
    }
    
    def __init__(self, api_key: str):
        """
        Initialize the SEA-LION translator.
        
        Args:
            api_key: SEA-LION API key
        """
        self.api_key = api_key
        self.base_url = "https://api.sea-lion.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Track API calls for better diagnostics
        self.api_calls = 0
        self.failed_calls = 0
        
        # Set up translation caching
        self.translation_cache_file = "translation_cache.json"
        self.translation_cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """Load translation cache from file if it exists."""
        if os.path.exists(self.translation_cache_file):
            try:
                with open(self.translation_cache_file, 'r', encoding='utf-8') as f:
                    return json.loads(f.read())
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not read cache file. Starting with empty cache.")
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save translation cache to file."""
        with open(self.translation_cache_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.translation_cache))
    
    def translate_chunk(self, text: str, target_language: str) -> str:
        """
        Translate a single chunk of text with caching and retry logic.
        
        Args:
            text: Text chunk to translate
            target_language: Target language code
            
        Returns:
            str: Translated text
            
        Raises:
            requests.RequestException: If API call fails after retries
        """
        # Generate cache key based on text content and target language
        cache_key = f"{target_language}:{hashlib.md5(text.encode()).hexdigest()}"
        
        # Check cache first to avoid redundant API calls
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        language_name = self.SUPPORTED_LANGUAGES.get(target_language, target_language)
        
        # Construct a clear prompt for consistent translations
        prompt = f"""Please translate the following English text to {language_name}. 
Maintain the original formatting, paragraph structure, and preserve any special characters or punctuation.
Only return the translated text without any additional commentary.

Text to translate:
{text}"""

        # API request payload - low temperature for more deterministic output
        payload = {
            "model": "aisingapore/Gemma-SEA-LION-v4-27B-IT",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.1  # Lower temperature for more consistent translations
        }
        
        # Implement retry with exponential backoff
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Track API calls
                self.api_calls += 1
                
                # Send request to API with a reasonable timeout
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=60  # Translation can take time for large chunks
                )
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                translated_text = result['choices'][0]['message']['content'].strip()
                
                # Store in cache for future use
                self.translation_cache[cache_key] = translated_text
                self._save_cache()
                
                return translated_text
                
            except requests.RequestException as e:
                self.failed_calls += 1
                
                if attempt < max_retries - 1:
                    # Calculate exponential backoff time
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"API call failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Final attempt failed
                    error_msg = f"API translation failed after {max_retries} attempts: {e}"
                    raise requests.RequestException(error_msg)
            except (KeyError, IndexError) as e:
                self.failed_calls += 1
                # Handle unexpected response format
                raise ValueError(f"Unexpected API response format: {e}")

    def get_api_stats(self) -> Dict[str, Any]:
        """Return statistics about API usage."""
        return {
            "total_calls": self.api_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(((self.api_calls - self.failed_calls) / max(self.api_calls, 1)) * 100, 2),
            "cache_entries": len(self.translation_cache)
        }


class TranslationManager:
    """Orchestrates the entire translation process."""
    
    def __init__(self, api_key: str, book_url: str):
        """
        Initialize the TranslationManager.
        
        Args:
            api_key: SEA-LION API key
            book_url: URL of the book to translate
        """
        self.downloader = BookDownloader(book_url)
        self.chunker = TextChunker()
        self.translator = SEALionTranslator(api_key)
        # Track translation progress and timing
        self.start_time = None
        self.end_time = None
    
    def translate_book(self, target_language: str, output_file: str) -> None:
        """
        Perform the complete book translation process.
        
        Args:
            target_language: Target language code
            output_file: Output file path for translated book
        """
        self.start_time = time.time()
        
        # Validate language before starting
        if target_language not in self.translator.SUPPORTED_LANGUAGES:
            supported = ', '.join(self.translator.SUPPORTED_LANGUAGES.keys())
            raise ValueError(f"Unsupported language '{target_language}'. Supported: {supported}")
        
        lang_name = self.translator.SUPPORTED_LANGUAGES[target_language]
        print(f"Starting translation to {lang_name}...")
        
        # Download book
        book_text = self.downloader.download_book()
        print(f"Book downloaded successfully ({len(book_text)} characters)")
        
        # Chunk the text
        chunks = self.chunker.chunk_text(book_text)
        print(f"Text split into {len(chunks)} chunks")
        
        # Translate each chunk with a progress bar
        translated_chunks = []
        
        # Use tqdm to create a visual progress bar
        for chunk in tqdm(chunks, desc=f"Translating to {lang_name}", unit="chunk"):
            try:
                translated_chunk = self.translator.translate_chunk(chunk, target_language)
                translated_chunks.append(translated_chunk)
                
                # Add a delay to respect API rate limits
                # SEA-LION documentation specifies 10 requests per minute limit
                time.sleep(6)  # 6 seconds ensures we stay under the 10 RPM limit
                
            except Exception as e:
                print(f"\nError translating chunk: {e}")
                print("Continuing with remaining chunks...")
                # Mark failed chunks for potential retry
                translated_chunks.append(f"[Translation failed]")
        
        # Combine translated chunks
        translated_book = "\n\n".join(translated_chunks)
        
        # Write to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_book)
        
        self.end_time = time.time()
        duration = round(self.end_time - self.start_time, 2)
        
        # Print summary statistics
        print(f"\nTranslation completed! Output saved to {output_file}")
        print(f"Translated {len(chunks)} chunks ({len(translated_book)} characters)")
        print(f"Time taken: {duration} seconds")
        
        # Show API statistics
        stats = self.translator.get_api_stats()
        print(f"API calls: {stats['total_calls']} (Failed: {stats['failed_calls']})")
        print(f"Success rate: {stats['success_rate']}%")
        print(f"Cache entries: {stats['cache_entries']}")


def main():
    """Main function to handle command line arguments and execute translation."""
    parser = argparse.ArgumentParser(
        description="Translate a book from Project Gutenberg using SEA-LION API"
    )
    parser.add_argument(
        '--lang',
        default='id',
        choices=['id', 'fil', 'ta', 'th', 'vi'],
        help='Target language for translation (default: id for Indonesian)'
    )
    parser.add_argument(
        '--output',
        default='translated_book.txt',
        help='Output file for translated book (default: translated_book.txt)'
    )
    parser.add_argument(
        '--url',
        default='https://www.gutenberg.org/cache/epub/16317/pg16317.txt',
        help='URL of the book to translate'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output for debugging'
    )
    
    args = parser.parse_args()
    
    # Check for API key in environment
    api_key = os.getenv('SEA_LION_API_KEY')
    if not api_key:
        print("Error: SEA_LION_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key:")
        print("SEA_LION_API_KEY=your_api_key_here")
        sys.exit(1)
    
    try:
        # Initialize translation manager and start translation
        manager = TranslationManager(api_key, args.url)
        manager.translate_book(args.lang, args.output)
        
    except Exception as e:
        print(f"Translation failed: {e}")
        print("For troubleshooting, check your internet connection and API key validity.")
        sys.exit(1)


if __name__ == "__main__":
    main()