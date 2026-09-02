---
name: git-log-searcher
description: >
  在 Git 仓库中按文件路径和关键字检索提交历史。用户给出一个文件路径，skill 列出该文件的所有 commit；用户再给出关键字，skill 在 commit message 和 diff 内容中双向搜索，并将匹配的 commitId、commit message 和该文件的 diff 输出到 Markdown 文件。
  当用户说"帮我找某个文件的提交"、"搜索 git 历史"、"查找包含某关键字的 commit"、"git log 检索"、"从提交历史里找 XXX"、"哪个 commit 改了 XXX"、"找一下这个文件的变更记录"等类似需求时，必须立即触发本 skill。
---

# Git Log Searcher

按**文件路径 + 关键字**在 git 历史中精准检索提交，并将结果输出到 Markdown 报告。

---

## 工作流程

### 第 1 步：确定仓库路径

检查当前工作目录是否是 git 仓库（`git rev-parse --show-toplevel`）。如果不是，询问用户仓库路径。后续所有 git 命令都在仓库根目录执行。

### 第 2 步：输入目标文件

询问用户要检索的**文件路径**（相对于仓库根目录，如 `drivers/net/wireless/wlan.c`）。

验证文件是否存在于仓库历史中（`git log --oneline --follow -- <file>` 至少返回一行），否则提示重新输入。

### 第 3 步：列出该文件的提交历史

运行：

```bash
git log --follow --oneline --date=short --format="%h  %ad  %an  %s" -- <file>
```

将结果展示给用户，格式如下（让用户对数量有直观感受）：

```
找到 23 条 <file> 的提交记录：
abc1234  2024-03-10  Alice    fix: resolve null pointer in wlan_open
def5678  2024-02-28  Bob      feat: add power save mode
...
```

### 第 4 步：输入关键字

询问用户要搜索的**关键字**（可以是函数名、错误码、特性名等任意文本）。支持用户一次输入多个关键字，用空格分隔，各关键字之间是"或"关系。

### 第 5 步：双向搜索

对每个关键字分别执行两类搜索，然后合并去重：

**搜索 commit message（`--grep`）：**
```bash
git log --follow --grep="<keyword>" --oneline --format="%H" -- <file>
```

**搜索 diff 内容（`-S` pickaxe）：**
```bash
git log --follow -S "<keyword>" --oneline --format="%H" -- <file>
```

将所有匹配的 commit hash 合并、去重，保持按时间倒序排列。

如果关键字包含特殊 shell 字符，需要正确转义。

### 第 6 步：获取每条匹配 commit 的详情

对每个匹配的 commit hash，运行：

```bash
# 提交元信息
git show --no-patch --format="HASH:%H%nSHORT:%h%nDATE:%ad%nAUTHOR:%an%nEMAIL:%ae%nSUBJECT:%s%nBODY:%b" --date=format:'%Y-%m-%d %H:%M:%S' <hash>

# 只输出目标文件的 diff
git show <hash> -- <file>
```

### 第 7 步：生成 Markdown 报告

将结果写入文件 `git-search-<keyword>-<YYYYMMDD_HHMMSS>.md`，保存在**仓库根目录**下。

---

## 输出格式（严格遵守）

```markdown
# Git 提交检索报告

**仓库：** /path/to/repo  
**目标文件：** drivers/net/wireless/wlan.c  
**关键字：** `wlan_open` `null pointer`  
**搜索时间：** 2024-03-15 14:22:08  
**匹配结果：** 共 N 条

---

## 1. abc1234 — fix: resolve null pointer in wlan_open

| 字段 | 内容 |
|------|------|
| Commit ID | `abc1234def5678abc1234def5678abc1234def56` |
| 短 ID | `abc1234` |
| 日期 | 2024-03-10 09:15:33 |
| 作者 | Alice <alice@example.com> |
| 匹配来源 | commit message / diff 内容 / 两者均匹配 |

**Commit Message：**

```
fix: resolve null pointer in wlan_open

When calling wlan_open before initialization completes,
the driver dereferences a null pointer. Add a guard check.
```

**文件变更（drivers/net/wireless/wlan.c）：**

```diff
@@ -128,6 +128,10 @@ int wlan_open(struct net_device *dev)
     struct wlan_priv *priv = netdev_priv(dev);
 
+    if (!priv->initialized) {
+        pr_err("wlan: device not initialized\n");
+        return -ENODEV;
+    }
+
     spin_lock_irqsave(&priv->lock, flags);
```

---

## 2. def5678 — ...

（后续 commit 同样格式）

---

*由 git-log-searcher skill 生成*
```

---

## 注意事项

- **关键字无结果时**：分别告知在 message 中找到 X 条、在 diff 中找到 Y 条，若均为 0 则提示用户换关键字，并建议大小写不敏感搜索（在 `--grep` 加 `-i` 参数，在 diff 中 `-i` 不被支持，可改用 `-G` 加正则）。
- **diff 过大**：单个文件 diff 超过 500 行时，在报告中截断并注明 `（diff 过长，已截断至前 500 行，完整内容见 git show <hash>）`。
- **二进制文件**：如果目标文件是二进制，diff 会显示 `Binary files differ`，在报告中保留该提示即可。
- **文件重命名**：`--follow` 参数会跟踪重命名历史，生成报告时注明文件在某 commit 时的原始路径（可从 `git show` diff header 中读取）。
- **完成后**：告诉用户报告路径，并简要总结（共 N 条匹配、关键字在 message/diff 中各命中多少条）。
