# bt_code_link Design

## Problem

Create a local skill named `bt_code_link` that traces Android Bluetooth code call chains with a Bluetooth expert mindset. The first version focuses on the **BT Enable flow** and must analyze the chain from **Settings** down through **Framework API / BT Framework Module / BT Service APK / BT Stack / BT HAL / Controller**, then emit a **Markdown report** with **key functions**, **function meaning**, **Mermaid sequence diagram**, and **Mermaid state diagram**.

The skill must work against an arbitrary Android source tree while defaulting to:

`/home/quectel/HardDisk3/Yd16/sm6225_sm6115_qcm2290_android16.0_ba04_r003_yd`

## Goals

1. Accept a source root and a target flow, defaulting to BT enable flow.
2. Trace code by layer instead of producing a flat symbol dump.
3. Explain each key function in context: why it matters and what the next hop is.
4. Generate a Markdown artifact under a fixed documentation root organized by skill name.
5. Include Mermaid diagrams for both timing and BT-related state transitions.
6. Support multiple target flows: `bt_enable`, `bt_connect`, `bt_scan`.

## Non-Goals

1. Do not hardcode one static call chain into the skill output.
2. Do not cover all BT profiles or all BLE variants in v1.
3. Do not depend on custom parsers or heavyweight indexing scripts in v1.

## Recommended Architecture

Use a **prompt-first skill** with a small set of reference documents:

1. `SKILL.md`
   - Trigger phrases
   - Input contract
   - Layer-by-layer tracing workflow
   - Output rules and Markdown structure
2. `references/layer-map.md`
   - Canonical layer order for Android Bluetooth
   - Typical entry classes and likely search anchors
   - Notes on vendor forks and path variants
3. `references/report-template.md`
   - Required report sections
   - Mermaid formatting skeletons
   - Evidence checklist
4. `references/target-protocols.md`
   - Per-flow chapter requirements and state machine candidates

This keeps the skill flexible across code drops while still making output consistent.

## Runtime Flow

1. Normalize inputs
   - `repo_root`
   - `target_flow` (default `bt_enable`)
   - `output_file` (default timestamped name)
2. Build the tracing scope by layer
   - Settings / App UI
   - Framework API (android.bluetooth)
   - BT Framework Module (AdapterService, Profile services)
   - BT Service APK (Profile implementations)
   - BT Stack BTIF / BTA / Stack
   - BT HAL (AIDL/HIDL interface)
   - BT Controller / Firmware boundary
3. Extract evidence
   - Key function names
   - Source file paths
   - Function meaning
   - Next-hop call
   - State changes
4. Compose report
   - Summary / overview
   - Layer path explanation
   - Key-function tables per layer
   - Sequence diagram (layered: Settings → Framework → BT → HAL)
   - Phase flow diagrams (≥ 2)
   - State machine diagram (real code only)
   - Architecture explanation
   - Source index table
   - Variant notes
5. Write the Markdown file into `/home/quectel/Work/CopilotDoc/bt_code_link/` and print a short summary.

## BT Layer Reference Paths

| Layer | Path |
|---|---|
| Settings | `qssi16/packages/apps/Settings/src/com/android/settings/bluetooth/` |
| Framework API | `qssi16/frameworks/base/core/java/android/bluetooth/` |
| BT Framework Module | `qssi16/packages/modules/Bluetooth/` |
| BT Service APK | `target/vendor/qcom/opensource/commonsys/packages/apps/Bluetooth/` |
| BT HAL | `target/hardware/interfaces/bluetooth/` |
| BT Stack | `target/vendor/qcom/opensource/commonsys/system/bt/` |

## Initial BT Enable Tracing Rule Set

The v1 skill should instruct the agent to start from the Settings bluetooth UI path and then trace downward. Current anchor examples include:

- `Settings`: `BluetoothEnabler` / `BluetoothDashboardFragment`
- `Framework API`: `BluetoothAdapter.enable()`
- `Framework Service boundary`: `IBluetoothManager.enable()` → Binder → `BluetoothManagerService`
- `BT Module Service`: `AdapterService.enable()`
- `BT Module StateMachine`: `AdapterStateMachine` (USER_TURN_ON)
- `BT Stack JNI`: `btifEnableBluetoothNative()`
- `BT Stack BTIF`: `btif_enable_bluetooth()`
- `BT Stack BTA`: `BTA_EnableBluetooth()`
- `BT HAL`: `IBluetoothHci.initialize()` / `open()`

The skill must treat these as **search anchors**, not unconditional truth, and continue to follow real callsites in the provided tree.

## Output Format

The generated Markdown document must contain these sections in order:

1. `# 概览` (Overview)
   - What flow was traced
   - Entry point
   - Final bring-up boundary reached
   - Notable branch / vendor specifics
2. `# 层级路径说明` (Layer Path Explanation)
3. `# 层级错误订正` (Layer Correction — on demand)
4. `# 完整调用链` (Full Call Chain)
5. `# 关键函数分层解析` (Layered Key Function Analysis)
6. `# Mermaid 时序图` (Sequence Diagram)
7. `# Mermaid 分阶段流程图` (Phase Flow Diagrams — ≥ 2)
8. `# 代码状态机图` (Real Code State Machine — if applicable)
9. `# 架构说明` (Architecture Notes)
10. `# 关键源码索引` (Source Index)
11. `# 变体、风险点与未解析边界` (Variants and Gaps)

## Analysis Rules

1. Prefer tracing the real invoking chain over listing all matching symbols.
2. Each layer must identify both:
   - the primary entry function
   - the decisive handoff into the next layer
3. If multiple candidate branches exist, keep the mainline chain first and list side branches separately.
4. When the chain crosses language boundaries, explicitly state the boundary:
   - Java → JNI → native (BT Stack)
   - BT Stack → AIDL/HIDL → HAL
   - HAL → HCI → BT Controller
5. If an exact lower-layer hop cannot be resolved from source alone, mark it as unresolved.
6. Sequence diagrams must show layered participants: Settings → Framework → BT Framework Module → BT Stack → BT HAL.
7. State diagrams must model real code `StateMachine` state transitions, not function call order.

## Error Handling

1. If the provided root path does not exist, stop with a clear error.
2. If a layer path is absent in the given tree, note it and continue with the remaining reachable layers.
3. If the BT entry path differs from the default anchors, switch to the discovered path and document the deviation.
4. If the report file already exists, overwrite only when explicitly instructed; otherwise write a timestamped variant.

## Validation Expectations

The skill should self-check before finishing:

1. The report is valid Markdown.
2. The sequence diagram and at least two phase flow diagrams are present.
3. Every key-function row has a file path and meaning.
4. The report names any unresolved cross-layer gaps explicitly.
5. State machine diagram (if present) references a real code `StateMachine` class.

## Open Decisions Resolved

1. Skill location: `~/.agents/skills/bt_code_link`
2. Source root behavior: caller-supplied root with the provided Android tree as default
3. Delivery shape: skill defines the analysis workflow; the chain is discovered from source at runtime
4. Output mode: write a Markdown file and print a concise terminal summary
5. Output directory: `/home/quectel/Work/CopilotDoc/bt_code_link/`
6. v1 scope: BT enable chain plus BT-related state machine; connect and scan protocols also defined
