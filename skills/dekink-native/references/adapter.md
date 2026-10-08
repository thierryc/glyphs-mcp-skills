# Native execution contract

Use Glyphs MCP `start_edit_workflow(kind="python_script")` with exact source,
`entrypoint="script"`, `targets=[]`, and parameters. Preparation does not execute.
Dispatch the offered revision-bound Run action under task authorization; retain
the workflow ID and reconcile uncertainty. Scripts never Save or Close.

`native_adapter.py` loads `geometry.py` from `geometry_source`, requiring the
matching UTF-8 `geometry_sha256`. Do not pass stale hashes after changing code.
The script receives the bound `font`, `params`, and `Glyphs` from MCP.

## Default one-run repair

For an authorized fix, use the parameters below with `mode: "repair"` and an
explicit `glyphs` list from the request or complete native selection. The adapter
detects current native output, trials candidates on detached copies and verifies
the whole guarded state before committing entries, all within one invocation.
It needs no external `expected_fingerprint` or separate review workflow.
Optional `selected_ids` narrows the requested joins further. Empty glyph/ID lists
select nothing. Omitted glyph scope is rejected in repair mode.

`mode: "review"` remains read-only. The two-step `review`/`apply` route below
is for explicit preview requests or callers retaining a review for later use.
Do not use that longer route for ordinary repair requests.

Default script output omits individual `samples` arrays but retains peaks,
midpoints, sample counts, factors, source metrics, settings and committed checks.
This prevents a single-glyph report from losing its beginning to MCP truncation.
Set `full_report: true` only when detailed sample output is needed. Large scopes
may still exceed MCP's output limit; reconcile available evidence before proceeding.

## Parameters

```json
{
  "expected_path": "/absolute/font.glyphs",
  "mode": "repair",
  "glyphs": ["a", "b"],
  "threshold_u": 1,
  "tolerance_u": 0.001,
  "sample_intervals": 100,
  "geometry_source": "<exact UTF-8 geometry.py source>",
  "geometry_sha256": "<SHA256 of that source>"
}
```

Omit `glyphs` for discovery across all glyphs; `[]` deliberately selects none.
Intervals must be even, 2–2000, so endpoints and midpoint are sampled.
Reported join IDs are `glyph/pathIndex/nodeIndex`. Unsupported global axis/master
configurations stop before writes. Unsupported glyphs/joins appear in `excluded`.

## Selected apply

Use the same scope and measurement options, `mode="apply"`, the fresh review's
`expected_fingerprint`, and `selected_ids` containing the authorized join IDs.
Omitting selected IDs means every eligible issue in the requested glyph scope;
an empty list means none. The fingerprint guards all recorded master/layer/path
geometry, node attributes, widths, document path, axis and master locations.
It is not a complete document serialization or a permission token.

Apply reruns trials against current guarded state. Proposals are ordered by glyph
and join; shared settings are reused when they already fix another join. Existing
local target-axis entries are never overwritten. Interacting unresolved entries
may therefore be excluded rather than jointly optimized. Final combined checks
abort before live writes if accepted proposals conflict.

## Native settings and assumptions

An `ip` is a font-coordinate pair stored under `hoi[axisTag]` on the lower key
layer's node. Preserve other axes and attributes. `rc`/`rd` and `tl`/`tu`/`al`/`au`
are alternative representations, not additions to `ip`; this adapter does not
generate or qualify those alternatives.

Schema source: pinned [official Glyphs 4 file format](https://github.com/schriftgestalt/GlyphsSDK/blob/0f5422db727b78cb42abfb386f33ae0b382b0c4d/GlyphsFileFormat/GlyphsFileFormatv4.md), `nodeAttr.hoi`.
Private `HOIWindow`/`HOI` evaluator selectors come from prior local qualification
and are checked anew on disposable fonts, not guaranteed by that schema.

Calibration stores a candidate, reads native midpoint output, then updates only
when another write/sample will follow. The report retains the last actually
written value and its actual result. At most eight attempts are made per node;
nonconverging candidates are rejected. Coordinate calibration uses one tenth of
the requested span tolerance, capped at 0.0001u, to accommodate the observed
native float precision. Exact source tangency retains the requested absolute
span tolerance. When a preserved master has a larger tangency residual, the
per-join limit is its maximum endpoint residual plus the requested tolerance.
Reports include `source_metrics`, `verification_limit_u`, and
`absolute_tolerance_met`; every accepted candidate must also meet the detection
threshold. This removes the source-misalignment exclusion without silently
claiming 0.001u absolute tangency. Other joins retain their existing no-regression
check. Folded and degenerate sources are still excluded.

Detection threshold and repair tolerance are distinct. Reruns skip errors at or
below the detection threshold even if above the stricter repair tolerance.
No global minimality, design-quality optimum, extrapolation guarantee, or
general multi-axis support is implied.
