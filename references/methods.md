# Stack-up methods: formulas, assumptions, and how to talk about results

Primary source: F. Scholz, *Tolerance Stack Analysis Methods*, Boeing Information & Support Services, 1995 (faculty.washington.edu/fscholz/Reports/isstech-95-030.pdf). The worked bearing example and the "common mistakes" list follow B. O'Neill, *Tolerance Stack Up Analysis: Worst Case vs RSS Methods*, Wevolver, 2026.

## Contents
1. Notation
2. The methods, roughly from most to least conservative
3. Distribution inflation factors
4. Choosing a method
5. Saying results honestly
6. Common mistakes
7. Beyond a straight 1D stack

## 1. Notation

The gap is G = a1·L1 + a2·L2 + … + an·Ln. Each Li has a mean and a ± tolerance Ti; ai is +1 if the dimension opens the gap and −1 if it closes it. For a non-linear function, ai is the partial derivative of the gap with respect to Li at nominal (Scholz §2). The script calls this the `sensitivity`.

## 2. The methods, roughly from most to least conservative

(The order can flip: on two-part chains Bender's result exceeds worst case. The script flags any statistical result wider than worst case.)

| Method | Formula | Holds when | Result means |
|---|---|---|---|
| Worst case | Σ \|ai\|·Ti | every part is in tolerance (inspected) | **guaranteed** range |
| Bender RSS | 1.5 × √Σ(ai·Ti)² | the stated tolerances are really ±2σ, not ±3σ | 99.73% estimate with a safety factor |
| Mean-shift model | Σ ηi\|ai\|Ti + √Σ((1−ηi)·ci·ai·Ti)² | each process may sit off-center by up to ηi·Ti, with Cpk ≥ 1 | at least 99.73% |
| RSS | √Σ(ci·ai·Ti)² | parts are centered, independent, and Ti = 3σ | 99.73% of assemblies |
| Monte Carlo | simulate many assemblies | the distributions you chose are right | an estimated reject rate |

Notes from Scholz:
- If worst case passes, you're done. If plain RSS fails, no other statistical method will rescue it: tighten tolerances or change the design.
- The mean-shift model is worst case at η = 1 and plain RSS at η = 0. η = 0.10–0.30 is common; η = 0.20 is the script's default and a defensible conservative choice when there's no process data.
- For two parts, Bender's 1.5 factor gives a *larger* result than worst case, so don't use it on very short chains.
- RSS's 99.73% assumes centered, normal, independent parts with Ti = 3σ. In practice assemblies vary more than plain RSS predicts.

## 3. Distribution inflation factors (ci)

Use these only when there's a reason (data or a known process behavior), not as decoration. The script supports the first three.

| Distribution over ±T | ci | Typical cause |
|---|---|---|
| normal (T = 3σ) | 1.000 | stable, centered process |
| triangular | 1.225 | parts cluster toward the middle |
| uniform | 1.732 | tool wear sweeping the range; unknown process (most conservative symmetric choice) |
| elliptical | 1.5 | |
| trapezoidal (flat to k·T) | √(3(1+k²)/2) | |

For a hobby 3D printer or any process with no data, **uniform** is the honest default.

## 4. Choosing a method

- **Safety-critical, low volume, or must-assemble-every-time** → judge by worst case. Statistical results are informational only.
- **Production volume with process data** → enter each measured `sigma` (and `process_mean` if it's off-center) in the chain file. Statistical methods then use the real spread and center, while worst case still uses the drawing tolerances. From a Cpk report, σ = (distance from mean to nearest limit) / (3 × Cpk).
- **No process data, moderate volume** → the mean-shift model with η = 0.2, and say it's an assumption.
- **Non-normal or mixed distributions, or you need a reject rate** → Monte Carlo.
- **Short chains (2–3 parts)** → statistical methods barely help; worst case is usually the right call.

## 5. Saying results honestly

- Only worst case is a guarantee. Phrase statistical results as estimates under stated assumptions, e.g. "about 1 in 10,000 assemblies would be too tight, if the parts are centered and independent."
- "Zero failures in the simulation" means fewer than about one in the sample count, not zero.
- Always check **both** ends of the gap: maximum-gap failures (rattle, backlash, under-compressed seals) are as real as interference.
- If the result depends on an assumption you made (distribution, η, a missing tolerance), list it, and say what data would replace it.

## 6. Common mistakes (catch these before calculating)

- **Mixed tolerance forms**: unequal tolerances not converted to mean ± T. A 10.0 +0.3/−0.0 hole is 10.15 ± 0.15. The script does this, but only if `minus` carries its sign.
- **Forgotten general tolerances**: dimensions with no tolerance still inherit the title-block or ISO 2768 general tolerance, and they still stack.
- **Assuming independence across identical parts**: two bearings from the same lot share a mean shift. Consider a mean shift for them, or treat them worst case.
- **Assembly-induced variation**: hole-to-fastener slop, joint compliance, and press-fit deformation don't appear on any drawing but belong in the chain.
- **Temperature**: ΔL = α·L·ΔT. A 200 mm aluminum part moves about 0.1 mm over 20 °C, which can exceed the whole stack. Add it as a dimension if the assembly sees temperature swings.
- **Statistical claims from worst-case inputs**: GD&T zones and inspected limits aren't distributions. Don't quote a 99.73% yield from them without saying so.

## 7. Beyond a straight 1D stack

- **GD&T in a 1D stack**: a diametral position tolerance Ø0.4 contributes ±0.2. With an MMC modifier, use the MMC value for worst case and model the bonus tolerance separately for statistical work. Orientation and form controls depend on the datum scheme. Treat them conservatively and flag them.
- **Angles and non-linear geometry**: linearize with sensitivity coefficients (partial derivatives at nominal) only if the variation is small relative to the geometry. Scholz notes linearization fails at points like a hole's true position at the origin.
- **Bolt patterns (the most common 2D question)**: ASME Y14.5 (Nonmandatory Appendix B) gives worst-case checks that answer "will the fasteners go through?" without a stack calculation. H is the smallest (MMC) clearance-hole diameter and F the largest (MMC) fastener diameter.
  - *Floating fastener* (clearance holes in every part, e.g. bolt and nut): each part's position tolerance at MMC can be up to **T = H − F**.
  - *Fixed fastener* (threaded or pressed into one part): **T₁ + T₂ = H − F**, split between the two parts. The tapped hole usually needs a projected tolerance zone.
  - These assume position tolerances at MMC, perpendicular holes, and the parts' datums lined up. If that isn't the case, or the question is about how the plates' edges line up after assembly, it's a true 2D/3D problem.
- **Other 2D/3D stacks** (compound angles, interacting datums, edge alignment of bolted parts) are beyond this skill's calculator. It is 1D only: it can't run a Monte Carlo on a hole pattern, so don't offer to. Say so, and point to Monte Carlo on the real geometry or dedicated tools such as CETOL 6σ or 3DCS.
