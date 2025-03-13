# OpenAI File Search Documentation

## Overview

File search is a tool available in OpenAI's Responses API that enables models to retrieve information from a knowledge base of previously uploaded files through semantic and keyword search. By creating vector stores and uploading files to them, you can augment the models' inherent knowledge by giving them access to these knowledge bases or `vector_stores`.

This is a hosted tool managed by OpenAI, meaning you don't have to implement code to handle its execution. When the model decides to use it, it will automatically call the tool, retrieve information from your files, and return an output.

## Implementation Steps

### 1. Upload Files to the File API

```python
import requests
from io import BytesIO
from openai import OpenAI

client = OpenAI()

def create_file(client, file_path):
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Download the file content from the URL
        response = requests.get(file_path)
        file_content = BytesIO(response.content)
        file_name = file_path.split("/")[-1]
        file_tuple = (file_name, file_content)
        result = client.files.create(
            file=file_tuple,
            purpose="assistants"
        )
    else:
        # Handle local file path
        with open(file_path, "rb") as file_content:
            result = client.files.create(
                file=file_content,
                purpose="assistants"
            )
    print(result.id)
    return result.id
```

### 2. Create a Vector Store

```python
vector_store = client.vector_stores.create(
    name="knowledge_base"
)
print(vector_store.id)
```

### 3. Add Files to the Vector Store

```python
client.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=file_id
)
```

### 4. Check File Processing Status

Run this code until the file status is `completed`:

```python
result = client.vector_stores.files.list(
    vector_store_id=vector_store.id
)
print(result)
```

### 5. Use the File Search Tool

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-4o-mini",
    input="What is deep research by OpenAI?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["<vector_store_id>"]
    }]
)
print(response)
```

The response will include:
1. A `file_search_call` output item with the ID of the file search call
2. A `message` output item with the model's response and file citations

## Retrieval Customization

### Limiting the Number of Results

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input="What is deep research by OpenAI?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["<vector_store_id>"],
        "max_num_results": 2
    }]
)
```

### Including Search Results in the Response

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input="What is deep research by OpenAI?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["<vector_store_id>"]
    }],
    include=["output[*].file_search_call.search_results"]
)
```

### Metadata Filtering

```python
response = client.responses.create(
    model="gpt-4o-mini",
    input="What is deep research by OpenAI?",
    tools=[{
        "type": "file_search",
        "vector_store_ids": ["<vector_store_id>"],
        "filters": {
            "type": "eq",
            "key": "type",
            "value": "blog"
        }
    }]
)
```

## Supported File Types

| File format | MIME type |
|-------------|-----------|
| .c          | text/x-c  |
| .cpp        | text/x-c++ |
| .cs         | text/x-csharp |
| .css        | text/css |
| .doc        | application/msword |
| .docx       | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| .go         | text/x-golang |
| .html       | text/html |
| .java       | text/x-java |
| .js         | text/javascript |
| .json       | application/json |
| .md         | text/markdown |
| .pdf        | application/pdf |
| .php        | text/x-php |
| .pptx       | application/vnd.openxmlformats-officedocument.presentationml.presentation |
| .py         | text/x-python |
| .py         | text/x-script.python |
| .rb         | text/x-ruby |
| .sh         | application/x-sh |
| .tex        | text/x-tex |
| .ts         | application/typescript |
| .txt        | text/plain |

## Limitations

- Projects are limited to a total size of 100GB for all Files
- Vector stores are limited to a total of 10k files
- Individual files can be a max of 512MB (roughly 5M tokens per file) 