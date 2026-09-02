#!/usr/bin/env python3
"""
Weekly Report Skill - 自动生成飞书周报正文
用法:
  python3 run.py
  python3 run.py --start 2026-08-24 --end 2026-08-29
"""
import argparse
import base64
import getpass
import html
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


JIRA_URL = "https://ticket.quectel.com"
FEISHU_ROOT_URL = "https://quectel.feishu.cn/wiki/PNUMwZUyZieLtEkzRmrcuLDun0b"
PAGE_PREFIX = "叶启航-rayman.ye-2026"
OWNER_FIELD = "cf[12001]"  # Software Development Engineer 软件开发工程师
TZ_OFFSET = timezone(timedelta(hours=8))

AGENT_BROWSER = (
    os.environ.get("AGENT_BROWSER")
    or shutil.which("agent-browser")
    or "/home/quectel/.hermes/hermes-agent/node_modules/agent-browser/bin/agent-browser.js"
)
CHROME_BIN = os.environ.get("CHROME_BIN") or shutil.which("google-chrome") or "/opt/google/chrome/google-chrome"
CDP_PORT = os.environ.get("FEISHU_CDP_PORT", "9222")

OPEN_STATUSES_EXCLUDED = ("Closed", "SW_Resolved", "patched", "Resolved", "ST_Closed")
FAE_ISSUE_TYPE = "Software-Issues"
FAE_OVERDUE_DAYS = 2
FAE_HIGH_PRIORITY_DAYS = 1
HIGH_PRIORITY_NAMES = {"High", "Critical", "Blocker", "High-高", "Critical-紧急", "Blocker-阻塞"}
STATUS_RED = "#d83931"


def parse_args():
    parser = argparse.ArgumentParser(description="生成飞书周报正文并检查 Chrome 登录会话")
    parser.add_argument("--start", help="报告开始日期 YYYY-MM-DD，默认本周一")
    parser.add_argument("--end", help="报告结束日期 YYYY-MM-DD，默认本周五")
    parser.add_argument("--no-browser", action="store_true", help="只生成内容，不检查/打开飞书 Chrome 会话")
    return parser.parse_args()


def get_report_range(args):
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start 和 --end 必须同时指定")
        start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=TZ_OFFSET)
        end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=TZ_OFFSET)
        return start, end

    today = datetime.now(TZ_OFFSET)
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return (
        monday.replace(hour=0, minute=0, second=0, microsecond=0),
        friday.replace(hour=23, minute=59, second=59, microsecond=0),
    )


