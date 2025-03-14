Vector stores
Vector stores power semantic search for the Retrieval API and the file_search tool in the Responses and Assistants APIs.

Related guide: File Search

Create vector store
post
 
https://api.openai.com/v1/vector_stores
Create a vector store.

Request body
chunking_strategy
object

Optional
The chunking strategy used to chunk the file(s). If not set, will use the auto strategy. Only applicable if file_ids is non-empty.


Show possible types
expires_after
object

Optional
The expiration policy for a vector store.


Show properties
file_ids
array

Optional
A list of File IDs that the vector store should use. Useful for tools like file_search that can access files.

metadata
map

Optional
Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard.

Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters.

name
string

Optional
The name of the vector store.

Returns
A vector store object.

Example request
curl https://api.openai.com/v1/vector_stores \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "name": "Support FAQ"
  }'
Response
{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776,
  "name": "Support FAQ",
  "bytes": 139920,
  "file_counts": {
    "in_progress": 0,
    "completed": 3,
    "failed": 0,
    "cancelled": 0,
    "total": 3
  }
}
List vector stores
get
 
https://api.openai.com/v1/vector_stores
Returns a list of vector stores.

Query parameters
after
string

Optional
A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.

before
string

Optional
A cursor for use in pagination. before is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.

limit
integer

Optional
Defaults to 20
A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.

order
string

Optional
Defaults to desc
Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.

Returns
A list of vector store objects.

Example request
curl https://api.openai.com/v1/vector_stores \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "object": "list",
  "data": [
    {
      "id": "vs_abc123",
      "object": "vector_store",
      "created_at": 1699061776,
      "name": "Support FAQ",
      "bytes": 139920,
      "file_counts": {
        "in_progress": 0,
        "completed": 3,
        "failed": 0,
        "cancelled": 0,
        "total": 3
      }
    },
    {
      "id": "vs_abc456",
      "object": "vector_store",
      "created_at": 1699061776,
      "name": "Support FAQ v2",
      "bytes": 139920,
      "file_counts": {
        "in_progress": 0,
        "completed": 3,
        "failed": 0,
        "cancelled": 0,
        "total": 3
      }
    }
  ],
  "first_id": "vs_abc123",
  "last_id": "vs_abc456",
  "has_more": false
}
Retrieve vector store
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}
Retrieves a vector store.

Path parameters
vector_store_id
string

Required
The ID of the vector store to retrieve.

Returns
The vector store object matching the specified ID.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776
}
Modify vector store
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}
Modifies a vector store.

Path parameters
vector_store_id
string

Required
The ID of the vector store to modify.

Request body
expires_after
object or null

Optional
The expiration policy for a vector store.


Show properties
metadata
map

Optional
Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard.

Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters.

name
string or null

Optional
The name of the vector store.

Returns
The modified vector store object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
  -d '{
    "name": "Support FAQ"
  }'
Response
{
  "id": "vs_abc123",
  "object": "vector_store",
  "created_at": 1699061776,
  "name": "Support FAQ",
  "bytes": 139920,
  "file_counts": {
    "in_progress": 0,
    "completed": 3,
    "failed": 0,
    "cancelled": 0,
    "total": 3
  }
}
Delete vector store
delete
 
https://api.openai.com/v1/vector_stores/{vector_store_id}
Delete a vector store.

Path parameters
vector_store_id
string

Required
The ID of the vector store to delete.

Returns
Deletion status

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -X DELETE
Response
{
  id: "vs_abc123",
  object: "vector_store.deleted",
  deleted: true
}
Search vector store
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/search
Search a vector store for relevant chunks based on a query and file attributes filter.

Path parameters
vector_store_id
string

Required
The ID of the vector store to search.

Request body
query
string or array

Required
A query string for a search

filters
object

Optional
A filter to apply based on file attributes.


Show possible types
max_num_results
integer

Optional
Defaults to 10
The maximum number of results to return. This number should be between 1 and 50 inclusive.

ranking_options
object

Optional
Ranking options for search.


