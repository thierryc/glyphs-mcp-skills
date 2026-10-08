# Catalog submission and examples

Author: Thierry Charbonnel ([thierryc](https://github.com/thierryc)).
License: [Apache-2.0](../LICENSE); attribution and source commit: [NOTICE](../NOTICE).
The skill, scripts, synthetic regression fonts and recorded reports originate in
[dekink-glyphs4 at f6c33d9](https://github.com/thierryc/dekink-glyphs4/tree/f6c33d969732716698e8a10e0714e1ec4b74a118/rebuild/dekink-native).

## Requirements and tested compatibility

- macOS with Glyphs 4 and a separately installed Glyphs MCP v2 connection
  advertising `script.native.v1`. Catalog browsing requires Glyphs MCP 2.0.1
  or later; the native capability check remains mandatory.
- Live interpolation evidence was recorded on Glyphs 4.1.1 build 4108 through
  native MCP Python workflows. Native Python uses the host-provided `objc` and
  Foundation bridge; do not install or execute native scripts in a shell.
- Codex desktop was used for development and native workflows. Its exact client
  version and the MCP version used for historical reports were not recorded;
  compatibility is limited to the recorded host/capability evidence.
- Cursor, Claude Code, ChatGPT and Claude have no recorded client invocation
  tests for this contribution. No compatibility claim is made for them.
- Offline tests require Python 3.11 or later and the standard library only.
  Run `python3 -B -m unittest discover -s tests -v` from this skill folder.

Inputs are an explicitly bound saved font and glyph names or the complete native
selection. Supported geometry has one internal axis, two ordinary masters and
compatible closed line/cubic paths. Outputs identify issues, exclusions, native
settings, verification measurements and save state. See the
[adapter contract](adapter.md) for parameters and scope.

## Example prompts and expected results

1. “Use $dekink-native to review interpolation kinks above 1u in
   `cubic.asymmetric` and `smooth.control` in this saved disposable fixture.
   Leave the font unchanged.”

   Expected: `mode="review"` is restricted to the two named glyphs; report the
   sampled native peak, join ID, exclusions and candidate HOI settings. Preserve
   the live font, master outlines and save state. The clean control gets no
   correction. Recorded review and repeat evidence is retained in
   [six-font-review.json](../results/six-font-review.json) and
   [six-font-rerun.json](../results/six-font-rerun.json).

2. “Use $dekink-native to detect and repair only the selected glyphs in this
   saved disposable Glyphs 4 font. Keep the verified changes without saving.”

   Expected: read the complete native selection, pass exactly those names to
   `mode="repair"`, and perform detection, detached trials, guarded commit and
   native verification in one invocation. Report before/after sampled peaks,
   entry count, midpoint movement, exclusions and that changes are unsaved.
   Preserve masters, widths, node types, smooth flags and unrelated glyphs.
   This entry mode has offline coverage; its end-to-end native qualification
   remains pending. Historical `mode="apply"` evidence does not qualify it.

3. “Tighten the spacing and kerning of AV.”

   Should not invoke this skill: this is a metrics/kerning request, with no
   interpolation-kink review or native HOI repair requested.

These examples specify intended behavior; they are not newly executed client
acceptance tests. [Qualification notes](qualification.md) distinguish recorded
native evidence from pending behavior, including the source-residual policy.
The current six-case saved-file report binds unchanged source/font hashes and
records 6,006 passing samples; it excludes later development glyphs and does
not establish a continuous interpolation or extrapolation bound.

## Resource review and publishing

The `scripts/` folder contains the native adapter, pure candidate geometry,
fixture/qualification helpers and proof rendering. Native helpers require
explicit MCP parameters and do not save or export fonts. Report helpers write
only explicitly provided new report paths; proof rendering writes its recorded
SVG. None are installation hooks. `fonts/` contains synthetic development
fixtures; `results/` preserves their published evidence, including failed and
uncertain attempts. No native workflow needs to run during installation.

This is a folder contribution for maintainer review. After it is merged, the
catalog contribution workflow calls for a separate reviewed registry PR with
the merged full commit and GitHub codeload ZIP SHA-256. The stable community ID
should be `thierryc/dekink-native`, with `compatibleClients: ["codex"]` based on
the evidence above and `bundled: false`. Installing instructions grants no tool
or font-edit permissions.
