#!/usr/bin/env python3
"""Convert a Markdown file to Confluence Storage XHTML and optionally upload images."""

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def unique_names(paths):
    seen = {}
    result = {}
    for path in paths:
        name = Path(urllib.parse.unquote(path)).name
        if name not in seen:
            seen[name] = 1
            result[path] = name
            continue
        seen[name] += 1
        stem = Path(name).stem
        suffix = Path(name).suffix
        result[path] = f"{stem}-{seen[name]}{suffix}"
    return result


def resolve_image(md_dir, raw):
    raw = raw.strip("<>")
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme in ("http", "https"):
        return raw, None
    decoded = urllib.parse.unquote(raw)
    path = Path(decoded)
    if not path.is_absolute():
        path = md_dir / path
    return raw, path.resolve()


def upload_attachment(base_url, page_id, username, password, file_path, filename):
    try:
        return post_attachment(base_url, page_id, username, password, file_path, filename)
    except RuntimeError as exc:
        if "HTTP 400" not in str(exc) and "HTTP 409" not in str(exc):
            raise
        attachment_id = find_attachment_id(base_url, page_id, username, password, filename)
        if not attachment_id:
            raise
        return update_attachment_data(base_url, page_id, attachment_id, username, password, file_path, filename)


def post_attachment(base_url, page_id, username, password, file_path, filename):
    boundary = f"----codex-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    data = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = auth_header(username, password)
    headers.update({
        "X-Atlassian-Token": "no-check",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}/child/attachment"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"attachment upload failed for {file_path}: HTTP {exc.code}: {detail}") from exc


def api_get_json(url, username, password):
    headers = auth_header(username, password)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())


def find_attachment_id(base_url, page_id, username, password, filename):
    quoted = urllib.parse.quote(filename)
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}/child/attachment?filename={quoted}"
    data = api_get_json(url, username, password)
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("id")


