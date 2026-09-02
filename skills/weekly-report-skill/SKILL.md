---
name: weekly-report-skill
description: >
  自动生成并更新飞书周报。从 Jira 拉取当前用户非关闭 Issues，按 createdDate 区分
  “上周遗留问题”和“本周新增问题”，在飞书年度页下维护月度子页面。
  正文包含时间、分类、Jira URL、标题和 Status；每条末尾 Status 必须红色标识。
  默认先连接 Chrome debug-port；连不上时主动尝试拉起 Chrome。如果 Chrome 无法打开或需要权限，通知用户。
---

# Weekly Report Skill

## 功能

从 Jira 生成周报正文，并更新到飞书年度页下的月度子页面。

年度根页面：

```text
https://quectel.feishu.cn/wiki/PNUMwZUyZieLtEkzRmrcuLDun0b
```

月度页面标题：

```text
叶启航-rayman.ye-2026-MM
```

## 流程

1. 输入 Jira 账号密码，凭据不落盘。
2. 查询当前用户所有非关闭 Jira 工单。
3. 按 `createdDate` 分类：报告周期内创建的是“本周新增问题”，报告周期前创建的是“上周遗留问题”。
4. 连接 Chrome debug port，默认端口 `9222`；连不上时主动尝试拉起 Chrome，再打开飞书年度根页面。
5. 查找或创建当月子页面。
6. 写入正文，并把每条最后的 Status 字段单独标红。
7. 确认飞书显示 `Saved to cloud`。

如果 Chrome 无法打开、无法连接 debug port、或系统要求图形界面/权限，例如 `Missing X server or $DISPLAY`，停止写入并提示用户处理。

## 输出格式

```text
时间：（YYYY-MM-DD~YYYY-MM-DD）

上周遗留问题：
1. https://ticket.quectel.com/browse/KEY-1 标题 <红色>Status>

本周新增问题：
1. https://ticket.quectel.com/browse/KEY-2 标题 <红色>Status>
```

Status 示例：`PENDING`、`Working`、`WAIT FAE INFO`、`waiting for feedback`。

## 执行脚本

```bash
python3 ~/.copilot/skills/weekly-report-skill/scripts/run.py
python3 ~/.copilot/skills/weekly-report-skill/scripts/run.py --start 2026-08-24 --end 2026-08-29
```

脚本会生成纯文本和带红色 Status 的富文本，并把富文本放入剪贴板。进入或创建正确月度页面后粘贴即可保留红色样式。
