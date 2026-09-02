# 完整工作流示例

> 本文件提供一个端到端的 Python 参考实现，展示如何将所有步骤串联执行。
> 此脚本仅作参考，实际执行时 AI 智能体应按 SKILL.md 中的步骤逐步执行 agent-browser 命令。

## 参考脚本

```python
#!/usr/bin/env python3
"""
Jira 工作周报生成器
依赖: agent-browser CLI (已安装并配置浏览器运行时)

用法:
  python weekly_report.py --user <邮箱> --password <密码>

注意: 凭据仅通过命令行参数传递，不写入任何文件。
"""

import argparse
import json
import subprocess
import urllib.parse
import uuid
from datetime import datetime, timedelta

# ============================================================
# 配置常量
# ============================================================
JIRA_BASE = "https://ticket.quectel.com"
CONFLUENCE_BASE = "https://knowledge.quectel.com"
USER_FIELD = "Software Development Engineer 软件开发工程师"
CONFLUENCE_SPACE = "SWSZTSMAR"
PARENT_PAGE_ID = "379073787"
PAGE_PREFIX = "叶启航-rayman.ye-2026"
SESSION_NAME = "quectel-session"
JIRA_SERVER_ID = "64c93c65-d9d2-3802-baea-f7a3f83589c5"
JIRA_SERVER_NAME = "quectel-ticket"

# agent-browser CLI 路径 (按实际安装路径修改)
AB_CMD = "agent-browser"

# ============================================================
# agent-browser 封装
# ============================================================
def ab(*args, timeout=30):
    """执行 agent-browser 命令"""
    result = subprocess.run(
        [AB_CMD] + list(args),
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout.strip()

def ab_open(url):
    """打开 URL"""
    return ab("open", url)

def ab_get_text():
    """获取页面文本内容"""
    return ab("get", "text")

def ab_eval(js):
    """执行 JavaScript"""
    return ab("eval", js)

def ab_wait(text=None, url=None, load=None, timeout=30):
    """等待条件"""
    args = ["wait"]
    if text:
        args += ["--text", text]
    if url:
        args += ["--url", url]
    if load:
        args += ["--load", load]
    return ab(*args, timeout=timeout)

def ab_snapshot():
    """获取页面快照"""
    return ab("snapshot", "-i")

# ============================================================
# Step 1: 认证
# ============================================================
def authenticate(user, password, force_relogin=False):
    """登录 Jira 并保存会话状态"""
    if not force_relogin:
        # 尝试加载已有会话
        ab("state", "load", SESSION_NAME)
        ab_open(f"{JIRA_BASE}/rest/api/2/myself")
        text = ab_get_text()
        if '"name"' in text or '"emailAddress"' in text:
            print("[OK] 会话有效")
            return True

    # 需要重新登录
    print("[INFO] 需要重新登录...")
    ab_open(f"{JIRA_BASE}/login.jspa")
    ab_wait(load="networkidle")
    snapshot = ab_snapshot()

    # 解析 snapshot 找到表单元素 ref
    # 实际实现中需要从 snapshot 输出中提取 ref
    # 这里用 CSS 选择器作为后备
    ab("fill", 'input[name="os_username"]', user)
    ab("fill", 'input[name="os_password"]', password)
    ab("click", 'input[name="login"]')
    ab_wait(url="ticket.quectel.com", load="networkidle")

    # 验证登录
    ab_open(f"{JIRA_BASE}/rest/api/2/myself")
    text = ab_get_text()
    if '"name"' in text:
        print("[OK] 登录成功")
        ab("state", "save", SESSION_NAME)
        return True
    else:
        print("[FAIL] 登录失败")
        return False

# ============================================================
# Step 2: 计算自然周日期
# ============================================================
def get_week_range(ref_date=None):
    """计算当前自然周的周一和周六日期"""
    if ref_date is None:
        ref_date = datetime.now()

    # 周一 = 当前日期 - (星期几 - 1)
    monday = ref_date - timedelta(days=ref_date.weekday())
    # 周六 = 周一 + 5 (用于 JQL 上界, 不含)
    saturday = monday + timedelta(days=5)
    friday = monday + timedelta(days=4)

    return {
        "monday": monday.strftime("%Y-%m-%d"),
        "friday": friday.strftime("%Y-%m-%d"),
        "saturday": saturday.strftime("%Y-%m-%d"),
    }

# ============================================================
# Step 3: 查询 Jira 工单
# ============================================================
def query_jira_issues(week_range):
    """查询本周更新的所有工单（不分 CLOSED 状态）"""
    jql = (
        f'"{USER_FIELD}" = currentUser() '
        f'AND updated >= "{week_range["monday"]}" '
        f'AND updated < "{week_range["saturday"]}"'
    )

    fields = "key,summary,status,created,updated,issuetype,priority"
    url = (
        f"{JIRA_BASE}/rest/api/2/search?"
        f"jql={urllib.parse.quote(jql)}"
        f"&fields={urllib.parse.quote(fields)}"
        f"&maxResults=200"
    )

    ab_open(url)
    text = ab_get_text()

    try:
        data = json.loads(text)
        issues = data.get("issues", [])
        print(f"[OK] 查询到 {len(issues)} 个工单")
        return issues
    except json.JSONDecodeError:
        print("[FAIL] 无法解析 Jira 响应")
        print(f"Response: {text[:500]}")
        return []

# ============================================================
# Step 4: 分类工单
# ============================================================
def classify_issues(issues, week_range):
    """按创建时间分类为本周新增和上周遗留"""
    monday = week_range["monday"]
    saturday = week_range["saturday"]

    carried_over = []  # 上周遗留
    new_this_week = []  # 本周新增

    for issue in issues:
        created = issue["fields"]["created"][:10]  # YYYY-MM-DD
        if created >= monday and created < saturday:
            new_this_week.append(issue)
        else:
            carried_over.append(issue)

    print(f"[OK] 上周遗留: {len(carried_over)} 个, 本周新增: {len(new_this_week)} 个")
    return {
        "carried_over": carried_over,
        "new_this_week": new_this_week,
    }

# ============================================================
# Step 5: Confluence 页面管理
# ============================================================
def find_monthly_page(month):
    """查找月度页面，返回 page_id 或 None"""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{PARENT_PAGE_ID}/child/page?limit=50"
    ab_open(url)
    text = ab_get_text()

    try:
        data = json.loads(text)
        page_title = f"{PAGE_PREFIX}-{month:02d}"
        for page in data.get("results", []):
            if page["title"] == page_title:
                print(f"[OK] 找到月度页面: {page_title} (ID: {page['id']})")
                return page["id"]
    except json.JSONDecodeError:
        pass

    print(f"[INFO] 月度页面不存在: {PAGE_PREFIX}-{month:02d}")
    return None

def create_monthly_page(month):
    """创建月度页面，返回 page_id"""
    page_title = f"{PAGE_PREFIX}-{month:02d}"
    payload = json.dumps({
        "type": "page",
        "title": page_title,
        "space": {"key": CONFLUENCE_SPACE},
        "ancestors": [{"id": PARENT_PAGE_ID}],
        "body": {
            "storage": {
                "value": "<p>月度周报页面</p>",
                "representation": "storage"
            }
        }
    })

    js = f"""
    (async () => {{
      const res = await fetch('{CONFLUENCE_BASE}/rest/api/content', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({payload.replace(chr(39), chr(92)+chr(39))})
      }});
      const data = await res.json();
      document.title = 'API_DONE';
      document.body.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    }})()
    """

    ab_eval(js)
    ab_wait(text="API_DONE")
    text = ab_get_text()

    try:
        data = json.loads(text)
        page_id = data["id"]
        print(f"[OK] 创建月度页面: {page_title} (ID: {page_id})")
        return page_id
    except (json.JSONDecodeError, KeyError):
        print(f"[FAIL] 创建页面失败: {text[:500]}")
        return None

def get_page_content(page_id):
    """获取页面内容和版本号"""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}?expand=body.storage,version"
    ab_open(url)
    text = ab_get_text()

    try:
        data = json.loads(text)
        return {
            "version": data["version"]["number"],
            "body": data["body"]["storage"]["value"]
        }
    except (json.JSONDecodeError, KeyError):
        print(f"[FAIL] 获取页面内容失败: {text[:500]}")
        return None

def update_page(page_id, title, new_body, current_version):
    """更新 Confluence 页面"""
    payload = json.dumps({
        "id": page_id,
        "type": "page",
        "title": title,
        "space": {"key": CONFLUENCE_SPACE},
        "body": {
            "storage": {
                "value": new_body,
                "representation": "storage"
            }
        },
        "version": {"number": current_version + 1}
    })

    js = f"""
    (async () => {{
      const res = await fetch('{CONFLUENCE_BASE}/rest/api/content/{page_id}', {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({payload.replace(chr(39), chr(92)+chr(39))})
      }});
      const data = await res.json();
      document.title = 'API_DONE';
      document.body.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    }})()
    """

    ab_eval(js)
    ab_wait(text="API_DONE")
    text = ab_get_text()

    try:
        data = json.loads(text)
        if "id" in data:
            print(f"[OK] 页面更新成功 (版本 {current_version + 1})")
            return True
        else:
            print(f"[FAIL] 页面更新失败: {text[:500]}")
            return False
    except json.JSONDecodeError:
        print(f"[FAIL] 解析响应失败: {text[:500]}")
        return False

# ============================================================
# Step 6: 生成周报 HTML
# ============================================================
def make_jira_macro(issue_key):
    """生成 Confluence Jira Macro HTML"""
    macro_id = str(uuid.uuid4())
    return (
        f'<ac:structured-macro ac:name="jira" ac:schema-version="1" ac:macro-id="{macro_id}">'
        f'<ac:parameter ac:name="server">{JIRA_SERVER_NAME}</ac:parameter>'
        f'<ac:parameter ac:name="serverId">{JIRA_SERVER_ID}</ac:parameter>'
        f'<ac:parameter ac:name="key">{issue_key}</ac:parameter>'
        f'</ac:structured-macro>'
    )

def generate_report_html(week_range, classified):
    """生成周报 HTML 片段"""
    lines = []

    # 标题
    lines.append(
        f'<p><strong><span style="color: rgb(0,51,102);">'
        f'时间：（{week_range["monday"]}~{week_range["friday"]}）'
        f'</span></strong></p>'
    )

    # 上周遗留问题
    lines.append('<p><strong>上周遗留问题：</strong></p>')
    lines.append('<ol>')
    if classified["carried_over"]:
        for issue in classified["carried_over"]:
            lines.append(f'<li>{make_jira_macro(issue["key"])}</li>')
    else:
        lines.append('<li>无</li>')
    lines.append('</ol>')
    lines.append('<p><br /></p>')

    # 本周新增问题
    lines.append('<p><strong>本周新增问题：</strong></p>')
    lines.append('<ol>')
    if classified["new_this_week"]:
        for issue in classified["new_this_week"]:
            lines.append(f'<li>{make_jira_macro(issue["key"])}</li>')
    else:
        lines.append('<li>无</li>')
    lines.append('</ol>')
    lines.append('<p><br /></p>')
    lines.append('<p><br /></p>')

    return ''.join(lines)

# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Jira 工作周报生成器")
    parser.add_argument("--user", required=True, help="Jira 登录邮箱")
    parser.add_argument("--password", required=True, help="Jira 登录密码")
    parser.add_argument("--force-relogin", action="store_true", help="强制重新登录")
    args = parser.parse_args()

    # Step 1: 认证
    print("=== Step 1: 认证 ===")
    if not authenticate(args.user, args.password, args.force_relogin):
        return

    # Step 2: 计算自然周
    print("\n=== Step 2: 计算自然周 ===")
    week_range = get_week_range()
    print(f"周一: {week_range['monday']}, 周五: {week_range['friday']}")

    # Step 3: 查询 Jira
    print("\n=== Step 3: 查询 Jira 工单 ===")
    issues = query_jira_issues(week_range)

    # Step 4: 分类
    print("\n=== Step 4: 分类工单 ===")
    classified = classify_issues(issues, week_range)

    # Step 5: 管理 Confluence 页面
    print("\n=== Step 5: Confluence 页面管理 ===")
    now = datetime.now()
    month = now.month
    page_id = find_monthly_page(month)
    if not page_id:
        page_id = create_monthly_page(month)
        if not page_id:
            print("[FAIL] 无法创建月度页面")
            return

    page_data = get_page_content(page_id)
    if not page_data:
        print("[FAIL] 无法获取页面内容")
        return

    # Step 6: 生成周报
    print("\n=== Step 6: 生成周报 HTML ===")
    report_html = generate_report_html(week_range, classified)

    # Step 7: 更新页面 (新周报 prepend)
    print("\n=== Step 7: 更新 Confluence 页面 ===")
    new_body = report_html + page_data["body"]
    page_title = f"{PAGE_PREFIX}-{month:02d}"
    update_page(page_id, page_title, new_body, page_data["version"])

    # Step 8: 清理
    print("\n=== Step 8: 清理 ===")
    ab("close")
    print("[DONE] 周报生成完成")

if __name__ == "__main__":
    main()
```

