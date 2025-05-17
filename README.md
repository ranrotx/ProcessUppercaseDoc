# Document Processing Tools

This repository contains Python scripts for processing and formatting documents using AWS Bedrock and Microsoft Word.

## Scripts

### 1. ProcessDoc.py

A script that processes Word documents using AWS Bedrock to improve text formatting and capitalization.

#### Features
- Processes Word documents to standardize capitalization
- Uses AWS Bedrock (Claude 3.7 Sonnet) for intelligent text processing
- Handles rate limiting and retries automatically
- Supports batch processing with parallel execution
- Can process entire documents or individual paragraphs
- Maintains original document structure and formatting

#### Requirements
- Python 3.x
- AWS credentials configured
- Required Python packages:
  - python-docx
  - boto3
  - tqdm

#### Usage
```bash
# Process entire document
python ProcessDoc.py input.docx -o output.txt

# Process specific paragraph
python ProcessDoc.py input.docx -p 5 -o output.txt
```

### 2. TextToWord.py

A script that converts text files into formatted Word documents.

#### Features
- Converts plain text files to professionally formatted Word documents
- Applies consistent formatting (font, spacing, margins)
- Automatically detects and formats potential headings
- Preserves paragraph structure
- Supports UTF-8 encoding

#### Requirements
- Python 3.x
- Required Python package:
  - python-docx

#### Usage
```bash
# Basic usage (outputs to input_filename.docx)
python TextToWord.py input.txt

# Specify custom output file
python TextToWord.py input.txt -o output.docx
```

## Installation

1. Clone this repository
2. Install required packages:
```bash
pip install python-docx boto3 tqdm
```

3. For ProcessDoc.py, ensure AWS credentials are configured:
   - Set up AWS CLI (`aws configure`)
   - Or set environment variables:
     - AWS_ACCESS_KEY_ID
     - AWS_SECRET_ACCESS_KEY
     - AWS_DEFAULT_REGION

## Example Workflow

1. Start with the Word doc that contains all uppercase text:
```bash
python ProcessDoc.py input.docx -o output.txt

```

2. Process the Word document for proper capitalization:
```bash
python TextToWord.py output.txt -o formatted.docx
```

## Error Handling

Both scripts include comprehensive error handling and logging:
- Input file validation
- AWS API error handling (for ProcessDoc.py)
- Detailed logging of operations and errors
- Graceful exit on critical errors

## License

This project is licensed under the MIT License - see the LICENSE file for details.
