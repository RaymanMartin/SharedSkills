---
name: jira-weekly-report
description: |
  Jira 工作周报自动化：查询当前用户所有非关闭 Jira 工单，按 createdDate 分类为“上周遗留”和“本周新增”，
  在飞书年度页下查找或创建对应月份子页面，并写入时间、分类、Jira URL、标题和状态。
  每条问题最后的 Status 字段必须用红色字体标识，只标状态，不标 URL 或标题。
  年度根页面：https://quectel.feishu.cn/wiki/PNUMwZUyZieLtEkzRmrcuLDun0b。
version: 1.1.0
author: agent_created
---

# Jira 工作周报 Skill

## 目标

从 Jira 生成周报，并更新到飞书年度根页面下的月度子页面。

核心流程：

1. 查询当前用户所有非关闭 Jira 工单
2. 按 `createdDate` 分类为“上周遗留问题”和“本周新增问题”
3. 打开飞书年度根页面
4. 查找或创建月度子页面，例如 `叶启航-rayman.ye-2026-08`
5. 写入周报正文，且把每条末尾 Status 标红

## 固定配置

| 配置 | 值 |
|------|-----|
| Jira | `https://ticket.quectel.com` |
| 飞书年度根页面 | `https://quectel.feishu.cn/wiki/PNUMwZUyZieLtEkzRmrcuLDun0b` |
| 月度页面标题 | `叶启航-rayman.ye-2026-MM` |
| Jira 负责人字段 | `cf[12001]` / `Software Development Engineer 软件开发工程师` |
| Chrome debug port | `9222`，可用 `FEISHU_CDP_PORT` 覆盖 |
| Chrome binary | `google-chrome` / `/opt/google/chrome/google-chrome`，可用 `CHROME_BIN` 覆盖 |

## Jira 查询规则

只查当前用户非关闭全集，不按 `updated` 过滤：

```text
cf[12001] = currentUser()
AND status != Closed
AND status != SW_Resolved
AND status != patched
AND status != Resolved
AND status != ST_Closed
ORDER BY created DESC
```

分类规则：

1. `created > 报告结束日`：排除
2. `created >= 报告开始日`：本周新增问题
3. `created < 报告开始日`：上周遗留问题

默认报告周期是北京时间周一到周五。补历史周报时可显式指定开始和结束日期。

## 飞书页面规则

飞书写入默认使用 Chrome debug-port 会话，不要求用户提供飞书 Token。

默认顺序：

1. 先连接当前 `9222` debug-port。
2. 如果连接失败，主动尝试启动 Chrome：

   ```bash
   google-chrome --remote-debugging-port=9222
   ```

3. 如果 Chrome 无法打开、无法连接 debug port、或系统提示 `Missing X server or $DISPLAY`、图形界面/权限问题，停止飞书写入并通知用户处理权限或重新启动 Chrome。

页面规则：

1. 先打开年度根页面。
2. 在左侧页面树下查找当月页面，例如 `叶启航-rayman.ye-2026-08`。
3. 如果不存在，在年度页条目右侧点击 `+` 新建普通 Docs 子页面，并改标题。
4. 不要把周报正文写入年度根页面。
5. 写入完成后确认顶部状态为 `Saved to cloud`。

## 正文格式

```text
时间：（YYYY-MM-DD~YYYY-MM-DD）

上周遗留问题：
1. https://ticket.quectel.com/browse/KEY-1 标题 <红色>Status>

本周新增问题：
1. https://ticket.quectel.com/browse/KEY-2 标题 <红色>Status>
```

Status 是每条记录的最后一个字段，例如 `PENDING`、`Working`、`WAIT FAE INFO`、`waiting for feedback`。必须单独设置为红色字体。

## 执行脚本

```bash
python3 ~/.copilot/skills/weekly-report-skill/scripts/run.py
python3 ~/.copilot/skills/weekly-report-skill/scripts/run.py --start 2026-08-24 --end 2026-08-29
```

脚本负责：

1. 读取 Jira 账号密码，不保存凭据
2. 查询和分类 Jira 工单
3. 生成纯文本正文和带红色 Status 的 HTML
4. 检查 Chrome debug-port 会话；连不上时主动尝试拉起 Chrome
5. 打开飞书年度根页面，并把富文本周报写入剪贴板

进入或创建正确月度页面后粘贴即可保留红色 Status。
