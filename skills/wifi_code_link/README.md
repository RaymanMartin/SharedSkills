# wifi_code_link

用于分析 Android Wi-Fi 函数调度链路的本地 skill。

---

## 这个 skill 现在会做什么

升级后，它不再只输出简版链路摘要，而会默认交付 **中文主导的重型 Markdown 文档**，包括：

1. 层级路径说明
2. 按需错误订正
3. 完整调用链
4. 分层关键函数解析
5. Mermaid 时序图
6. Mermaid 分阶段流程图
7. 真实代码状态机图
8. 架构说明
9. 关键源码索引
10. 变体 / 风险点 / 未解析边界

---

## 默认输出路径

`/home/quectel/Work/CopilotDoc/wifi_code_link/`

---

## 支持的典型目标

### 1. `sap_open`

适合分析：

- Settings 如何开启热点
- SoftAP 启动链路
- Hostapd / AP bring-up

### 2. `sta_init`

适合分析：

- WiFi 初始化
- `setWifiEnabled`
- STA 启动与连接

### 3. `wifi_toggle`

适合分析：

- WiFi 开关状态机
- `ActiveModeWarden`
- 模式切换仲裁

---

## 输出语言规则

1. 文档说明、章节、结论默认中文
2. 函数名、类名、接口名保留源码英文

---

## 检索策略

1. 优先按用户给出的参考路径做定点检索
2. 如果用户没给，再按 skill 内置的分层路径检索
3. 默认不以整仓搜索作为第一选择
4. 驱动层默认参考路径为 `target/vendor/qcom/opensource/wlan`

---

## 主要文件

- `SKILL.md`：主执行协议
- `references/layer-map.md`：层级说明与按需订正规则
- `references/report-template.md`：重型中文报告模板
- `references/target-protocols.md`：不同目标链路的专属规则
