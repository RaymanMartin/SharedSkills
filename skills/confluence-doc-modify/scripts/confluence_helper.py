#!/usr/bin/env python3
"""
Confluence Server/Data Center helper script.
Usage:
  python confluence_helper.py get   <base_url> <page_id_or_url> <username> <password>
  python confluence_helper.py update <base_url> <page_id> <username> <password> <title> <version> <storage_content_file>
"""

import sys
import json
import re
import urllib.request
import urllib.parse
import urllib.error
import base64
import ssl


def make_auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def extract_page_id(base_url, page_id_or_url):
    """Extract numeric page ID from a URL or return as-is if already an ID."""
    # If it's already a numeric ID
    if re.match(r'^\d+$', page_id_or_url.strip()):
        return page_id_or_url.strip()

    # Pattern: /pages/viewpage.action?pageId=12345
    m = re.search(r'pageId=(\d+)', page_id_or_url)
    if m:
        return m.group(1)

    # Pattern: /pages/12345 or /display/SPACE/Title-with-id-12345 tail
    m = re.search(r'/pages/(\d+)', page_id_or_url)
    if m:
        return m.group(1)

    # Pattern: /display/SPACE/Page+Title  -> need to search by title
    m = re.search(r'/display/([^/]+)/(.+)', page_id_or_url)
    if m:
        space_key = m.group(1)
        title = urllib.parse.unquote_plus(m.group(2).replace('+', ' '))
        return f"SEARCH:{space_key}:{title}"

    return None


def api_get(url, headers):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def api_put(url, headers, data):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method='PUT')
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def cmd_get(base_url, page_id_or_url, username, password):
    headers = make_auth_header(username, password)
    base_url = base_url.rstrip('/')

    resolved = extract_page_id(base_url, page_id_or_url)
    if resolved is None:
        print("ERROR: Cannot parse page ID from the given URL.", file=sys.stderr)
        sys.exit(1)

    if resolved.startswith("SEARCH:"):
        _, space_key, title = resolved.split(":", 2)
        search_url = (f"{base_url}/rest/api/content?"
                      f"spaceKey={urllib.parse.quote(space_key)}"
                      f"&title={urllib.parse.quote(title)}"
                      f"&expand=body.storage,version,space")
        data = api_get(search_url, headers)
        results = data.get("results", [])
        if not results:
            print(f"ERROR: Page not found: space={space_key}, title={title}", file=sys.stderr)
            sys.exit(1)
        page = results[0]
    else:
        page_url = f"{base_url}/rest/api/content/{resolved}?expand=body.storage,version,space,title"
        page = api_get(page_url, headers)

    output = {
        "page_id": page["id"],
        "title": page["title"],
        "version": page["version"]["number"],
        "space_key": page.get("space", {}).get("key", ""),
        "storage_content": page["body"]["storage"]["value"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_update(base_url, page_id, username, password, title, version, content_file):
    with open(content_file, 'r', encoding='utf-8') as f:
        new_content = f.read()

    headers = make_auth_header(username, password)
    base_url = base_url.rstrip('/')
    url = f"{base_url}/rest/api/content/{page_id}"

    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {"number": int(version) + 1},
        "body": {
            "storage": {
                "value": new_content,
                "representation": "storage"
            }
        }
    }

    result = api_put(url, headers, payload)
    print(json.dumps({
        "status": "updated",
        "page_id": result.get("id"),
        "title": result.get("title"),
        "new_version": result.get("version", {}).get("number"),
        "url": result.get("_links", {}).get("base", base_url) + result.get("_links", {}).get("webui", "")
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "get":
        if len(sys.argv) != 6:
            print("Usage: confluence_helper.py get <base_url> <page_id_or_url> <username> <password>")
            sys.exit(1)
        cmd_get(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

    elif cmd == "update":
        if len(sys.argv) != 9:
            print("Usage: confluence_helper.py update <base_url> <page_id> <username> <password> <title> <version> <storage_content_file>")
            sys.exit(1)
        cmd_update(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                   sys.argv[6], sys.argv[7], sys.argv[8])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
