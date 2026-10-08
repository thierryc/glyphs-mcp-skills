# Qualification status — 2026-10-08

## Default repair workflow

`mode="repair"` now performs native detection, detached trials and guarded
commit verification in one invocation, using the same trial and commit code as
the existing `apply` route. Explicit glyph scope is required. Default output
omits individual sample arrays while retaining verification summaries, avoiding
the truncation observed during the `to-repair` review. All 16 offline tests pass,
including one-run no-op behavior, scope enforcement and report evidence.
The new entry mode has not been run against the open font; this update did not
change it. Earlier `apply` execution for `to-repair` did pass native committed
and interleaved checks: 67.15017953u before, less than 0.00001663u after, one entry.
See [selected apply evidence](../results/to-repair-selected-apply.json).

## Source-residual policy correction

The selected `repaired/0/1` regression exposed an overly strict exclusion:
the original integer-coordinate masters have tangency residuals of
0.07921540858u and 0.01537540655u. These are real geometric measurements, but
exceeding the 0.001u repair tolerance does not by itself make HOI trials invalid.
The adapter now measures these joins rather than excluding them or requiring
master outline edits. It preserves endpoints and verifies against the larger
source residual plus tolerance (0.08021540858u here), while requiring accepted
spans to meet the detection threshold and retaining other-join regression checks.
Reports distinguish this limit from meeting the absolute 0.001u tolerance.

All 13 offline tests pass, including the original rounded coordinates at 1,001
analytic samples, endpoint preservation, exact-source tolerance, and rejection
of neighboring-join regressions. Analytic sampling is candidate mathematics,
not native verification. Native qualification of this new source-residual
behavior remains pending; the historical native results below do not qualify it.

The original two-glyph cubic regression now passes native review, selected apply, repeat no-op and saved-file verification on Glyphs 4.1.1 build 4108. The five-case regression and its control now also pass selected apply, repeat no-op and 6,006 native saved-file samples; see [six-case report](https://github.com/thierryc/dekink-glyphs4/blob/f6c33d969732716698e8a10e0714e1ec4b74a118/rebuild/SIX-CASE-REPAIR-REPORT.md). A fresh [scoped saved-file verification](../results/six-font-current-saved-verification.json) also passes all 6,006 samples using the current font and scripts, with unchanged regression master geometry. The saved font now includes two later development glyphs, which are outside this six-case qualification; a whole-font check did not pass. Historical report hashes are retained unchanged. The complete behavioral suite remains pending. Use disposable copies outside these tested cases.

## Verified original-font test

The old unrepaired `Dekink-Disposable.glyphs` was opened natively and saved as a separate [working copy](../fonts/Dekink-Previous-Font-Test.glyphs). Native discovery found `kink.test/0/3`; review sampled 101 positions and measured a 38.42606797u peak. One lower-layer join-node `wght/ip` correction reduced the live and interleaved peak below 0.00000704u. Masters, widths, node types, flags and the control were preserved. Repeat detection returned zero issues and zero proposals.

[Saved-file verification](../results/previous-font-saved-verification.json) loaded the saved font natively and tested 1,001 positions per join: 2,002 total. The repaired peak was 0.00000219u and the control peak was 0.00000491u, both below 0.001u. The report binds the saved font, adapter and geometry hashes.

One-entry minimality applies within the implemented candidate family. This candidate moves the midpoint join by 40.94784336u from its linear trajectory. The [native-coordinate proof](../results/previous-font-before-after.svg) exposes that tradeoff; fewer entries alone do not establish better design preservation. See [review](../results/previous-font-review-02.json), [apply](../results/previous-font-apply.json), and [repeat review](../results/previous-font-rerun.json).

## Verified offline

Nine geometry tests pass. They cover analytical tangency and endpoint preservation, strict thresholds, folded/degenerate tangents, invalid geometry, no-op omission, candidate ranking, opposing directions, native precision-floor calibration and the final value after exhausted calibration. Python files parse and skill frontmatter validates. Offline results alone do not qualify native interpolation.

## Retained development failures

This was an informed rebuild in an empty `rebuild/` folder; no old implementation was copied. Prior mathematics, benchmark inputs and native sampling methods were consulted.

[Attempt 01](../results/native-qualification-01.json) failed all nine behavioral tests because of an incorrect master-location selector. It was corrected using the pinned wrapper. [Attempt 02](../results/native-qualification-02.json) failed all nine because detached copies lose their document path. The harness now binds their actual detached identity without weakening the production path guard.

Attempt 03 produced no report and left an uncertain workflow. After the authorized restart, MCP reported `bridge_operation_lost`; its offered outcome acknowledgment was used. The job was not replayed or counted as passing. [Attempt status](../results/native-attempt-status.json) preserves the failure and recovery record.

The original-font test's first review failed an overly strict coordinate calibration threshold. Native floating-point precision prevented 0.000001u convergence. The adapter now uses `min(0.0001, repair_tolerance / 10)` for coordinate calibration, retains the 0.001u native kink tolerance and verifies the last written value. The successful review and all subsequent evidence use the corrected source hashes.

## Pending qualification and boundaries

The full nine-test behavioral suite, rollback, additional axes/attributes, existing-HOI behavior and general interacting-join behavior remain unqualified. `qualify_native.py` supports bounded test subsets and copy-only mode; do not treat its implementation as a pass.

The code handles one axis and two ordinary masters with compatible closed line/cubic paths. Components, extra layers, open paths and incompatible topology are exclusions. It does not overwrite existing local target-axis HOI, globally optimize joins, automatically generate proof layers, or implement rotation/Bézier repairs. Checks cover supported smooth joins, not overall contour aesthetics or excluded joins. Samples do not prove a continuous or extrapolation bound.
