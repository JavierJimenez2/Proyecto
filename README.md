# SAR Web Searcher Project

## Overview

This project is part of the SAR (Storage and Information Retrieval Systems) coursework. It implements a **web search system** in Python, focusing on crawling, indexing, and retrieving information from Spanish Wikipedia articles.

The project consists of three main components:
1. **Crawler**: Gathers and stores Wikipedia articles.
2. **Indexer**: Processes the articles and creates an inverted index for fast retrieval.
3. **Searcher**: Retrieves articles based on user queries.

## Repository Structure

```plaintext
SAR_Web_Searcher/
├── SAR_Crawler.py           # Main crawler program
├── SAR_Crawler_lib.py       # Crawler library (customized)
├── SAR_Indexer.py           # Main indexer program
├── SAR_lib.py               # Indexer and searcher library (customized)
├── SAR_Searcher.py          # Main searcher program
├── test_queries.txt         # Test file with queries
├── queries.txt              # Example queries
├── results/                 # Output directory for results
├── Memoria/                 # Documentation for the project
├── .gitignore               # Git ignore file
```

## Features

### Core Functionality
1. **Crawling**:
   - Extracts content from Wikipedia pages, starting from a URL or a predefined list.
   - Stores data in JSON format, structured with fields like `title`, `summary`, and `sections`.

2. **Indexing**:
   - Processes JSON files to create an inverted index.
   - Supports tokenization and normalization of article content.
   - Generates a unique ID for each article.

3. **Searching**:
   - Performs boolean queries (`AND`, `OR`, `NOT`) on indexed data.
   - Supports interactive querying and file-based query evaluation.

### Extended Functionality
- **Parentheses**: Advanced query parsing using logical operators with precedence.
- **Stemming**: Adds support for stemmed queries.
- **Multifield**: Enables searching in specific fields (e.g., `title`, `summary`).
- **Positional Queries**: Retrieves results for consecutive terms within quotes.
- **Permuterm Indexing**: Supports wildcard queries (`*`, `?`).

## Requirements

- Python 3.9+
- Libraries: `re`, `argparse`, `heapq`, and others included in Python's standard library.

## Setup and Usage

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd SAR_Web_Searcher
   ```

2. Run the crawler:
   ```bash
   python SAR_Crawler.py --initial-url <URL> --out-base-filename output.json
   ```

3. Index the crawled data:
   ```bash
   python SAR_Indexer.py <input-directory> <output-index>
   ```

4. Perform searches:
   ```bash
   python SAR_Searcher.py <index-file> -Q "query"
   ```

## Testing

Use `test_queries.txt` to evaluate the functionality:
```bash
python SAR_Searcher.py <index-file> -T test_queries.txt
```

## Contribution

The project was developed collaboratively. All members contributed to the design and implementation of crawling, indexing, and retrieval functionalities.

For detailed contributions and explanations, refer to the **Memoria.pdf** file in the `Memoria` directory.

## License

This project is developed for educational purposes as part of the SAR course (2023-2024).
