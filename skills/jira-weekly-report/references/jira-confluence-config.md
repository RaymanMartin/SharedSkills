# Jira / Confluence 配置详情

## Jira 配置

| 配置项 | 值 |
|--------|-----|
| 服务器地址 | `https://ticket.quectel.com` |
| 登录页 | `https://ticket.quectel.com/login.jspa` |
| REST API 基路径 | `/rest/api/2` |
| 用户追踪字段 | `Software Development Engineer 软件开发工程师`（自定义字段，非标准 assignee） |
| 用户标识 | `rayman.ye@quectel.com`（JIRAUSER26240） |
| "My open issues" 过滤器 ID | 30907 |
| Jira Macro serverId | `64c93c65-d9d2-3802-baea-f7a3f83589c5` |
| Jira Macro server name | `quectel-ticket` |

### Jira 登录方式（实测验证 2026-08-05）

| 方式 | 端点 | 可用性 |
|------|------|--------|
| REST Session API | `POST /rest/auth/1/session` (JSON body) | ✅ 推荐 |
| Web 表单登录 | 表单字段 os_username/os_password | ✅ 可用 |
| Basic Auth | HTTP Header | ✅ curl 后备方案 |

**REST Session API 登录命令**（推荐）：
```bash
agent-browser batch \
  "open https://ticket.quectel.com/login.jspa" \
  "wait 3000" \
  "eval \"fetch('https://ticket.quectel.com/rest/auth/1/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'<邮箱>',password:'<密码>'})}).then(function(r){return r.json()}).then(function(d){document.body.innerText='LOGIN_OK'})\"" \
  "wait 5000"
```

### 关键 API 端点

| 操作 | 方法 | URL |
|------|------|-----|
| 获取当前用户 | GET | `/rest/api/2/myself` |
| 搜索工单 | GET | `/rest/api/2/search?jql=<JQL>&fields=<fields>&maxResults=<n>` |
| 获取工单详情 | GET | `/rest/api/2/issue/<KEY>` |
| 获取收藏过滤器 | GET | `/rest/api/2/filter/favourite` |

### Jira 登录表单结构

登录页 (`/login.jspa`) 表单字段：
- 用户名输入框：`input[name="os_username"]` 或通过 snapshot ref 定位
- 密码输入框：`input[name="os_password"]` 或通过 snapshot ref 定位
- 登录按钮：`input[name="login"]` 或通过 snapshot ref 定位

## Confluence 配置

| 配置项 | 值 |
|--------|-----|
| 服务器地址 | `https://knowledge.quectel.com` |
| REST API 基路径 | `/rest/api/content` |
| 空间 Key | `SWSZTSMAR` |
| 父页面 ID | `379073787` |
| 父页面标题 | `叶启航-rayman.ye-2026` |
| 月度页面命名规则 | `叶启航-rayman.ye-2026-MM`（MM = 01-12） |

### 页面层级

```
智能SoC二部
  └── Framework科
      └── Framework工作周报
          └── Framework周报-2026
              └── 叶启航-rayman.ye-2026 (ID: 379073787)
                  ├── 叶启航-rayman.ye-2026-01
                  ├── 叶启航-rayman.ye-2026-02
                  ├── ...
                  └── 叶启航-rayman.ye-2026-12
```

### 关键 API 端点

| 操作 | 方法 | URL |
|------|------|-----|
| 获取页面 | GET | `/rest/api/content/<id>?expand=body.storage,version` |
| 获取子页面 | GET | `/rest/api/content/<id>/child/page?limit=50` |
| 创建页面 | POST | `/rest/api/content` |
| 更新页面 | PUT | `/rest/api/content/<id>` |

### Confluence 认证

Confluence 与 Jira 不共享 cookie（不同域名：ticket.quectel.com vs knowledge.quectel.com），需分别登录。

**Confluence 登录方式**（实测验证 2026-08-05）：

| 方式 | 端点 | 可用性 |
|------|------|--------|
| Web 表单登录 | `POST /login.action` (表单字段 os_username/os_password) | ✅ 可用 |
| REST Session API | `POST /rest/auth/1/session` | ❌ 返回 HTML，不可用 |

**Web 表单登录命令**：
```bash
agent-browser batch \
  "open https://knowledge.quectel.com/login.action" \
  "wait 3000" \
  "fill input[name=os_username] <邮箱>" \
  "fill input[name=os_password] <密码>" \
  "click input[name=login]" \
  "wait 5000"
```

登录后，浏览器中的 JSESSIONID cookie 对 `knowledge.quectel.com` 域有效，后续 `eval` + `fetch` 调用会自动携带。

## agent-browser 会话管理

| 操作 | 命令 |
|------|------|
| 保存会话 | `agent-browser state save quectel-session` |
| 加载会话 | `agent-browser state load quectel-session` |
| 删除会话 | 删除 state 文件（路径取决于 agent-browser 配置） |

### 会话有效期

- Jira/Confluence SSO 会话通常有效期为数小时到数天
- 如果 `state load` 后访问 API 返回登录页 HTML，说明会话已过期，需重新登录
- 建议每周执行时先验证会话有效性，过期则重新登录

## 迁移到其他用户/环境

迁移时需修改的配置：

1. `USER_FIELD` 中的用户标识（邮箱）
2. `PAGE_PREFIX`（页面标题前缀，包含用户姓名）
3. `PARENT_PAGE_ID`（个人年度页面的 ID）
4. `JIRA_SERVER_ID`（如果 Jira 服务器不同）
