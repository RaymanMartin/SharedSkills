---
name: codex-claude-launching
description: >
  在 Linux 上完整部署 OpenAI Codex CLI 和 Anthropic Claude Code 的一站式 Skill。
  涵盖：Codex 安装与 PATH 修复、Claude Code 安装、Mihomo (Clash Meta) 代理安装与订阅配置、
  代理环境变量写入（让 Codex/Claude 自动走代理）、Mihomo systemd 开机自启、
  节点切换（支持指定地区如 SG/HK/JP）、以及 Clash External UI（metacubexd）图形化面板配置。
  当用户提到"安装 Codex"、"安装 Claude Code"、"配置代理"、"安装 Clash/Mihomo"、
  "Clash 开机启动"、"切换节点"、"Clash 图形界面"、"clash external-ui"、
  "代理 401 报错"、"ETIMEDOUT platform.claude.com"、"无法连接 Anthropic"等场景时，
  必须立即触发本 Skill。即使用户只提到其中一个子步骤，也应触发并引导完整部署流程。
---

# CodexClaudeLaunching — Linux 上部署 Codex & Claude Code 完整指南

本 Skill 覆盖从零开始在 Linux 上部署 Codex CLI 和 Claude Code 所需的全部步骤，
包括网络代理（Mihomo/Clash Meta）的安装与配置。按需执行对应章节即可。

---

## 总体流程

```
1. 安装 Codex CLI
2. 安装 Claude Code
3. 安装 Mihomo 代理（解决网络访问问题）
4. 配置代理环境变量（让 Codex/Claude 走代理）
5. Mihomo systemd 开机自启
6. 切换代理节点
7. 配置 Clash External UI 图形面板
```

---

## 第一步：安装 Codex CLI

### 1.1 通过 npm 安装
```bash
npm install -g @openai/codex
```

### 1.2 检查是否可以直接调用
```bash
which codex && codex --version
```

### 1.3 如果提示 `command not found`，找到实际安装位置并创建软链接

npm 全局包的 bin 目录可能不在 PATH 里（常见于使用 `/opt/node-xxx` 安装的 Node）：

```bash
# 找到 codex 二进制所在位置
find /opt /usr/local -name codex -type f 2>/dev/null
# 例如找到 /opt/node-v22.23.1-linux-x64/bin/codex，则：
sudo ln -s /opt/node-v22.23.1-linux-x64/bin/codex /usr/local/bin/codex
```

验证：
```bash
codex --version  # 应输出 codex-cli x.x.x
```

### 1.4 配置使用 OpenAI（ChatGPT Plus 账号）

编辑 `~/.codex/config.toml`，确保 provider 为 openai（不是 azure）：

```toml
model = "codex-mini-latest"
model_provider = "openai"
model_reasoning_effort = "medium"
```

> **注意**：Codex 登录通过 `codex` 命令启动后交互完成，本 Skill 不处理登录步骤。

---

## 第二步：安装 Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

验证：
```bash
claude --version
```

> **注意**：Claude Code 登录通过 `claude` 命令启动后交互完成，本 Skill 不处理登录步骤。

---

## 第三步：安装 Mihomo 代理

Mihomo 是 Clash Meta 的继承版本，支持 Clash 订阅格式。

### 3.1 下载最新版 Mihomo

```bash
mkdir -p ~/clash && cd ~/clash

# 获取最新版本号
LATEST=$(curl -s https://api.github.com/repos/MetaCubeX/mihomo/releases/latest \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'])")
echo "最新版本: $LATEST"

# 下载并解压（x86_64 架构）
curl -L "https://github.com/MetaCubeX/mihomo/releases/download/${LATEST}/mihomo-linux-amd64-${LATEST}.gz" \
  -o mihomo.gz
gzip -d mihomo.gz
chmod +x mihomo
./mihomo -v   # 验证
```

> ARM 架构请将 `amd64` 替换为 `arm64`。

### 3.2 下载 Clash 订阅配置

**请用户提供自己的 Clash 订阅链接**（从代理服务商网站获取，格式通常为 `https://...`）：

```bash
# 将下面的 URL 替换为你自己的订阅链接
SUBSCRIBE_URL="https://your-subscribe-url-here"

curl -L "$SUBSCRIBE_URL" \
  -H "User-Agent: clash-meta" \
  -o ~/clash/config.yaml

# 验证是否为有效的 YAML 配置
head -5 ~/clash/config.yaml
```

如果输出的是 HTML 而不是 YAML，说明订阅链接需要重新获取或检查。

### 3.3 启动 Mihomo 验证

```bash
cd ~/clash
nohup ./mihomo -d . > clash.log 2>&1 &
sleep 3
tail -10 clash.log  # 应看到 "Mixed(http+socks) proxy listening at: [::]:7890"
```

---

## 第四步：配置代理环境变量

让 Codex 和 Claude Code 通过 Mihomo 代理访问网络：

```bash
cat >> ~/.bashrc << 'EOF'

# Clash/Mihomo proxy
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=localhost,127.0.0.1
EOF

source ~/.bashrc
```

