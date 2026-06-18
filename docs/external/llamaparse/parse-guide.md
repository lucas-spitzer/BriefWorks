---
title: REST API Guide | Developer Documentation
description: Parse REST API endpoints, request/response shapes, expand values, and presigned URL patterns.
---

**For the complete SDK and API documentation, see the [Parse API Reference →](https://developers.llamaindex.ai/reference/resources/parsing/methods/create)**

This page covers REST API usage patterns: endpoint overview, request examples, response shapes, and the `expand` parameter quick-reference.

## Endpoints

| Method                       | URL                                        | Use case |
| ---------------------------- | ------------------------------------------ | -------- |
| `POST /api/v2/parse`         | Parse a file by ID or URL (JSON body)      |          |
| `GET /api/v2/parse`          | List and filter parse jobs with pagination |          |
| `GET /api/v2/parse/{job_id}` | Check job status and retrieve results      |          |

**Required header:** `Authorization: Bearer YOUR_API_KEY` on all endpoints.

### Creating a parse job

Send a JSON body with `file_id` (or `source_url`), `tier`, `version`, and any options:

Terminal window

```
curl -X POST 'https://api.cloud.llamaindex.ai/api/v2/parse' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LLAMA_CLOUD_API_KEY" \
  --data '{
    "file_id": "<file_id>",
    "tier": "agentic",
    "version": "latest"
  }'
```

The response includes a `job.id`. Use it to retrieve results with the `expand` query parameter (see [Retrieving results](#retrieving-results) below). See [Configuring Parse](/llamaparse/parse/guides/configuring-parse/index.md) for every available option.

---

## Listing jobs

Terminal window

```
curl 'https://api.cloud.llamaindex.ai/api/v2/parse?page_size=10&status=COMPLETED' \
  -H "Authorization: Bearer $LLAMA_CLOUD_API_KEY"
```

**Query parameters:**

| Parameter    | Type    | Description                                                      |
| ------------ | ------- | ---------------------------------------------------------------- |
| `page_size`  | integer | Max items per page (optional)                                    |
| `page_token` | string  | Token for the next page (from a previous response)               |
| `status`     | string  | Filter: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |

**Response:**

```
{
  "items": [
    {
      "id": "job-uuid-1",
      "project_id": "project-uuid",
      "status": "COMPLETED",
      "error_message": null
    }
  ],
  "next_page_token": "eyJsYXN0X2lkIjogImpvYi...",
  "total_size": 42
}
```

---

## Retrieving results

Terminal window

```
curl 'https://api.cloud.llamaindex.ai/api/v2/parse/{job_id}?expand=markdown,items,metadata' \
  -H "Authorization: Bearer $LLAMA_CLOUD_API_KEY"
```

The response always includes a `job` object with `id`, `project_id`, `status`, and `error_message`. Additional fields depend on the `expand` parameter.

### Expand values

| Value                            | What it returns                                                        |
| -------------------------------- | ---------------------------------------------------------------------- |
| `text`                           | Plain text per page                                                    |
| `markdown`                       | Markdown per page                                                      |
| `items`                          | Structured JSON items (tables, headings, paragraphs per page)          |
| `metadata`                       | Page-level metadata (confidence, speaker notes, cost\_optimized, etc.) |
| `job_metadata`                   | Usage and processing details                                           |
| `text_full`                      | Full plain text as a single string (all pages concatenated)            |
| `markdown_full`                  | Full markdown as a single string (all pages concatenated)              |
| `text_content_metadata`          | Text file presigned download URL                                       |
| `markdown_content_metadata`      | Markdown file presigned download URL                                   |
| `items_content_metadata`         | Items file presigned download URL                                      |
| `metadata_content_metadata`      | Metadata file presigned download URL                                   |
| `text_full_content_metadata`     | Full text file presigned download URL                                  |
| `markdown_full_content_metadata` | Full markdown file presigned download URL                              |
| `xlsx_content_metadata`          | XLSX file presigned download URL                                       |
| `output_pdf_content_metadata`    | Output PDF presigned download URL                                      |
| `images_content_metadata`        | Images metadata with per-image presigned URLs                          |

Combine multiple values: `?expand=markdown,items,images_content_metadata`

For detailed guidance on choosing expand values, see [Retrieving Results](/llamaparse/parse/guides/retrieving-results/index.md).

### Content metadata response shapes

When requesting `*_content_metadata` expand values, the response includes presigned URLs for direct download:

**XLSX and PDF:**

```
{
  "result_content_metadata": {
    "xlsx": {
      "size_bytes": 15234,
      "exists": true,
      "presigned_url": "https://s3.amazonaws.com/..."
    },
    "outputPDF": {
      "size_bytes": 102400,
      "exists": true,
      "presigned_url": "https://s3.amazonaws.com/..."
    }
  }
}
```

**Images:**

```
{
  "images_content_metadata": {
    "total_count": 3,
    "images": [
      {
        "index": 0,
        "filename": "image_0.png",
        "content_type": "image/png",
        "size_bytes": 12345,
        "presigned_url": "https://s3.amazonaws.com/..."
      }
    ]
  }
}
```

You can filter images with the `image_filenames` query parameter:

Terminal window

```
curl 'https://api.cloud.llamaindex.ai/api/v2/parse/{job_id}?expand=images_content_metadata&image_filenames=image_0.png,image_1.jpg' \
  -H "Authorization: Bearer $LLAMA_CLOUD_API_KEY"
```

> **Presigned URLs are temporary.** Download files promptly after retrieving them, or call the endpoint again for fresh URLs.

---

## Error responses

v2 returns structured validation errors:

```
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["tier"],
      "msg": "Unsupported tier: invalid_tier. Must be one of: fast, cost_effective, agentic, agentic_plus",
      "input": {}
    }
  ]
}
```

---

## See also

- [Configuring Parse](/llamaparse/parse/guides/configuring-parse/index.md) — every option explained with examples
- [Retrieving Results](/llamaparse/parse/guides/retrieving-results/index.md) — detailed `expand` guidance and common patterns
- [Migration Guide: v1 to v2](/llamaparse/parse/guides/migration-v1-to-v2/index.md) — parameter mapping for v1 users
- [Tiers](/llamaparse/parse/guides/tiers/index.md) — tier comparison and version pinning
- [Parse API Reference](https://developers.llamaindex.ai/reference/resources/parsing/methods/create) — complete SDK and API documentation
