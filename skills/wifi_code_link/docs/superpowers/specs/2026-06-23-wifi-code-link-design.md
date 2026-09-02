# wifi_code_link Design

## Problem

Create a local skill named `wifi_code_link` that traces Android Wi-Fi code call chains with a Wi-Fi expert mindset. The first version focuses on the **SAP hotspot enable flow** and must analyze the chain from **Settings** down through **Framework / Connectivity / Wifi module / HAL / Kernel / Driver initialization**, then emit a **Markdown report** with **key functions**, **function meaning**, **Mermaid sequence diagram**, and **Mermaid state diagram**.

The skill must work against an arbitrary Android source tree while defaulting to:

`/home/quectel/HardDisk3/Yd16/sm6225_sm6115_qcm2290_android16.0_ba04_r003_yd`

## Goals

1. Accept a source root and a target flow, defaulting to SAP hotspot startup.
2. Trace code by layer instead of producing a flat symbol dump.
3. Explain each key function in context: why it matters and what the next hop is.
4. Generate a Markdown artifact under a fixed documentation root organized by skill name.
5. Include Mermaid diagrams for both timing and SAP-related state transitions.

## Non-Goals

1. Do not hardcode one static call chain into the skill output.
2. Do not cover STA, generic Wi-Fi switch, or all tethering variants in v1.
3. Do not depend on custom parsers or heavyweight indexing scripts in v1.

## Recommended Architecture

Use a **prompt-first skill** with a small set of reference documents:

1. `SKILL.md`
   - Trigger phrases
   - Input contract
   - Layer-by-layer tracing workflow
   - Output rules and Markdown structure
2. `references/layer-map.md`
   - Canonical layer order
   - Typical entry classes and likely search anchors
   - Notes on vendor forks and path variants
3. `references/report-template.md`
   - Required report sections
   - Mermaid formatting skeletons
   - Evidence checklist

This keeps the skill flexible across code drops while still making output consistent.

## Runtime Flow

1. Normalize inputs
   - `repo_root`
   - `target_flow` (default `sap_open`)
   - `output_file` (default `wifi_code_link_sap_open.md`)
2. Build the tracing scope by layer
   - Settings
   - Framework API / binder boundary
   - Connectivity / tethering handoff where applicable
   - Wifi service internals
   - HAL / hostapd control path
   - Kernel / driver bring-up path
3. Extract evidence
   - Key function names
   - Source file paths
   - Function meaning
   - Next-hop call
   - State changes
4. Compose report
   - Summary
   - Key-function table
   - Sequence diagram
   - State diagram
   - Evidence section
   - Variant notes
5. Write the Markdown file into `/home/quectel/Work/CopilotDoc/wifi_code_link/` and print a short summary to terminal.

## Initial SAP Tracing Rule Set

The v1 skill should instruct the agent to start from the concrete hotspot UI path seen in this codebase and then trace downward. Current anchor examples already verified in the target source tree include:

- `Settings`: `WifiTetherPreferenceController`
- `Framework API`: `WifiManager.startTetheredHotspot(...)`
- `Wifi service`: `WifiServiceImpl.startTetheredHotspot(...)`
- `Wifi service internal`: `WifiServiceImpl.startTetheredHotspotInternal(...)`
- `Mode orchestration`: `ActiveModeWarden.startSoftAp(...)`
- `Soft AP manager`: `SoftApManager.startSoftAp()`
- `Native bridge`: `WifiNative.startSoftAp(...)`
- `HAL / hostapd`: `HostapdHal` and lower layers

The skill must treat these as **search anchors**, not unconditional truth, and continue to follow real callsites in the provided tree.

## Output Format

The generated Markdown document must contain these sections in order:

1. `# Summary`
   - What flow was traced
   - Entry point
   - Final bring-up boundary reached
   - Notable branch / vendor specifics
2. `# Layered Key Functions`
   - Table columns:
     - Layer
     - Function
     - File
     - Meaning
     - Next Hop
3. `# Sequence Diagram`
   - `mermaid`
   - `sequenceDiagram`
   - Participants grouped by layer, e.g. `Settings -> Framework -> Connectivity -> Wifi -> HAL -> Kernel/Driver`
4. `# SAP State Machine`
   - `mermaid`
   - `stateDiagram-v2`
   - Focus on SAP enable path and its key transitions / failure exits
5. `# Source Evidence`
   - File paths and symbol locations backing each hop
6. `# Variants and Gaps`
   - Vendor divergence
   - Unresolved jumps
   - Places where the chain leaves Java and enters native / kernel space

## Analysis Rules

1. Prefer tracing the real invoking chain over listing all matching symbols.
2. Each layer must identify both:
   - the primary entry function
   - the decisive handoff into the next layer
3. If multiple candidate branches exist, keep the mainline chain first and list side branches separately.
4. When the chain crosses language boundaries, explicitly state the boundary:
   - Java -> JNI / binder / HIDL / AIDL / native daemon / kernel interface
5. If an exact lower-layer hop cannot be resolved from source alone, mark it as unresolved instead of guessing.
6. Sequence diagrams should prioritize signal over completeness; only keep the functions needed to explain the bring-up.
7. State diagrams should model state transitions, not merely restate function order.

## Error Handling

1. If the provided root path does not exist, stop with a clear error.
2. If a layer path is absent in the given tree, note it and continue with the remaining reachable layers.
3. If the SAP entry path differs from the default anchors, switch to the discovered path and document the deviation.
4. If the report file already exists, overwrite only when explicitly instructed by the caller; otherwise write a timestamped variant.

## Validation Expectations

The skill should self-check before finishing:

1. The report is valid Markdown.
2. Both Mermaid blocks are present.
3. Every key-function row has a file path and meaning.
4. The report names any unresolved cross-layer gaps explicitly.

## Open Decisions Resolved

1. Skill location: `~/.agents/skills/wifi_code_link`
2. Source root behavior: caller-supplied root with the provided Android tree as default
3. Delivery shape: skill defines the analysis workflow; the chain is discovered from source at runtime
4. Output mode: write a Markdown file in the working directory and print a concise terminal summary
5. Output directory: `/home/quectel/Work/CopilotDoc/wifi_code_link/`
6. v1 scope: SAP hotspot enable chain plus SAP-related state machine only