Show properties
rewrite_query
boolean

Optional
Defaults to false
Whether to rewrite the natural language query for vector search.

Returns
A page of search results from the vector store.

Example request
curl -X POST \
https://api.openai.com/v1/vector_stores/vs_abc123/search \
-H "Authorization: Bearer $OPENAI_API_KEY" \
-H "Content-Type: application/json" \
-d '{"query": "What is the return policy?", "filters": {...}}'
Response
{
  "object": "vector_store.search_results.page",
  "search_query": "What is the return policy?",
  "data": [
    {
      "file_id": "file_123",
      "filename": "document.pdf",
      "score": 0.95,
      "attributes": {
        "author": "John Doe",
        "date": "2023-01-01"
      },
      "content": [
        {
          "type": "text",
          "text": "Relevant chunk"
        }
      ]
    },
    {
      "file_id": "file_456",
      "filename": "notes.txt",
      "score": 0.89,
      "attributes": {
        "author": "Jane Smith",
        "date": "2023-01-02"
      },
      "content": [
        {
          "type": "text",
          "text": "Sample text content from the vector store."
        }
      ]
    }
  ],
  "has_more": false,
  "next_page": null
}
The vector store object
A vector store is a collection of processed files can be used by the file_search tool.

created_at
integer

The Unix timestamp (in seconds) for when the vector store was created.

expires_after
object

The expiration policy for a vector store.


Show properties
expires_at
integer or null

The Unix timestamp (in seconds) for when the vector store will expire.

file_counts
object


Show properties
id
string

The identifier, which can be referenced in API endpoints.

last_active_at
integer or null

The Unix timestamp (in seconds) for when the vector store was last active.

metadata
map

Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard.

Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters.

name
string

The name of the vector store.

object
string

The object type, which is always vector_store.

status
string

The status of the vector store, which can be either expired, in_progress, or completed. A status of completed indicates that the vector store is ready for use.

usage_bytes
integer

The total number of bytes used by the files in the vector store.

OBJECT The vector store object
{
  "id": "vs_123",
  "object": "vector_store",
  "created_at": 1698107661,
  "usage_bytes": 123456,
  "last_active_at": 1698107661,
  "name": "my_vector_store",
  "status": "completed",
  "file_counts": {
    "in_progress": 0,
    "completed": 100,
    "cancelled": 0,
    "failed": 0,
    "total": 100
  },
  "last_used_at": 1698107661
}
Vector store files
Vector store files represent files inside a vector store.

Related guide: File Search

Create vector store file
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files
Create a vector store file by attaching a File to a vector store.

Path parameters
vector_store_id
string

Required
The ID of the vector store for which to create a File.

Request body
file_id
string

Required
A File ID that the vector store should use. Useful for tools like file_search that can access files.

attributes
map

Optional
Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters, booleans, or numbers.

chunking_strategy
object

Optional
The chunking strategy used to chunk the file(s). If not set, will use the auto strategy.


Show possible types
Returns
A vector store file object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -H "OpenAI-Beta: assistants=v2" \
    -d '{
      "file_id": "file-abc123"
    }'
Response
{
  "id": "file-abc123",
  "object": "vector_store.file",
  "created_at": 1699061776,
  "usage_bytes": 1234,
  "vector_store_id": "vs_abcd",
  "status": "completed",
  "last_error": null
}
List vector store files
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files
Returns a list of vector store files.

Path parameters
vector_store_id
string

Required
The ID of the vector store that the files belong to.

Query parameters
after
string

Optional
A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.

before
string

Optional
A cursor for use in pagination. before is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.

filter
string

Optional
Filter by file status. One of in_progress, completed, failed, cancelled.

limit
integer

Optional
Defaults to 20
A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.

order
string

Optional
Defaults to desc
Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.

Returns
A list of vector store file objects.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "object": "list",
  "data": [
    {
      "id": "file-abc123",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    },
    {
      "id": "file-abc456",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    }
  ],
  "first_id": "file-abc123",
  "last_id": "file-abc456",
  "has_more": false
}
Retrieve vector store file
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}
Retrieves a vector store file.