def update_attachment_data(base_url, page_id, attachment_id, username, password, file_path, filename):
    boundary = f"----codex-{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    data = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = auth_header(username, password)
    headers.update({
        "X-Atlassian-Token": "no-check",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    url = f"{base_url.rstrip('/')}/rest/api/content/{page_id}/child/attachment/{attachment_id}/data"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"attachment update failed for {file_path}: HTTP {exc.code}: {detail}") from exc


def inline_markup(text):
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = LINK_RE.sub(lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', escaped)
    return escaped


def render_inline_with_images(text, attachments):
    rendered = []
    last = 0
    for match in IMAGE_RE.finditer(text):
        rendered.append(inline_markup(text[last:match.start()]))
        rendered.append(image_tag(match.group(1), match.group(2), attachments))
        last = match.end()
    rendered.append(inline_markup(text[last:]))
    return "".join(rendered)


def image_tag(alt, raw_src, attachments):
    alt_attr = f' ac:alt="{html.escape(alt, quote=True)}"' if alt else ""
    parsed = urllib.parse.urlparse(raw_src)
    if parsed.scheme in ("http", "https"):
        return f'<ac:image{alt_attr}><ri:url ri:value="{html.escape(raw_src, quote=True)}" /></ac:image>'
    filename = attachments.get(raw_src)
    if not filename:
        raise RuntimeError(f"image was not resolved/uploaded: {raw_src}")
    return f'<ac:image{alt_attr}><ri:attachment ri:filename="{html.escape(filename, quote=True)}" /></ac:image>'


def convert_blocks(markdown, attachments):
    lines = markdown.splitlines()
    table_starts = set()
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and is_table_separator_line(lines[idx + 1]):
            table_starts.add(idx)
    out = []
    para = []
    in_code = False
    code_lang = ""
    code_lines = []
    list_type = None
    list_items = []
    table_rows = []

    def flush_para():
        if not para:
            return
        text = " ".join(para).strip()
        para.clear()
        image_only = IMAGE_RE.fullmatch(text)
        if image_only:
            out.append(image_tag(image_only.group(1), image_only.group(2), attachments))
        else:
            out.append(f"<p>{render_inline_with_images(text, attachments)}</p>")

    def flush_list():
        nonlocal list_type, list_items
        if not list_type:
            return
        tag = "ol" if list_type == "ol" else "ul"
        body = "".join(f"<li>{inline_markup(item)}</li>" for item in list_items)
        out.append(f"<{tag}>{body}</{tag}>")
        list_type = None
        list_items = []

    def is_table_separator(line):
        return is_table_separator_line(line)

    def is_horizontal_rule(line):
        return bool(re.match(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$", line))

    def flush_table():
        nonlocal table_rows
        if not table_rows:
            return
        header = table_rows[0]
        body_rows = table_rows[1:]
        header_xml = "".join(f"<th>{render_inline_with_images(cell, attachments)}</th>" for cell in header)
        rows_xml = [f"<tr>{header_xml}</tr>"]
        for row in body_rows:
            rows_xml.append("".join(["<tr>", *[f"<td>{render_inline_with_images(cell, attachments)}</td>" for cell in row], "</tr>"]))
        out.append(f"<table><tbody>{''.join(rows_xml)}</tbody></table>")
        table_rows = []

    def parse_table_row(line):
        if "|" not in line:
            return None
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    for idx, line in enumerate(lines):
        fence = re.match(r"^```(\w+)?\s*$", line)
        if fence:
            if in_code:
                language = f'<ac:parameter ac:name="language">{html.escape(code_lang)}</ac:parameter>' if code_lang else ""
                code = "\n".join(code_lines)
                out.append(
                    '<ac:structured-macro ac:name="code">'
                    f"{language}<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>"
                    "</ac:structured-macro>"
                )
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                flush_para()
                flush_list()
                flush_table()
                in_code = True
                code_lang = fence.group(1) or ""
            continue
        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_para()
            flush_list()
            flush_table()
            continue

        if is_horizontal_rule(line):
            flush_para()
            flush_list()
            flush_table()
            out.append("<hr />")
            continue

        table_row = parse_table_row(line)
        if table_rows and table_row is not None:
            if len(table_rows) == 1 and is_table_separator(line):
                continue
            table_rows.append(table_row)
            continue
        if table_rows:
            flush_table()
        if idx in table_starts and table_row is not None:
            flush_para()
            flush_list()
            table_rows.append(table_row)
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_para()
            flush_list()
            flush_table()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markup(heading.group(2).strip())}</h{level}>")
            continue

        bullet = re.match(r"^\s*[-*+]\s+(.+)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if bullet or ordered:
            flush_para()
            flush_table()
            item_type = "ul" if bullet else "ol"
            if list_type and list_type != item_type:
                flush_list()
            list_type = item_type
            list_items.append((bullet or ordered).group(1).strip())
            continue

        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            flush_para()
            flush_list()
            flush_table()
            out.append(f"<blockquote><p>{inline_markup(quote.group(1))}</p></blockquote>")
            continue

        para.append(line.strip())

    flush_para()
    flush_list()
    flush_table()
    if in_code:
        raise RuntimeError("unclosed fenced code block")
    return "\n".join(out) + "\n"


def is_table_separator_line(line):
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", cell) for cell in cells)


def validate_storage_xml(content):
    wrapped = (
        '<root xmlns:ac="http://atlassian.com/content" '
        'xmlns:ri="http://atlassian.com/resource/identifier">'
        f"{content}</root>"
    )
    ET.fromstring(wrapped)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    convert = sub.add_parser("convert")
    convert.add_argument("--md", required=True)
    convert.add_argument("--out", required=True)
    convert.add_argument("--base-url")
    convert.add_argument("--page-id")
    convert.add_argument("--username")
    convert.add_argument("--password")
    convert.add_argument("--upload-images", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.md).resolve()
    text = md_path.read_text(encoding="utf-8")
    raw_images = [m.group(2) for m in IMAGE_RE.finditer(text)]
    resolved = [resolve_image(md_path.parent, raw) for raw in raw_images]
    local = [(raw, path) for raw, path in resolved if path is not None]
    missing = [str(path) for _, path in local if not path.exists()]
    if missing:
        raise SystemExit("missing local images:\n" + "\n".join(missing))

    names = unique_names([raw for raw, _ in local])
    if args.upload_images:
        required = [args.base_url, args.page_id, args.username, args.password]
        if not all(required):
            raise SystemExit("--upload-images requires --base-url, --page-id, --username, and --password")
        for raw, path in local:
            upload_attachment(args.base_url, args.page_id, args.username, args.password, path, names[raw])

    body = convert_blocks(text, names)
    validate_storage_xml(body)
    Path(args.out).write_text(body, encoding="utf-8")
    print(json.dumps({
        "status": "converted",
        "markdown": str(md_path),
        "output": args.out,
        "local_images": [{"source": raw, "attachment": names[raw]} for raw, _ in local],
        "uploaded_images": bool(args.upload_images),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
