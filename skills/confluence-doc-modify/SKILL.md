---
name: confluence-doc-modify
description: |
  Modify Confluence Server/Data Center wiki pages using natural language instructions or direct content.
  Given a Confluence page URL, login credentials (username + password), and modification instructions,
  this skill fetches the page, applies the requested changes (add/update/delete sections, modify tables,
  update text, rewrite content, etc.), and publishes the updated version back to Confluence.

  Use this skill IMMEDIATELY whenever the user wants to edit, update, rewrite, or modify a Confluence
  page and provides a URL + credentials + instructions. Triggers include: "update this Confluence page",
  "modify the doc at [url]", "add a section to Confluence", "edit this wiki page", "help me update the
  Confluence doc", "按照XXX修改这个Confluence文档", "更新Confluence页面内容", "对文档进行调整并更新回去".
---

# Confluence Doc Modify

This skill edits Confluence Server/Data Center pages via the REST API and publishes the result back.

## Workflow

### Step 1 — Collect inputs

Make sure you have all three inputs before proceeding:

| Input | Example |
|---|---|
| **Page URL or Page ID** | `https://wiki.example.com/display/TEAM/My+Page` or `12345` |
| **Credentials** | username + password (Basic Auth) |
| **Modification instructions** | Natural language ("Add a Risks section after Step 3") OR direct content ("Replace the intro with: …") |

If anything is missing, ask the user before continuing.

**Base URL** = the Confluence host, e.g. `https://wiki.example.com` (strip `/display/...` path).

---

### Step 2 — Fetch the page

Use the helper script to retrieve the current page content:

```bash
python <skill_dir>/scripts/confluence_helper.py get \
  "<base_url>" \
  "<page_url_or_id>" \
  "<username>" \
  "<password>"
```

The script outputs JSON:
```json
{
  "page_id": "12345",
  "title": "Page Title",
  "version": 7,
  "space_key": "TEAM",
  "storage_content": "<p>…Confluence storage XML…</p>"
}
```

**`<skill_dir>`** is the directory containing this SKILL.md — use it as a literal path when constructing the command.

If the page cannot be found, inform the user with the exact error and stop.

---

### Step 3 — Understand and apply modifications

The `storage_content` field is Confluence's **Storage Format** — an XHTML dialect. Key tags:

| Confluence concept | Storage tag |
|---|---|
| Paragraph | `<p>text</p>` |
| Heading (H1–H6) | `<h1>…</h1>` … `<h6>…</h6>` |
| Bulleted list | `<ul><li>…</li></ul>` |
| Numbered list | `<ol><li>…</li></ol>` |
| Table | `<table><tbody><tr><th>…</th><td>…</td></tr></tbody></table>` |
| Code block | `<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[…]]></ac:plain-text-body></ac:structured-macro>` |
| Info/Note panel | `<ac:structured-macro ac:name="info"><ac:rich-text-body><p>…</p></ac:rich-text-body></ac:structured-macro>` |
| Warning panel | `<ac:structured-macro ac:name="warning">…</ac:structured-macro>` |
| Bold | `<strong>text</strong>` |
| Italic | `<em>text</em>` |
| Inline link | `<a href="url">text</a>` |

#### Modification types

**Natural language instructions** (e.g., "在第二节后面加一个风险说明"):  
→ Parse the storage XML, identify the right location, insert/update/delete nodes accordingly, regenerate valid storage XML.

**Direct content replacement** (e.g., "把引言替换成: …"):  
→ Locate the target section and replace with the provided content, properly wrapped in storage XML tags.

**Rewrite / restructure** (e.g., "把整篇文章重新整理成更清晰的结构"):  
→ Transform the entire content while preserving factual information. Output well-formed storage XML.

#### Rules for storage XML
- Must be well-formed XML (all tags closed, attributes quoted).
- Do NOT invent Confluence macros you are not sure about; use plain XHTML when uncertain.
- Preserve any existing `ac:structured-macro` blocks that should not change.
- Keep Chinese characters as UTF-8 — do not escape them as XML entities.

---

### Step 4 — Write the new content to a temp file

Save the updated storage XML to a temporary file, e.g. `/tmp/confluence_new_content.xml`.

```bash
cat > /tmp/confluence_new_content.xml << 'CONFLUENCE_CONTENT_EOF'
<p>…updated storage XML…</p>
CONFLUENCE_CONTENT_EOF
```

Or use Python/bash redirection — whatever is reliable in the current environment.

---

### Step 5 — Push the update back to Confluence

```bash
python <skill_dir>/scripts/confluence_helper.py update \
  "<base_url>" \
  "<page_id>" \
  "<username>" \
  "<password>" \
  "<exact_page_title>" \
  "<current_version_number>" \
  "/tmp/confluence_new_content.xml"
```

- `<exact_page_title>` must match the title returned in Step 2 exactly (Confluence rejects mismatched titles).
- `<current_version_number>` is the `version` field from Step 2. The script auto-increments it by 1.

On success the script prints:
```json
{
  "status": "updated",
  "page_id": "12345",
  "title": "Page Title",
  "new_version": 8,
  "url": "https://wiki.example.com/display/TEAM/Page+Title"
}
```

---

### Step 6 — Confirm to the user

Report:
- ✅ Page updated successfully
- Page title and URL (clickable if terminal supports it)
- Brief summary of changes made (1–3 bullet points)
- New version number

If the update fails with HTTP 409 (conflict), the page was edited by someone else while this was running — fetch again and retry.

---

## Error handling

| Situation | Action |
|---|---|
| SSL certificate error | The script disables certificate verification for self-hosted instances — this is expected. |
| 401 Unauthorized | Ask user to verify username/password |
| 403 Forbidden | User lacks edit permission on the page |
| 404 Not Found | Double-check the URL and base URL |
| Page ID search returns 0 results | Ask user to confirm space key and page title |
| Content too large / macro errors | Simplify the storage XML; avoid complex nested macros |
