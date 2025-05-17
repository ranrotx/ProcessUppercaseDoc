#!/usr/bin/env python
# coding: utf-8

from docx import Document
import os
import boto3
import json
import time
from botocore.config import Config
from botocore.exceptions import ClientError
from typing import List, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure boto3 client with retry settings
config = Config(
    retries = dict(
        max_attempts = 3,  # Maximum number of retry attempts
        mode = 'adaptive'  # Use adaptive retry mode
    ),
    connect_timeout = 5,  # Connection timeout in seconds
    read_timeout = 30,    # Read timeout in seconds
)

# Initialize the Bedrock client with custom config
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
    config=config
)

# Constants for rate limiting
RATE_LIMIT_DELAY = 1.0  # Base delay between API calls in seconds
MAX_RETRIES = 3         # Maximum number of retries for rate limiting
BATCH_SIZE = 5          # Number of chunks to process in parallel

class BedrockRateLimitError(Exception):
    """Custom exception for Bedrock rate limiting"""
    pass

def read_word_file(file_path: str) -> List[str]:
    """
    Read and parse a Word document
    
    Args:
        file_path (str): Path to the Word document
        
    Returns:
        List[str]: List containing paragraphs from the document
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: For other document processing errors
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist")
    
    try:
        doc = Document(file_path)
        document_content = [
            paragraph.text for paragraph in doc.paragraphs 
            if paragraph.text.strip()
        ]
        return document_content
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise

def process_chunk_with_bedrock(chunk: str, retry_count: int = 0) -> str:
    """
    Process a single chunk of text using Bedrock with retry logic
    
    Args:
        chunk (str): Text to process
        retry_count (int): Current retry attempt
        
    Returns:
        str: Processed text
        
    Raises:
        BedrockRateLimitError: If rate limit is hit and max retries exceeded
        Exception: For other API errors
    """
    prompt = f"""
    Please reformat the following text according to these rules:
    
    1. Convert to standard sentence case (First letter of sentences capitalized)
    2. Properly capitalize proper nouns, names, and titles
    3. Maintain appropriate capitalization for acronyms and initalisms
    4. Format dialogue and quotations correctly
    
    Important: Preserve all original formatting, spacing, and paragraph structure. 
    Only modify capitalization - do not change any words or punctuation. 
    Do not provide any additional commentary.
    
    Text to process: {chunk}
    
    Formatted text:
    """
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 0.9,
    }
    
    model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        # Handle rate limiting
        if error_code == 'ThrottlingException':
            if retry_count < MAX_RETRIES:
                # Exponential backoff
                delay = RATE_LIMIT_DELAY * (2 ** retry_count)
                logger.warning(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                return process_chunk_with_bedrock(chunk, retry_count + 1)
            else:
                raise BedrockRateLimitError("Max retries exceeded for rate limiting")
        
        # Handle other AWS errors
        logger.error(f"AWS Error: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

def process_batch(chunks: List[str], start_index: int) -> List[tuple[int, str]]:
    """
    Process a batch of chunks in parallel while maintaining order
    
    Args:
        chunks (List[str]): List of text chunks to process
        start_index (int): Starting index of this batch in the original document
        
    Returns:
        List[tuple[int, str]]: List of tuples containing (original_index, processed_text)
    """
    results = []
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        # Create a dictionary to map futures to their original indices
        future_to_index = {
            executor.submit(process_chunk_with_bedrock, chunk): i + start_index 
            for i, chunk in enumerate(chunks)
        }
        
        # Process futures as they complete
        for future in as_completed(future_to_index):
            original_index = future_to_index[future]
            try:
                result = future.result()
                results.append((original_index, result))
            except Exception as e:
                logger.error(f"Error processing chunk at index {original_index}: {str(e)}")
                results.append((original_index, None))  # Add None for failed chunks
    
    # Sort results by original index to maintain order
    results.sort(key=lambda x: x[0])
    return results

def process_document(file_path: str, output_file: str = None) -> None:
    """
    Process an entire document with progress tracking while maintaining paragraph order
    
    Args:
        file_path (str): Path to input document
        output_file (str, optional): Path to save processed document
    """
    try:
        # Read document
        content = read_word_file(file_path)
        logger.info(f"Processing document with {len(content)} paragraphs")
        
        # Process in batches with progress bar
        all_processed_chunks = []
        for i in tqdm(range(0, len(content), BATCH_SIZE), desc="Processing document"):
            batch = content[i:i + BATCH_SIZE]
            processed_batch = process_batch(batch, i)
            all_processed_chunks.extend(processed_batch)
            
            # Add delay between batches to prevent rate limiting
            time.sleep(RATE_LIMIT_DELAY)
        
        # Sort all chunks by their original index to ensure correct order
        all_processed_chunks.sort(key=lambda x: x[0])
        
        # Save results if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                for _, chunk in all_processed_chunks:
                    if chunk is not None:  # Skip failed chunks
                        f.write(chunk + '\n\n')
            logger.info(f"Results saved to {output_file}")
        else:
            # Print results in order
            for _, chunk in all_processed_chunks:
                if chunk is not None:  # Skip failed chunks
                    print(chunk)
                    print()  # Add spacing between chunks
                    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise

def process_single_paragraph(file_path: str, paragraph_number: int) -> str:
    """
    Process a single paragraph from the document by its number
    
    Args:
        file_path (str): Path to input document
        paragraph_number (int): 1-based index of the paragraph to process
        
    Returns:
        str: Processed paragraph text
        
    Raises:
        ValueError: If paragraph number is invalid
        FileNotFoundError: If the file doesn't exist
        Exception: For other processing errors
    """
    try:
        # Read document
        content = read_word_file(file_path)
        
        # Convert to 0-based index and validate
        index = paragraph_number - 1
        if index < 0 or index >= len(content):
            raise ValueError(
                f"Invalid paragraph number. Document has {len(content)} paragraphs. "
                f"Please provide a number between 1 and {len(content)}."
            )
        
        # Process the single paragraph
        logger.info(f"Processing paragraph {paragraph_number} of {len(content)}")
        processed_text = process_chunk_with_bedrock(content[index])
        
        return processed_text
        
    except Exception as e:
        logger.error(f"Error processing paragraph {paragraph_number}: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process Word document with AWS Bedrock')
    parser.add_argument('input_file', help='Path to input Word document')
    parser.add_argument('--output', '-o', help='Path to output file (optional)')
    parser.add_argument('--paragraph', '-p', type=int, 
                       help='Process only a specific paragraph number (1-based index)')
    
    args = parser.parse_args()
    
    try:
        if args.paragraph is not None:
            # Process single paragraph
            processed_text = process_single_paragraph(args.input_file, args.paragraph)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(processed_text + '\n')
                logger.info(f"Processed paragraph saved to {args.output}")
            else:
                print(processed_text)
        else:
            # Process entire document
            process_document(args.input_file, args.output)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        exit(1)


