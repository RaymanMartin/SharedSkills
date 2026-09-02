# Confluence REST API 模板

## 1. 获取子页面列表

判断月度页面是否已存在。

**GET** `/rest/api/content/379073787/child/page?limit=50`

```bash
# agent-browser 方式
agent-browser open "https://knowledge.quectel.com/rest/api/content/379073787/child/page?limit=50"
agent-browser get text
```

**响应结构**：
```json
{
  "results": [
    {"id": "400055033", "title": "叶启航-rayman.ye-2026-07", ...},
    {"id": "403585443", "title": "叶启航-rayman.ye-2026-08", ...}
  ],
  "size": 2
}
```

**判断逻辑**：遍历 `results`，查找 `title` 匹配 `叶启航-rayman.ye-2026-08` 的页面。如果找到，记录 `id`；如果未找到，需要创建。

## 2. 获取页面内容和版本

**GET** `/rest/api/content/<page_id>?expand=body.storage,version`

```bash
agent-browser open "https://knowledge.quectel.com/rest/api/content/400055033?expand=body.storage,version"
agent-browser get text
```

**响应结构**：
```json
{
  "id": "400055033",
  "title": "叶启航-rayman.ye-2026-07",
  "version": {"number": 10, ...},
  "body": {"storage": {"value": "<p>已有内容...</p>", "representation": "storage"}}
}
```

**关键字段**：
- `version.number` — 当前版本号，更新时需 +1
- `body.storage.value` — 当前页面 HTML 内容

## 3. 创建月度页面

**POST** `/rest/api/content`

```bash
agent-browser eval "
(async () => {
  const res = await fetch('https://knowledge.quectel.com/rest/api/content', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      type: 'page',
      title: '叶启航-rayman.ye-2026-08',
      space: {'key': 'SWSZTSMAR'},
      ancestors: [{'id': '379073787'}],
      body: {
        'storage': {
          'value': '<p>月度周报页面</p>',
          'representation': 'storage'
        }
      }
    })
  });
  const data = await res.json();
  document.title = 'API_DONE';
  document.body.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
})()
"
agent-browser wait --text "API_DONE"
agent-browser get text
```

**响应结构**：
```json
{
  "id": "403585443",
  "title": "叶启航-rayman.ye-2026-08",
  "version": {"number": 1},
  ...
}
```

## 4. 更新页面（追加周报）

**PUT** `/rest/api/content/<page_id>`

```bash
# 构造新 body = 新周报 HTML + 已有内容
# version.number 必须 = 当前版本 + 1

agent-browser eval "
(async () => {
  const res = await fetch('https://knowledge.quectel.com/rest/api/content/<PAGE_ID>', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      id: '<PAGE_ID>',
      type: 'page',
      title: '叶启航-rayman.ye-2026-08',
      space: {'key': 'SWSZTSMAR'},
      body: {
        'storage': {
          'value': '<NEW_BODY_HTML>',
          'representation': 'storage'
        }
      },
      version: {'number': <CURRENT_VERSION + 1>}
    })
  });
  const data = await res.json();
  document.title = 'API_DONE';
  document.body.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
})()
"
agent-browser wait --text "API_DONE"
agent-browser get text
```

**注意事项**：
- `version.number` 必须是当前版本号 +1，否则返回 409 冲突
- `body.storage.value` 中的 HTML 特殊字符需正确转义
- 新周报内容应**prepend**到已有内容前面（最新周报在最上方）
- 如果 body 内容很长，考虑将 HTML 拆分为变量拼接

## 5. eval + fetch 模式说明

agent-browser 的 `eval` 命令在浏览器上下文执行 JavaScript，自动携带会话 cookies。由于 `fetch()` 是异步操作，采用以下模式：

```
1. eval 执行 async IIFE，发起 fetch 请求
2. 将结果写入 document.body.innerHTML
3. 设置 document.title = 'API_DONE' 作为完成信号
4. wait --text "API_DONE" 等待完成
5. get text 提取结果
```

**大 body 处理**：

如果 HTML body 超长（超过命令行长度限制），先将 body 写入浏览器全局变量：

```bash
# 步骤1: 设置 body 内容到全局变量
agent-browser eval "window.__body = '<部分1>'"
agent-browser eval "window.__body += '<部分2>'"
# ... 继续拼接

# 步骤2: 使用全局变量发起请求
agent-browser eval "
(async () => {
  const res = await fetch('...', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      ...
      body: {storage: {value: window.__body, representation: 'storage'}},
      ...
    })
  });
  ...
})()
"
```
