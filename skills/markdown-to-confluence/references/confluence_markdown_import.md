# Confluence Markdown Import Reference

## REST Operations

For Confluence Server/Data Center, use the REST API with Basic Auth or the initialized connector provided by the user.

Fetch page:

```text
GET /rest/api/content/{pageId}?expand=body.storage,version,space,title
```

Update page:

```text
PUT /rest/api/content/{pageId}
```

Payload shape:

```json
{
  "id": "12345",
  "type": "page",
  "title": "Exact Page Title",
  "version": { "number": 8 },
  "body": {
    "storage": {
      "value": "<h1>...</h1>",
      "representation": "storage"
    }
  }
}
```

Upload or replace attachment:

```text
POST /rest/api/content/{pageId}/child/attachment
X-Atlassian-Token: no-check
Content-Type: multipart/form-data
field: file=@/path/to/image.png
```

If an attachment with the same filename already exists, Confluence may create a new attachment version. If the server rejects duplicates, query existing attachments first and post to the attachment's `/data` endpoint when supported by that instance.

## Markdown To Storage Mapping

| Markdown | Storage XHTML |
|---|---|
| `# Heading` | `<h1>Heading</h1>` |
| Paragraph | `<p>Paragraph</p>` |
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `` `code` `` | `<code>code</code>` |
| fenced code | `<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">...</ac:parameter><ac:plain-text-body><![CDATA[...]]></ac:plain-text-body></ac:structured-macro>` |
| image attachment | `<ac:image><ri:attachment ri:filename="name.png" /></ac:image>` |
| external image | `<ac:image><ri:url ri:value="https://..." /></ac:image>` |

Declare these namespaces when validating wrapped XML:

```text
xmlns:ac="http://atlassian.com/content"
xmlns:ri="http://atlassian.com/resource/identifier"
```

## Image Path Rules

- Resolve relative paths against the Markdown file's parent directory.
- Leave absolute local paths as-is only if they exist and are readable.
- Support URL-encoded spaces in Markdown paths.
- Preserve remote `http://` and `https://` URLs unless mirroring is requested.
- Warn on missing local files and stop before page update.

## Recommended Checks Before Publish

- The converted body is non-empty.
- XML parsing succeeds when wrapped in a root element with `ac` and `ri` namespaces.
- Every local image reference is either uploaded and rewritten as `ri:attachment` or explicitly accepted as unresolved.
- The page version used for update is freshly fetched.