Path parameters
file_id
string

Required
The ID of the file being retrieved.

vector_store_id
string

Required
The ID of the vector store that the file belongs to.

Returns
The vector store file object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files/file-abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "id": "file-abc123",
  "object": "vector_store.file",
  "created_at": 1699061776,
  "vector_store_id": "vs_abcd",
  "status": "completed",
  "last_error": null
}
Retrieve vector store file content
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}/content
Retrieve the parsed contents of a vector store file.

Path parameters
file_id
string

Required
The ID of the file within the vector store.

vector_store_id
string

Required
The ID of the vector store.

Returns
The parsed contents of the specified vector store file.

Example request
curl \
https://api.openai.com/v1/vector_stores/vs_abc123/files/file-abc123/content \
-H "Authorization: Bearer $OPENAI_API_KEY"
Response
{
  "file_id": "file-abc123",
  "filename": "example.txt",
  "attributes": {"key": "value"},
  "content": [
    {"type": "text", "text": "..."},
    ...
  ]
}
Update vector store file attributes
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}
Update attributes on a vector store file.

Path parameters
file_id
string

Required
The ID of the file to update attributes.

vector_store_id
string

Required
The ID of the vector store the file belongs to.

Request body
attributes
map

Required
Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters, booleans, or numbers.

Returns
The updated vector store file object.

Example request
curl https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id} \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"attributes": {"key1": "value1", "key2": 2}}'
Response
{
  "id": "file-abc123",
  "object": "vector_store.file",
  "usage_bytes": 1234,
  "created_at": 1699061776,
  "vector_store_id": "vs_abcd",
  "status": "completed",
  "last_error": null,
  "chunking_strategy": {...},
  "attributes": {"key1": "value1", "key2": 2}
}
Delete vector store file
delete
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/files/{file_id}
Delete a vector store file. This will remove the file from the vector store but the file itself will not be deleted. To delete the file, use the delete file endpoint.

Path parameters
file_id
string

Required
The ID of the file to delete.

vector_store_id
string

Required
The ID of the vector store that the file belongs to.

Returns
Deletion status

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files/file-abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -X DELETE
Response
{
  id: "file-abc123",
  object: "vector_store.file.deleted",
  deleted: true
}
The vector store file object
Beta
A list of files attached to a vector store.

attributes
map

Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters, booleans, or numbers.

chunking_strategy
object

The strategy used to chunk the file.


Show possible types
created_at
integer

The Unix timestamp (in seconds) for when the vector store file was created.

id
string

The identifier, which can be referenced in API endpoints.

last_error
object or null

The last error associated with this vector store file. Will be null if there are no errors.


Show properties
object
string

The object type, which is always vector_store.file.

status
string

The status of the vector store file, which can be either in_progress, completed, cancelled, or failed. The status completed indicates that the vector store file is ready for use.

usage_bytes
integer

The total vector store usage in bytes. Note that this may be different from the original file size.

vector_store_id
string

The ID of the vector store that the File is attached to.

OBJECT The vector store file object
{
  "id": "file-abc123",
  "object": "vector_store.file",
  "usage_bytes": 1234,
  "created_at": 1698107661,
  "vector_store_id": "vs_abc123",
  "status": "completed",
  "last_error": null,
  "chunking_strategy": {
    "type": "static",
    "static": {
      "max_chunk_size_tokens": 800,
      "chunk_overlap_tokens": 400
    }
  }
}
Vector store file batches
Vector store file batches represent operations to add multiple files to a vector store. Related guide: File Search

Create vector store file batch
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches
Create a vector store file batch.

Path parameters
vector_store_id
string

Required
The ID of the vector store for which to create a File Batch.

Request body
file_ids
array

Required
A list of File IDs that the vector store should use. Useful for tools like file_search that can access files.

attributes
map

