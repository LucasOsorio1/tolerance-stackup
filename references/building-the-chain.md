# Building the dimension chain (the step most stack-ups get wrong)

The math is easy. Most wrong answers come from a wrong chain: a missing dimension, a flipped sign, or mixed units. Build and confirm the chain with the person before you calculate anything.

## Steps (adapted from O'Neill, Wevolver 2026, and Scholz 1995)

1. **Define the requirement.** Name the gap and what "good" means at **both** ends, e.g. "ring clearance must stay between 0.05 and 0.70 mm". If they only give one limit, ask whether the other end matters (rattle, backlash, seal squeeze).
2. **Draw the loop.** Start at one side of the gap, go part to part through surfaces that actually touch, and end at the other side. Every dimension you cross is in the stack, and nothing else is.
3. **Assign directions.** Pick which way positive gap points. A dimension that makes the gap bigger gets dir +1; one that makes it smaller gets −1. Sanity check: the nominal gap from the chain should match the design intent.
4. **Convert every tolerance to the same form.** Write minus with its sign (`+0.3/-0.1` → plus 0.3, minus −0.1). Limit dimensions go in as `limits`. Untoleranced dimensions get the drawing's general tolerance.
5. **Translate geometric controls** (see `methods.md` section 7).
6. **Use real process data where you have it** instead of assuming the tolerance band is ±3σ.

## Text loop diagram (show this to the person before calculating)

```
  gap = + Housing bore depth   52.40 ± 0.20
        − Bearing 1 width      15.00 ± 0.05
        − Spacer length        20.00 ± 0.10
        − Bearing 2 width      15.00 ± 0.05
        − Retaining ring        2.00 ± 0.05
  nominal gap = 0.40 mm   (must be 0.05 … 0.70)
```

Ask "Does every part in this list touch the next one, and is anything missing?" before running the script.

## Chain mistakes to look for

- **Diameters vs. radii.** Hole minus pin diameter is the *diametral* clearance. If the parts can shift to one side, the side gap is half that. Decide which one the requirement means.
- **A dimension that doesn't touch the loop.** Overall part length when only a shoulder-to-face distance matters.
- **Double counting.** The same feature measured twice from different datums.
- **Dimensioning scheme.** A drawing that chains dimensions end to end stacks differently from one that dimensions everything from a single datum. Use the dimensions as actually toleranced on the drawing, not ones you derive yourself.
- **Mixed units.** Inches and millimeters in one chain. Convert before entering.
- **Parts that float.** Clearance between a fastener and its hole is a contributor of its own, not zero. A common way to model it is 0 ± half the clearance.

## Questions to ask when information is missing

- What's the tolerance on this dimension? (If none, the title-block general tolerance applies.)
- How are these parts made, and how many? This decides the method and the distribution (see `methods.md` sections 3 and 4).
- What's the consequence if it doesn't fit: annoyance, rework, or a safety issue? Safety and must-fit means judging by worst case.

## 3D-printed and hobby parts

- Printers vary with material, nozzle, orientation, and calibration, so there is no universal tolerance number. The reliable approach is to print a test piece, measure a few copies, and use the spread you observe.
- With no measurements, treat printed dimensions as **uniform** over the tolerance you expect, the most conservative symmetric choice.
- On FDM printers, holes commonly come out undersized while outside walls come out slightly oversized, which is why slicers offer separate hole compensation. Measure holes and outside dimensions separately; don't assume one tolerance for both.
- For press fits, the requirement is a *negative* gap (interference) within a range: too little and it's loose, too much and it cracks or won't press. Set both spec limits.