def auth_headers(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def api_get(url, headers):
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")[:300]
        print(f"HTTP {exc.code}: {url}\n{body}")
        return None
    except URLError as exc:
        print(f"连接失败: {exc.reason}")
        return None


def jira_search(headers):
    status_filter = " AND ".join(f"status != {status}" for status in OPEN_STATUSES_EXCLUDED)
    jql = f"{OWNER_FIELD} = currentUser() AND {status_filter} ORDER BY created DESC"
    params = urlencode({
        "jql": jql,
        "maxResults": 200,
        "fields": "summary,status,priority,issuetype,created,updated",
    })
    data = api_get(f"{JIRA_URL}/rest/api/2/search?{params}", headers)
    return data.get("issues", []) if data else []


def classify_issues(issues, start, end):
    new_issues = []
    carried_issues = []
    start_date = start.date()
    end_date = end.date()

    for issue in issues:
        created = datetime.strptime(issue["fields"]["created"][:10], "%Y-%m-%d").date()
        if created > end_date:
            continue
        if created >= start_date:
            new_issues.append(issue)
        else:
            carried_issues.append(issue)
    return new_issues, carried_issues


def issue_status(issue):
    return issue["fields"].get("status", {}).get("name", "")


def issue_summary(issue):
    return issue["fields"].get("summary", "")


def issue_url(issue):
    return f"{JIRA_URL}/browse/{issue['key']}"


def report_text(start, end, new_issues, carried_issues):
    date_range = f"{start:%Y-%m-%d}~{end:%Y-%m-%d}"

    def lines(issues):
        if not issues:
            return ["无"]
        return [
            f"{idx}. {issue_url(issue)} {issue_summary(issue)} {issue_status(issue)}"
            for idx, issue in enumerate(issues, 1)
        ]

    return "\n".join([
        f"时间：（{date_range}）",
        "",
        "上周遗留问题：",
        *lines(carried_issues),
        "",
        "本周新增问题：",
        *lines(new_issues),
    ])


def report_html(start, end, new_issues, carried_issues):
    date_range = f"{start:%Y-%m-%d}~{end:%Y-%m-%d}"

    def rows(issues):
        if not issues:
            return "<p>无</p>"
        items = []
        for issue in issues:
            url = html.escape(issue_url(issue))
            summary = html.escape(issue_summary(issue))
            status = html.escape(issue_status(issue))
            items.append(
                f'<li><a href="{url}">{url}</a> {summary} '
                f'<span style="color:{STATUS_RED};">{status}</span></li>'
            )
        return "<ol>" + "".join(items) + "</ol>"

    return (
        f"<p>时间：（{html.escape(date_range)}）</p>"
        "<p><br></p>"
        "<p>上周遗留问题：</p>"
        f"{rows(carried_issues)}"
        "<p><br></p>"
        "<p>本周新增问题：</p>"
        f"{rows(new_issues)}"
    )


def check_fae_overdue(issues):
    now = datetime.now(TZ_OFFSET)
    alerts = []
    for issue in issues:
        fields = issue["fields"]
        if fields.get("issuetype", {}).get("name") != FAE_ISSUE_TYPE:
            continue
        if issue_status(issue).lower() not in ("working", "in progress", "处理中"):
            continue

        updated_raw = fields.get("updated", "")
        if not updated_raw:
            continue
        try:
            updated_raw = updated_raw[:-2] + ":" + updated_raw[-2:]
            updated = datetime.fromisoformat(updated_raw).astimezone(TZ_OFFSET)
        except ValueError:
            continue

        priority = fields.get("priority", {}).get("name", "")
        threshold = FAE_HIGH_PRIORITY_DAYS if priority in HIGH_PRIORITY_NAMES else FAE_OVERDUE_DAYS
        days_since = (now - updated).days
        if days_since >= threshold:
            alerts.append({
                "key": issue["key"],
                "summary": issue_summary(issue)[:60],
                "priority": priority,
                "days_since": days_since,
                "threshold": threshold,
            })
    return alerts


def run_browser(*args):
    cmd = [AGENT_BROWSER]
    if AGENT_BROWSER.endswith(".js"):
        cmd.insert(0, "node")
    cmd += ["--cdp", CDP_PORT, *args]
    env = os.environ.copy()
    env.setdefault("AGENT_BROWSER_HOME", "/tmp/agent-browser-home")
    return subprocess.run(cmd, text=True, capture_output=True, env=env, timeout=30)


def chrome_probe():
    return run_browser("get", "url")


def launch_chrome():
    profile_dir = os.environ.get("FEISHU_CHROME_PROFILE", "/tmp/feishu-weekly-chrome-profile")
    cmd = [
        CHROME_BIN,
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--disable-default-apps",
        FEISHU_ROOT_URL,
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        return False, f"Chrome 启动失败: {exc}"

    time.sleep(3)
    probe = chrome_probe()
    if probe.returncode == 0:
        return True, ""

    stderr = ""
    if proc.poll() is not None:
        _, stderr = proc.communicate(timeout=1)
    return False, stderr.strip() or probe.stderr.strip() or probe.stdout.strip()


def ensure_chrome():
    probe = chrome_probe()
    if probe.returncode == 0:
        return True

    print(f"\n未发现可用 Chrome debug-port: {CDP_PORT}，尝试主动启动 Chrome...")
    started, reason = launch_chrome()
    if started:
        print("Chrome 已启动并可连接。")
        return True

    print("\nChrome 无法主动打开，飞书写入需要你处理浏览器权限或图形界面环境。")
    if reason:
        print(reason)
    print(f"可手动启动: {CHROME_BIN} --remote-debugging-port={CDP_PORT}")
    return False


def prepare_feishu_browser(month_title, rich_html, plain_text):
    if not ensure_chrome():
        return False

    opened = run_browser("open", FEISHU_ROOT_URL)
    if opened.returncode != 0:
        print("\n已连接 Chrome，但无法打开飞书年度页。")
        print(opened.stderr.strip() or opened.stdout.strip())
        print("如果浏览器打开需要权限，请通知我处理。")
        return False

    js = (
        "(async()=>{"
        f"const html={json.dumps(rich_html, ensure_ascii=False)};"
        f"const text={json.dumps(plain_text, ensure_ascii=False)};"
        "await navigator.clipboard.write([new ClipboardItem({"
        "'text/html':new Blob([html],{type:'text/html'}),"
        "'text/plain':new Blob([text],{type:'text/plain'})"
        "})]);window.__weeklyReportClipboard='ok';"
        "})().catch(e=>{window.__weeklyReportClipboard='ERR:'+e.message})"
    )
    copied = run_browser("eval", js)
    if copied.returncode != 0:
        print("\n飞书富文本复制到剪贴板失败。")
        print(copied.stderr.strip() or copied.stdout.strip())
        return False

    print("\n飞书年度页已在 Chrome 中打开，富文本周报已写入剪贴板。")
    print(f"目标月度子页面: {month_title}")
    print("请进入或新建该月度子页面后粘贴；Status 字段已带红色样式。")
    return True


def main():
    args = parse_args()
    start, end = get_report_range(args)
    month_title = f"{PAGE_PREFIX}-{start.month:02d}"

    print("Jira/飞书周报")
    print(f"报告周期: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}")

    username = input("Jira 用户名(email): ").strip()
    password = getpass.getpass("Jira 密码: ")
    headers = auth_headers(username, password)

    me = api_get(f"{JIRA_URL}/rest/api/2/myself", headers)
    if not me:
        print("Jira 账号验证失败")
        return 1
    print(f"Jira 登录成功: {me.get('displayName')}")

    issues = jira_search(headers)
    new_issues, carried_issues = classify_issues(issues, start, end)
    print(f"上周遗留: {len(carried_issues)} 个")
    print(f"本周新增: {len(new_issues)} 个")

    alerts = check_fae_overdue(new_issues + carried_issues)
    if alerts:
        print("\nFAE Case 超时告警:")
        for alert in alerts:
            print(
                f"- {alert['key']} {alert['summary']} | {alert['priority']} | "
                f"{alert['days_since']} 天未更新，阈值 {alert['threshold']} 天"
            )

    plain_text = report_text(start, end, new_issues, carried_issues)
    rich_html = report_html(start, end, new_issues, carried_issues)

    print(f"\n飞书年度根页面: {FEISHU_ROOT_URL}")
    print(f"目标月度子页面: {month_title}")
    print("\n周报正文:")
    print(plain_text)
    print("\n样式要求: 写入飞书时，每条末尾 Status 字段为红色。")

    if not args.no_browser:
        prepare_feishu_browser(month_title, rich_html, plain_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
