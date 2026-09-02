# JQL 查询模板

## 核心查询：非 CLOSED 全集（按 createdDate 分类）

> **2026-08-11 二次更正**：查询当前用户所有非 CLOSED 状态的工单，不按 `updated` 时间过滤。`updated` 时间会因手动批量更新而集中到当天，导致漏查。正确做法是查非 CLOSED 全集，再按 `createdDate` 分类。

```jql
"Software Development Engineer 软件开发工程师" = currentUser()
AND status != Closed
AND status != SW_Resolved
AND status != patched
AND status != Resolved
AND status != ST_Closed
ORDER BY created DESC
```

> **注意**：此 JQL 不含任何日期过滤条件，返回当前用户名下所有未关闭工单。分类逻辑在下方按 `createdDate` 完成。

**完整查询 URL**（GET 请求，JQL 需 URL 编码）：

```
https://ticket.quectel.com/rest/api/2/search
  ?jql="Software Development Engineer 软件开发工程师" = currentUser() AND status != Closed AND status != SW_Resolved AND status != patched AND status != Resolved AND status != ST_Closed ORDER BY created DESC
  &fields=key,summary,status,created,updated
  &maxResults=200
```

> JQL 中的中文和空格需要 URL 编码（用 Python `urllib.parse.quote()`）。

## 旧版查询（已废弃，仅作参考）

```jql
// 旧版：按 updated 时间范围查询（2026-08-05 版本，已废弃）
"Software Development Engineer 软件开发工程师" = currentUser()
AND updated >= "YYYY-MM-DD"
AND updated < "YYYY-MM-DD"
```

**废弃原因**：`updated` 时间会因用户手动批量更新（如批量改状态）而集中到当天，导致查询结果失真。2026-08-11 实测发现所有工单 updated=08-11（当天手动更新），`updated >= 08-03 AND updated < 08-08` 返回 0 条。

## 分类逻辑

从非 CLOSED 全集中按 `created` 字段分类，三步：

### Step 0: 排除未来工单

```python
# 排除报告周五之后创建的工单（报告周还不存在）
issues = [
    i for i in issues
    if i["fields"]["created"][:10] <= friday
]
```

> 当生成历史周报时，非 CLOSED 全集中可能包含报告周之后新创建的工单，应排除。

### Step 1: 本周新增

```python
monday = "2026-08-03"
friday = "2026-08-07"

new_this_week = [
    issue for issue in issues
    if issue["fields"]["created"][:10] >= monday
    and issue["fields"]["created"][:10] <= friday
]
```

### Step 2: 上周遗留

```python
carried_over = [
    issue for issue in issues
    if issue["fields"]["created"][:10] < monday
]
```

## 辅助查询

### 查看特定工单详情

```jql
key = SWSMAR-5688
```

### 查询已 Closed 的工单（如需追踪已关闭工单）

```jql
"Software Development Engineer 软件开发工程师" = currentUser()
AND status = Closed
AND created >= "2026-08-03"
AND created <= "2026-08-07"
```

### 使用 Jira 内置日期函数（分类时可选）

如果需要在 JQL 层面直接按创建日期分类：

```jql
// 本周新增（JQL 内置函数版）
"Software Development Engineer 软件开发工程师" = currentUser()
AND status != Closed
AND status != SW_Resolved
AND status != patched
AND status != Resolved
AND status != ST_Closed
AND created >= startOfWeek()
AND created <= endOfWeek()
```

```jql
// 上周遗留（JQL 内置函数版）
"Software Development Engineer 软件开发工程师" = currentUser()
AND status != Closed
AND status != SW_Resolved
AND status != patched
AND status != Resolved
AND status != ST_Closed
AND created < startOfWeek()
```

> **注意**：`startOfWeek()` 和 `endOfWeek()` 的行为取决于 Jira 服务器配置的周首日。默认 startOfWeek() = 周一，endOfWeek() = 周日。如需精确到周五，建议使用显式日期。
