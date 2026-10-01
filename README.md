# Tolerance Stack-Up

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that answers one question: **will these parts still fit when each one is made slightly off-size?**

It builds the dimension chain with you, runs the numbers with a bundled script, and reports the gap range, the predicted reject rate, which tolerance matters most, and how far each could be tightened (or loosened to save cost).

## What you get

For a chain of parts it reports:

- **Five methods side by side:** worst case, RSS, a mean-shift model, Bender RSS, and a 200,000-assembly Monte Carlo
- **Pass/fail against your spec** at *both* ends of the gap (too tight and too loose)
- **Predicted out-of-spec assemblies** per million
- **What drives the stack:** each dimension's share of the variation
- **Tolerance allocation:** the largest tolerance each top contributor could have
- **Assumptions to challenge**, listed every time

Example, a bearing stack where the ring clearance must stay between 0.05 and 0.70 mm:

```
  method                                     +/- T  gap range             verdict
  Worst case                                  0.45  -0.05 to 0.85         FAIL
  RSS                                       0.2398  0.1602 to 0.6398      PASS
  Mean-shift model (eta=0.20)               0.2818  0.1182 to 0.6818      PASS
  Bender RSS (1.5 x assumed tolerances)     0.3597  0.0403 to 0.7597      FAIL
  Monte Carlo (200,000 samples)          sd 0.0798  0.1605 to 0.6398      (99.73% interval)
```

Only worst case is a guarantee. The skill labels everything else as an estimate and states the assumptions behind it.

## Install

**Claude.ai (web or desktop):** turn on *Code execution and file creation* under **Settings → Capabilities**, then go to **Settings → Capabilities → Skills**, choose **Upload skill**, and pick `tolerance-stackup.skill` from the [latest release](../../releases/latest). If the upload dialog doesn't accept `.skill`, rename the file to `.zip`.

**Claude Code:** clone this repo into your skills folder.

```bash
git clone https://github.com/LucasOsorio1/tolerance-stackup ~/.claude/skills/tolerance-stackup
```

On Windows the folder is `%USERPROFILE%\.claude\skills\`.

## Try it

> Shaft assembly: housing bore depth 52.40 ±0.20, two bearings 15.00 ±0.05 each, spacer 20.00 ±0.10, retaining ring 2.00 ±0.05. Ring clearance has to stay between 0.05 and 0.70 mm. Will this work, and what should I change?

> im 3d printing a box with a lid. the lid's lip is 50mm and the box opening is 50.4mm. my printer is roughly ±0.2mm. will the lid fit or be too tight or loose?

> two aluminum plates bolted together with M6 bolts through 6.6mm clearance holes. position tolerance on the holes is ø0.2 on both plates. will the bolts always go through?

## What it handles

- 1D linear stacks, with unequal tolerances (`25 +0.1/-0.3`), limit dimensions, and sensitivity coefficients for lever ratios or linearized geometry
- Normal, triangular, and uniform distributions (uniform is the honest default for processes with no data, like hobby 3D printing)
- Your own **measured process data** (`sigma`, `process_mean`) for the statistical methods
- Bolt-pattern questions ("will the bolts go through?") using the ASME Y14.5 floating- and fixed-fastener checks
- 3D-print notes: FDM holes tend to print undersized and outside walls oversized, so measure both

## What it doesn't handle

True 2D and 3D stacks (interacting angles, datum schemes, edge alignment of bolted parts). The skill says so instead of forcing a 1D answer. For those, use Monte Carlo on the real geometry or dedicated tolerance software. Results are estimates to support a design decision, not an engineering sign-off, so verify safety-critical fits independently.

## How it works

| File | Purpose |
|---|---|
| `SKILL.md` | Short router: ground rules, workflow, report format |
| `references/building-the-chain.md` | How to build and check the dimension chain, plus 3D-printing notes |
| `references/methods.md` | Formulas, assumptions, choosing a method, GD&T and fastener checks |
| `scripts/stackup.py` | The calculator |

Run the script yourself (Python 3.9+, standard library only; `matplotlib` is optional for `--plot`):

```bash
python3 scripts/stackup.py --template > chain.json    # example input
python3 scripts/stackup.py chain.json --plot stackup.png
```

On Windows use `python` or `py` instead of `python3`. Input is JSON or CSV. `minus` keeps its sign as on the drawing, so `10.0 +0.3/-0.1` is `"plus": 0.3, "minus": -0.1`, and `dir` is `+1` if a dimension opens the gap and `-1` if it closes it.

## Sources

- F. Scholz, *Tolerance Stack Analysis Methods*, Boeing Information & Support Services, 1995: the worst-case, RSS, Bender, and mean-shift formulas and distribution factors
- B. O'Neill, *Tolerance Stack Up Analysis: Worst Case vs RSS Methods*, Wevolver, 2026: the worked bearing example used as a test case, and the common-mistakes list
- ASME Y14.5 fastener formulas, as summarized in secondary sources (the standard itself is paywalled)

## Tests

```bash
python3 evals/test_stackup.py
```

18 regression tests check the script against the published example and edge cases (asymmetric tolerances, floating-point limits, measured data, bad input). `evals/evals.json` holds four end-to-end prompts with the results each should produce.

## License

[MIT](LICENSE.txt). Not affiliated with ASME, Boeing, or Wevolver.