## 替代方案: curl + Basic Auth

如果 agent-browser 不可用，可使用 curl 作为后备方案：

```bash
# Jira 查询
curl -s -u "<邮箱>:<密码>" -G "https://ticket.quectel.com/rest/api/2/search" \
  --data-urlencode 'jql="Software Development Engineer 软件开发工程师" = currentUser() AND updated >= "2026-08-03" AND updated < "2026-08-08"' \
  --data-urlencode 'fields=key,summary,status,created,updated' \
  --data-urlencode 'maxResults=200'

# Confluence 获取子页面
curl -s -u "<邮箱>:<密码>" "https://knowledge.quectel.com/rest/api/content/379073787/child/page?limit=50"

# Confluence 创建页面
curl -s -u "<邮箱>:<密码>" -X POST "https://knowledge.quectel.com/rest/api/content" \
  -H "Content-Type: application/json" \
  -d '{"type":"page","title":"叶启航-rayman.ye-2026-08","space":{"key":"SWSZTSMAR"},"ancestors":[{"id":"379073787"}],"body":{"storage":{"value":"<p>内容</p>","representation":"storage"}}}'

# Confluence 更新页面
curl -s -u "<邮箱>:<密码>" -X PUT "https://knowledge.quectel.com/rest/api/content/<page_id>" \
  -H "Content-Type: application/json" \
  -d '{"id":"<page_id>","type":"page","title":"叶启航-rayman.ye-2026-08","space":{"key":"SWSZTSMAR"},"body":{"storage":{"value":"<新内容>","representation":"storage"}},"version":{"number":<当前版本+1>}}'
```

> **注意**: curl 方式需要在命令行中传递凭据，可能被 shell history 记录。agent-browser 方式更安全。