验证代理是否可达：
```bash
curl -s --proxy http://127.0.0.1:7890 --max-time 10 \
  https://platform.claude.com -o /dev/null -w "HTTP: %{http_code}\n"
# 200 或 403 均说明网络可达
```

---

## 第五步：Mihomo systemd 开机自启

### 5.1 创建 systemd service 文件

```bash
sudo tee /etc/systemd/system/mihomo.service << EOF
[Unit]
Description=Mihomo Clash Meta Proxy
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/clash
ExecStart=$HOME/clash/mihomo -d $HOME/clash
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 5.2 启用并启动

```bash
sudo systemctl daemon-reload
sudo systemctl enable mihomo
sudo systemctl start mihomo
sudo systemctl status mihomo  # 确认 active (running)
```

### 5.3 如果 7890 端口冲突（之前手动启动过 mihomo）

```bash
kill $(pgrep -f "mihomo -d") 2>/dev/null
sudo systemctl restart mihomo
```

---

## 第六步：切换代理节点

Mihomo 提供 REST API（默认端口 9090）来切换节点。

### 6.1 查看当前代理组和可用节点

```bash
curl -s http://127.0.0.1:9090/proxies | python3 -c "
import json, sys
data = json.load(sys.stdin)
for name, info in data['proxies'].items():
    if info.get('type') == 'Selector':
        print(f'[组] {name}: 当前={info.get(\"now\",\"\")}')
        # 按地区过滤，如 SG、HK、JP、US
        target = [n for n in info.get('all', []) if 'SG' in n or '新加坡' in n]
        if target:
            print(f'  可用节点: {target[:3]}')
"
```

### 6.2 切换节点示例（以「节点选择」组为例）

```bash
# 切换到新加坡直连节点
curl -X PUT http://127.0.0.1:9090/proxies/%F0%9F%9A%80%20%E8%8A%82%E7%82%B9%E9%80%89%E6%8B%A9 \
  -H "Content-Type: application/json" \
  -d '{"name":"🇸🇬新加坡-A-Direct-1X"}'

# 切回自动选择
curl -X PUT http://127.0.0.1:9090/proxies/%F0%9F%9A%80%20%E8%8A%82%E7%82%B9%E9%80%89%E6%8B%A9 \
  -H "Content-Type: application/json" \
  -d '{"name":"🔮 自动选择"}'
```

> 代理组名称因订阅不同而异，需根据第 6.1 步的实际输出替换。  
> 组名含中文/emoji 时需 URL encode，可用 `python3 -c "import urllib.parse; print(urllib.parse.quote('🚀 节点选择'))"` 获取编码。

### 6.3 测试节点延迟

```bash
NODE_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('🇸🇬新加坡-A-Direct-1X'))")
curl -s "http://127.0.0.1:9090/proxies/${NODE_ENCODED}/delay?timeout=3000&url=http://www.gstatic.com/generate_204"
# 返回 {"delay": 306} 表示延迟 306ms
```

---

## 第七步：配置 Clash External UI（图形化面板）

### 7.1 下载 metacubexd UI

```bash
mkdir -p ~/clash/ui && cd ~/clash/ui
curl -L https://github.com/MetaCubeX/metacubexd/releases/latest/download/compressed-dist.tgz \
  -o ui.tgz
tar -xzf ui.tgz && rm ui.tgz
ls ~/clash/ui  # 应看到 index.html 等文件
```

### 7.2 修改 config.yaml 添加 external-ui 配置

```bash
# 将 external-controller 改为监听 0.0.0.0（可从局域网访问），并添加 ui 路径
sed -i "s|external-controller: '127.0.0.1:9090'|external-controller: '0.0.0.0:9090'\nexternal-ui: '$HOME/clash/ui'\nsecret: ''|" ~/clash/config.yaml

# 验证
grep -E 'external-controller|external-ui|secret' ~/clash/config.yaml
```

### 7.3 重启 Mihomo 使配置生效

```bash
sudo systemctl restart mihomo
```

### 7.4 访问 Web UI

在浏览器打开：
```
http://127.0.0.1:9090/ui
```

局域网其他设备访问（替换为本机 IP）：
```
http://192.168.x.x:9090/ui
```

UI 功能：
- **Proxies**：切换节点、测速
- **Connections**：查看实时连接
- **Rules**：查看分流规则
- **Logs**：实时日志

---

## 常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `codex: command not found` | npm bin 不在 PATH | 创建软链接到 `/usr/local/bin/` |
| `401 Unauthorized` (Azure) | config.toml 配置了 azure provider | 改为 `model_provider = "openai"` |
| `ETIMEDOUT platform.claude.com` | 网络无法直连 | 安装 Mihomo 代理并设置环境变量 |
| 7890 端口已占用 | 手动启动了旧进程 | `kill $(pgrep -f "mihomo -d")` 后重启 service |
| config.yaml 下载得到 HTML | Cloudflare 拦截 | 加 `-H "User-Agent: clash-meta"` 参数 |
| UI 无法访问 | external-controller 绑定 127.0.0.1 | 改为 `0.0.0.0:9090` |
