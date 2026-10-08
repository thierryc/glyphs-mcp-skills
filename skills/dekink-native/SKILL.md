---
name: dekink-native
description: Detect and repair interpolation kinks in selected Glyphs 4 glyphs through native HOI, preserving master outlines and verifying the result.
license: Apache-2.0
metadata:
  author: thierryc
---

# Native dekink

Use for interpolation-kink review or authorized native HOI repair. For manual
outline editing, spacing, kerning, or multi-axis work, use the relevant workflow.
See [requirements, compatibility and examples](references/catalog.md).

For a repair request, detect, trial, apply and verify in **one native script run**.
Use the bundled adapter as-is; do not assemble an ad hoc repair script.

1. Bind the intended open font through Glyphs MCP and require `script.native.v1`.
   Read complete `context.selectedGlyphs` when the user asks for the selection.
   An explicitly named glyph takes precedence. Pass only those names in `glyphs`;
   never expand a selected-glyph request to the whole font.
2. Follow [the adapter contract](references/adapter.md). Use `mode="repair"`
   for fixes and `mode="review"` for detection or suggestions. Defaults are a 1u
   detection threshold, 0.001u repair allowance, and 101 native sample positions.
   Repair detects first, trials minimal HOI on detached copies, then commits only
   verified entries with endpoint, other-join and interleaved-sample checks.
3. Start one MCP Python workflow and dispatch its offered Run action under the
   user's repair authorization. No separate proposal approval or second review
   workflow is needed. Show the MCP script warning once. If MCP requires a saved
   baseline, reuse applicable save authorization; otherwise request it, explaining
   that MCP saves the whole font. Never bypass a rejected save or uncertain action.
4. Reconcile that workflow until execution finishes. Read its compact report,
   then Keep successful verified changes without saving unless saving is authorized.
   Report affected glyphs, before/after peak, entry count, midpoint movement,
   skipped joins and whether the result is saved. Do not run another repair just
   to confirm success: committed and interleaved native checks already do that.

## Repair behavior

Supported: one internal axis, two ordinary masters, compatible closed line/cubic
paths, including multiple paths. Skip and explain components, extra layers,
open paths, incompatible topology, unsupported segments, folded/degenerate
spans, and existing local target-axis HOI that the candidate family cannot handle.
An excluded join is not evidence of a clean join.

Leave master outlines, widths, node types, smooth flags and unrelated glyphs
unchanged. Small nonzero source tangency residuals are not a repair blocker;
do not align master handles as a prerequisite. Preserve endpoints, report source
residuals and the per-join verification limit, and distinguish that limit from
meeting absolute 0.001u tangency. A repaired peak must also meet the detection
threshold. Details are in the [adapter contract](references/adapter.md).

Try one-node candidates before coordinated neighbors, ordered by entry count
and midpoint movement. This is minimality within the implemented candidate
family, not a global design optimum. Native checks, not candidate mathematics,
determine success; failed commit checks restore this invocation's entries.
Already-correct joins are no-ops. Do not create proof layers or export implicitly.

## Validation

[Qualification notes](references/qualification.md) distinguish tested behavior
from pending coverage. Sampling does not establish a continuous or extrapolation
bound. Retain workflow IDs after uncertainty and reconcile rather than replaying.

Run offline checks with `python3 -B -m unittest discover -s tests -v` from this
skill folder. [geometry.py](scripts/geometry.py) is pure candidate mathematics;
[native_adapter.py](scripts/native_adapter.py) supplies native evidence and writes.
