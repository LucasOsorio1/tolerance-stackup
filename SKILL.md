---
name: tolerance-stackup
license: MIT
description: Calculates mechanical tolerance stack-ups, i.e. whether parts will still fit when each one is made slightly off-size. Builds the dimension chain (loop diagram) with the user, then runs worst-case, RSS, mean-shift, and Monte Carlo analyses with a bundled script and reports the gap range, predicted reject rate, which tolerances dominate, and how far each could be tightened or loosened. Use this whenever someone asks if parts will fit, about clearance, interference, press fits, gaps, stacked or accumulated tolerances, tolerance analysis, worst case vs RSS, whether an assembly will go together, fit between 3D-printed parts, or how to choose tolerances for a drawing, even if they never say "stack-up". Handles 1D linear stacks (plus simple non-linear cases via sensitivity coefficients) and flags 2D/3D problems that need dedicated tools.
---

# Tolerance Stack-Up

Every part comes out a little off its nominal size. This skill answers whether those small errors, added up along a chain of parts, still leave a working gap, and which tolerance to change if they don't.

## Ground rules

- **Get the chain right before doing math.** Wrong answers almost always come from a missing dimension or a flipped sign, not from arithmetic. Confirm the chain with the person first.
- **Let the script do the arithmetic.** Mental math on square roots and unequal tolerances goes wrong quietly. Run the script, even for two parts.
- **Every number you quote comes from a script run.** If you want a figure the report didn't print (a re-centered nominal, a changed tolerance, "how often is it below X"), edit the chain or spec and rerun. Don't work it out by hand.
- **Only worst case is a guarantee.** RSS, mean-shift, and Monte Carlo results are estimates that depend on assumptions. Say which ones every time.
- **Never invent a tolerance silently.** If a value is missing, ask. If you must assume one, label it as an assumption in the report.
- **Check both ends of the gap.** Too loose fails too: rattle, backlash, an under-squeezed seal, a press fit that slips.

## Workflow

1. **Build the chain.** Read `references/building-the-chain.md`. Show the person a text loop diagram (signs, nominals, tolerances, spec) and ask whether every part touches the next and anything is missing. Ask what happens if it doesn't fit and how the parts are made. Those two answers decide the method.
2. **Write the chain file.** `python3 scripts/stackup.py --template` prints the format. Input rules that prevent the common errors:
   - `minus` keeps its sign as on the drawing: `+0.3/-0.1` is `"plus": 0.3, "minus": -0.1`. Use `"tol"` for symmetric ± and `"limits"` for min/max dimensions.
   - `dir` is +1 if the dimension opens the gap and −1 if it closes it. Use `sensitivity` for lever ratios or linearized non-linear geometry.
   - `dist`: `normal` (default), `triangular`, or `uniform`. Use uniform for unknown processes such as hobby 3D printing.
   - `mean_shift` (0–1): how far off-center a process may sit, as a fraction of its tolerance.
   - Measured process data beats assumptions: add `sigma` and/or `process_mean` for any dimension that has it.
3. **Run it** from this skill's folder (or with the script's full path):
   `python3 scripts/stackup.py chain.json --plot stackup.png`
   Include the plot when a picture of the distribution will help the person. Skip it for a quick yes/no.
4. **Interpret.** `references/methods.md` covers which method's verdict to lead with (section 4), what the numbers do and don't promise (section 5), and the mistakes to rule out (section 6). Read the section you need, not the whole file.
5. **2D questions:** for "will the bolts go through?", use the fastener checks in `references/methods.md` section 7. Other 2D/3D stacks (interacting angles, datum schemes, edge alignment) are out of scope: say so rather than forcing a 1D answer.

## Report format

Open with a one-line answer: does it fit, and by which standard (e.g. "Fits with 99.7% confidence under RSS, but not guaranteed: worst case allows interference").

Then:
- **The chain**: the loop diagram you calculated with, so they can spot a wrong input.
- **Results**: a table of method, gap range, and pass/fail against the spec.
- **Reject rate** (if there's a spec): the Monte Carlo and RSS estimates, as "about N per million".
- **What drives it**: the one or two dimensions with the largest share.
- **What to change**: from the script's allocation section, which tolerance to tighten and to what, and anything that could be loosened to save cost. If the mean gap itself is off, a nominal has to change.
- **Assumptions**: distribution, independence, mean shift, anything you assumed.

Use the person's units. Match depth to the person: a hobbyist wants "make the hole 0.2 mm bigger"; an engineer wants the numbers and assumptions.

## Files

| File | Read it when |
|---|---|
| `references/building-the-chain.md` | building or checking the chain, or 3D-printed parts |
| `references/methods.md` | choosing a method, wording results, GD&T, or 2D/3D questions |
| `scripts/stackup.py` | run it (`--help`, `--template`); only read the source if it errors |