Optional
Set of 16 key-value pairs that can be attached to an object. This can be useful for storing additional information about the object in a structured format, and querying for objects via API or the dashboard. Keys are strings with a maximum length of 64 characters. Values are strings with a maximum length of 512 characters, booleans, or numbers.

chunking_strategy
object

Optional
The chunking strategy used to chunk the file(s). If not set, will use the auto strategy.


Show possible types
Returns
A vector store file batch object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/file_batches \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json \
    -H "OpenAI-Beta: assistants=v2" \
    -d '{
      "file_ids": ["file-abc123", "file-abc456"]
    }'
Response
{
  "id": "vsfb_abc123",
  "object": "vector_store.file_batch",
  "created_at": 1699061776,
  "vector_store_id": "vs_abc123",
  "status": "in_progress",
  "file_counts": {
    "in_progress": 1,
    "completed": 1,
    "failed": 0,
    "cancelled": 0,
    "total": 0,
  }
}
Retrieve vector store file batch
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}
Retrieves a vector store file batch.

Path parameters
batch_id
string

Required
The ID of the file batch being retrieved.

vector_store_id
string

Required
The ID of the vector store that the file batch belongs to.

Returns
The vector store file batch object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files_batches/vsfb_abc123 \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "id": "vsfb_abc123",
  "object": "vector_store.file_batch",
  "created_at": 1699061776,
  "vector_store_id": "vs_abc123",
  "status": "in_progress",
  "file_counts": {
    "in_progress": 1,
    "completed": 1,
    "failed": 0,
    "cancelled": 0,
    "total": 0,
  }
}
Cancel vector store file batch
post
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel
Cancel a vector store file batch. This attempts to cancel the processing of files in this batch as soon as possible.

Path parameters
batch_id
string

Required
The ID of the file batch to cancel.

vector_store_id
string

Required
The ID of the vector store that the file batch belongs to.

Returns
The modified vector store file batch object.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files_batches/vsfb_abc123/cancel \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -X POST
Response
{
  "id": "vsfb_abc123",
  "object": "vector_store.file_batch",
  "created_at": 1699061776,
  "vector_store_id": "vs_abc123",
  "status": "in_progress",
  "file_counts": {
    "in_progress": 12,
    "completed": 3,
    "failed": 0,
    "cancelled": 0,
    "total": 15,
  }
}
List vector store files in a batch
get
 
https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}/files
Returns a list of vector store files in a batch.

Path parameters
batch_id
string

Required
The ID of the file batch that the files belong to.

vector_store_id
string

Required
The ID of the vector store that the files belong to.

Query parameters
after
string

Optional
A cursor for use in pagination. after is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with obj_foo, your subsequent call can include after=obj_foo in order to fetch the next page of the list.

before
string

Optional
A cursor for use in pagination. before is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with obj_foo, your subsequent call can include before=obj_foo in order to fetch the previous page of the list.

filter
string

Optional
Filter by file status. One of in_progress, completed, failed, cancelled.

limit
integer

Optional
Defaults to 20
A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 20.

order
string

Optional
Defaults to desc
Sort order by the created_at timestamp of the objects. asc for ascending order and desc for descending order.

Returns
A list of vector store file objects.

Example request
curl https://api.openai.com/v1/vector_stores/vs_abc123/files_batches/vsfb_abc123/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
Response
{
  "object": "list",
  "data": [
    {
      "id": "file-abc123",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    },
    {
      "id": "file-abc456",
      "object": "vector_store.file",
      "created_at": 1699061776,
      "vector_store_id": "vs_abc123"
    }
  ],
  "first_id": "file-abc123",
  "last_id": "file-abc456",
  "has_more": false
}
The vector store files batch object
Beta
A batch of files attached to a vector store.

created_at
integer

The Unix timestamp (in seconds) for when the vector store files batch was created.

file_counts
object


Show properties
id
string

The identifier, which can be referenced in API endpoints.

object
string

The object type, which is always vector_store.file_batch.

status
string

The status of the vector store files batch, which can be either in_progress, completed, cancelled or failed.

vector_store_id
string

The ID of the vector store that the File is attached to.