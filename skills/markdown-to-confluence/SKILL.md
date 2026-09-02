---
name: markdown-to-confluence
description: Import or sync a local Markdown document, including local images, into a Confluence page while preserving document structure and visual consistency.
---

# Markdown To Confluence

Use this skill when the user gives a local `.md` path and wants the document copied, imported, synchronized, or published to Confluence. The expected result is a Confluence page whose headings, lists, tables, code blocks, links, and images match the Markdown document as closely as Confluence Storage Format allows.

## Inputs

Collect only the missing inputs:

- Markdown file path.
- Target Confluence page URL or page ID.
- Confluence connection details. Prefer an initialized connector/session if one is available; otherwise use the user's Confluence Server/Data Center base URL plus username and password/API token.
- Whether to replace the full page body or append to a named section. Default to full replacement only when the user explicitly says this is a document import/sync.

Do not publish to Confluence until the target page has been fetched and the converted content is ready. If the page does not exist, ask whether to create it unless the user has explicitly requested creation.

## Workflow

1. Read the Markdown file from disk and resolve relative assets from the Markdown file's directory.
2. Inspect image references: `![](relative.png)`, reference-style image definitions, and HTML `<img src="...">` tags. Local images must be uploaded as Confluence attachments before publishing. Remote HTTP(S) images may remain external unless the user asks to mirror them.
3. Convert Markdown to Confluence Storage XHTML. Preserve document order, heading levels, tables, code fences with language names, blockquotes, checklists, links, and inline formatting. Prefer a structured converter such as `pandoc` when available; otherwise use [scripts/md_to_confluence.py](scripts/md_to_confluence.py) for a practical CommonMark subset.
4. Upload local images to the target page as attachments and rewrite their references to Confluence image tags:

   ```xml
   <ac:image><ri:attachment ri:filename="image.png" /></ac:image>
   ```

   Keep alt text when practical:

   ```xml
   <ac:image ac:alt="diagram"><ri:attachment ri:filename="diagram.png" /></ac:image>
   ```

5. Fetch the current page immediately before update, preserve the exact page title, and publish valid Storage XHTML with an incremented version.
6. After publishing, report the page title, URL, new version, Markdown source path, and any images that could not be uploaded or were left as external links.

## Helper Script

The helper script can convert Markdown and, when credentials are supplied, upload local images:

```bash
python3 <skill_dir>/scripts/md_to_confluence.py convert \
  --md /path/to/doc.md \
  --out /tmp/confluence_body.xml
```

```bash
python3 <skill_dir>/scripts/md_to_confluence.py convert \
  --md /path/to/doc.md \
  --out /tmp/confluence_body.xml \
  --base-url https://wiki.example.com \
  --page-id 12345 \
  --username "$CONFLUENCE_USER" \
  --password "$CONFLUENCE_PASSWORD" \
  --upload-images
```

Then update the page with the existing Confluence helper:

```bash
python3 /home/quectel/.shared-skills/skills/confluence-doc-modify/scripts/confluence_helper.py update \
  "<base_url>" "<page_id>" "<username>" "<password>" "<exact_page_title>" "<current_version>" \
  "/tmp/confluence_body.xml"
```

Use an initialized Confluence connector instead of these scripts when the session exposes one with equivalent page fetch, attachment upload, and page update operations.

## Consistency Rules

- Treat the Markdown as the source of truth for full imports. Do not rewrite prose unless the user asks.
- Avoid lossy simplification of tables, nested lists, fenced code, or images just to make conversion easier.
- Keep file and attachment names stable; if two local images share the same basename, generate deterministic unique attachment names before upload and rewrite the references accordingly.
- Validate generated XML before publishing. At minimum parse it as XML wrapped in a temporary root with Confluence namespaces declared.
- If any image upload fails, stop before updating the page unless the user explicitly accepts broken or external image references.
- Confluence Storage Format is XHTML-like XML. Escape text content, preserve UTF-8 Chinese text, and do not invent unsupported macros.

For REST details and image handling edge cases, read [references/confluence_markdown_import.md](references/confluence_markdown_import.md).
