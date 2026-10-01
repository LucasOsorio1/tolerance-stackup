#!/usr/bin/env python3
"""
stackup.py - 1D tolerance stack-up calculator.

Usage
  python3 stackup.py CHAIN.json [--plot hist.png] [--samples 200000] [--seed 1]
  python3 stackup.py CHAIN.csv  [...]
  python3 stackup.py --template            # print an example CHAIN.json

Methods (formulas from Scholz, "Tolerance Stack Analysis Methods", Boeing 1995)
  worst case        T = sum |a_i| T_i                       (guaranteed bound)
  RSS               T = sqrt(sum (c_i a_i T_i)^2)            (99.73% if assumptions hold)
  Bender RSS        T = 1.5 * plain RSS                     (if tolerances are really +/-2 sigma)
  mean-shift model  T = sum eta_i |a_i| T_i + sqrt(sum ((1-eta_i) c_i a_i T_i)^2)
  Monte Carlo       sample every dimension from its distribution, add them up

  a_i = direction (+1 opens the gap, -1 closes it) x sensitivity (default 1)
  c_i = distribution inflation factor: normal 1, triangular 1.225, uniform 1.732
  eta_i = mean shift as a fraction of the tolerance (0 = centered process)

Input: JSON (see --template) or CSV with columns
  name,nominal,plus,minus,dir[,dist][,sensitivity][,mean_shift]
'minus' is the lower deviation WITH its sign as written on the drawing:
  10.0 +0.3/-0.1 -> plus 0.3, minus -0.1;  10.0 +0.3/-0.0 -> plus 0.3, minus 0.
A symmetric tolerance can be given as "tol": 0.05 instead of plus/minus,
or limit dimensions as "limits": [9.98, 10.02].
Measured process data (optional, per dimension): "sigma" (standard deviation)
and/or "process_mean". Statistical methods and Monte Carlo use them; worst case
keeps using the drawing tolerances.

Standard library only; matplotlib is used for --plot if installed.
"""
import argparse
import csv
import json
import math
import random
import sys

C_FACTOR = {"normal": 1.0, "triangular": math.sqrt(1.5), "uniform": math.sqrt(3.0)}

TEMPLATE = {
    "units": "mm",
    "gap": "clearance between retaining ring and bearing face",
    "spec": {"min": 0.05, "max": 0.70},
    "mean_shift": 0.0,
    "dimensions": [
        {"name": "Housing bore depth", "nominal": 52.40, "tol": 0.20, "dir": 1},
        {"name": "Bearing 1 width", "nominal": 15.00, "tol": 0.05, "dir": -1},
        {"name": "Spacer length", "nominal": 20.00, "tol": 0.10, "dir": -1},
        {"name": "Bearing 2 width", "nominal": 15.00, "tol": 0.05, "dir": -1},
        {"name": "Retaining ring thickness", "nominal": 2.00, "tol": 0.05, "dir": -1},
    ],
}


class InputError(Exception):
    pass


def phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fnum(x, units=""):
    s = f"{x:+.4f}".rstrip("0").rstrip(".") if abs(x) < 1e6 else f"{x:+.4g}"
    if s in ("+", "-", "+0", "-0", "-0."):
        s = "0"
    return s + (f" {units}" if units else "")


def plain(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #

def load(path):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        dims = []
        for r in rows:
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            d = {"name": r.get("name") or f"dim{len(dims) + 1}"}
            for k in ("nominal", "plus", "minus", "tol", "sensitivity", "mean_shift"):
                if r.get(k):
                    d[k] = float(r[k])
            if r.get("dir"):
                d["dir"] = int(float(r["dir"]))
            if r.get("dist"):
                d["dist"] = r["dist"].lower()
            dims.append(d)
        return {"dimensions": dims}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize(cfg):
    dims_in = cfg.get("dimensions") or []
    if not dims_in:
        raise InputError("no dimensions given")
    default_eta = float(cfg.get("mean_shift", 0.0))
    out, notes = [], []
    for i, d in enumerate(dims_in, 1):
        name = d.get("name", f"dim{i}")
        if "limits" in d:
            lo, hi = sorted(float(x) for x in d["limits"])
            nominal = float(d.get("nominal", (lo + hi) / 2))
            plus, minus = hi - nominal, lo - nominal
        else:
            if "nominal" not in d:
                raise InputError(f"'{name}': missing nominal")
            nominal = float(d["nominal"])
            if "tol" in d:
                t = abs(float(d["tol"]))
                plus, minus = t, -t
            elif "plus" in d and "minus" in d:
                plus, minus = float(d["plus"]), float(d["minus"])
            else:
                raise InputError(f"'{name}': give tol, plus+minus, or limits")
        if plus < minus:
            raise InputError(f"'{name}': plus ({plus}) is below minus ({minus}). "
                             "Write minus with its sign, e.g. +0.3/-0.1 -> "
                             "plus 0.3, minus -0.1")
        if minus > 0:
            notes.append(f"'{name}': both deviations are positive (+{plus}/+{minus}); "
                         "treated as a unilateral tolerance above nominal. If you "
                         f"meant +{plus}/-{minus}, enter minus as -{minus}")
        direction = d.get("dir", 1)
        if direction not in (1, -1):
            raise InputError(f"'{name}': dir must be +1 (opens the gap) or -1 "
                             "(closes it); use 'sensitivity' for other coefficients")
        sens = float(d.get("sensitivity", 1.0))
        dist = str(d.get("dist", "normal")).lower()
        if dist not in C_FACTOR:
            raise InputError(f"'{name}': dist must be normal, triangular, or uniform")
        eta = float(d.get("mean_shift", default_eta))
        if not 0.0 <= eta < 1.0:
            raise InputError(f"'{name}': mean_shift must be in [0, 1)")
        T = (plus - minus) / 2.0
        mean = nominal + (plus + minus) / 2.0
        sigma = d.get("sigma")
        pmean = d.get("process_mean")
        data = sigma is not None or pmean is not None
        if sigma is not None:
            sigma = float(sigma)
            if sigma < 0:
                raise InputError(f"'{name}': sigma must be positive")
            if dist != "normal":
                raise InputError(f"'{name}': measured sigma implies a normal model; "
                                 "drop dist or sigma")
        if pmean is not None:
            pmean = float(pmean)
            if not (mean - T - 1e-12 <= pmean <= mean + T + 1e-12):
                notes.append(f"'{name}': measured process mean {pmean} is outside its "
                             "tolerance limits; many parts will be out of tolerance")
        # statistical spread and center: measured data wins over assumptions
        T_stat = 3 * sigma if sigma is not None else T
        mean_stat = pmean if pmean is not None else mean
        if data and eta:
            notes.append(f"'{name}': has measured data, so its mean_shift is ignored")
        out.append({"name": name, "nominal": nominal, "plus": plus, "minus": minus,
                    "mean": mean, "T": T, "a": direction * sens, "dir": direction,
                    "sens": sens, "dist": dist, "c": C_FACTOR[dist],
                    "eta": 0.0 if data else eta, "data": data,
                    "T_stat": T_stat, "mean_stat": mean_stat,
                    "shifted": abs(plus + minus) > 1e-12})
    spec = cfg.get("spec") or {}
    smin = spec.get("min")
    smax = spec.get("max")
    if smin is not None and smax is not None and float(smin) > float(smax):
        raise InputError("spec min is larger than spec max")
    return out, (None if smin is None else float(smin),
                 None if smax is None else float(smax)), notes


# --------------------------------------------------------------------------- #
# Math
# --------------------------------------------------------------------------- #

def analyze(dims, spec, samples=200_000, seed=1):
    a = [d["a"] for d in dims]
    T = [d["T"] for d in dims]
    nominal_gap = sum(d["a"] * d["nominal"] for d in dims)
    mean_gap = sum(d["a"] * d["mean"] for d in dims)
    stat_gap = sum(d["a"] * d["mean_stat"] for d in dims)
    any_data = any(d["data"] for d in dims)
    wc = sum(abs(ai) * ti for ai, ti in zip(a, T))
    # Bender's 1.5 covers stated tolerances that are really +/-2 sigma; measured
    # sigmas need no such allowance, so only assumed tolerances are inflated
    bender = math.sqrt(sum((d["a"] * d["T_stat"]) ** 2 if d["data"]
                           else (1.5 * d["a"] * d["T"]) ** 2 for d in dims))
    rss_c = math.sqrt(sum((d["c"] * d["a"] * d["T_stat"]) ** 2 for d in dims))
    any_nonnormal = any(d["dist"] != "normal" for d in dims)
    any_shift = any(d["eta"] > 0 for d in dims)
    eta_default = 0.2

    def mean_shift_T(etas):
        # dimensions with measured data keep eta = 0: their real center is known
        return sum(e * abs(d["a"]) * d["T"] for e, d in zip(etas, dims)) + math.sqrt(
            sum(((1 - e) * d["c"] * d["a"] * d["T_stat"]) ** 2
                for e, d in zip(etas, dims)))

    etas = ([d["eta"] for d in dims] if any_shift else
            [0.0 if d["data"] else eta_default for d in dims])
    ms = mean_shift_T(etas)
    methods = [
        ("Worst case", wc, "guaranteed if every part is inspected in tolerance"),
        ("RSS" + (" (with distribution factors)" if any_nonnormal else ""), rss_c,
         "~99.73% of assemblies, IF parts are centered, independent, and "
         "tolerance = 3 sigma"),
        ("Mean-shift model (eta=" + ("per input" if any_shift else f"{eta_default:.2f}")
         + ")", ms, "at least 99.73%; allows each process to sit off-center by eta x T"),
        ("Bender RSS (1.5 x assumed tolerances)", bender,
         "use if stated tolerances are really +/-2 sigma (measured sigmas "
         "are not inflated)"),
    ]
    rows = []
    for i, (name, t, meaning) in enumerate(methods):
        center = mean_gap if i == 0 else stat_gap
        lo, hi = center - t, center + t
        v = verdict(lo, hi, spec)
        if i > 0 and t > wc + 1e-12:
            v = "n/a: wider than worst case (impossible); use worst case"
        rows.append({"method": name, "T": t, "low": lo, "high": hi,
                     "meaning": meaning, "verdict": v, "exceeds_wc": i > 0 and t > wc + 1e-12})

    # Monte Carlo
    rng = random.Random(seed)
    gaps = []
    for _ in range(samples):
        g = 0.0
        for d in dims:
            if d["dist"] == "normal":
                x = (rng.gauss(d["mean_stat"], d["T_stat"] / 3.0) if d["T_stat"] > 0
                     else d["mean_stat"])
            elif d["dist"] == "uniform":
                x = rng.uniform(d["mean"] - d["T"], d["mean"] + d["T"])
            else:
                x = rng.triangular(d["mean"] - d["T"], d["mean"] + d["T"], d["mean"])
            g += d["a"] * x
        gaps.append(g)
    gaps.sort()
    n = len(gaps)
    mc_mean = sum(gaps) / n
    mc_sd = math.sqrt(sum((g - mc_mean) ** 2 for g in gaps) / (n - 1))
    q = lambda p: gaps[min(n - 1, max(0, int(p * n)))]
    smin, smax = spec
    eps = 1e-9 * max(1.0, abs(mean_gap))
    below = sum(1 for g in gaps if smin is not None and g < smin - eps)
    above = sum(1 for g in gaps if smax is not None and g > smax + eps)
    mc = {"samples": n, "mean": mc_mean, "sd": mc_sd, "min": gaps[0],
          "max": gaps[-1], "p00135": q(0.00135), "p99865": q(0.99865),
          "below": below, "above": above, "gaps": gaps}

    # normal-theory out-of-spec estimate from RSS
    sigma = rss_c / 3.0
    est = None
    if sigma > 0 and (smin is not None or smax is not None):
        pb = phi((smin - stat_gap) / sigma) if smin is not None else 0.0
        pa = 1 - phi((smax - stat_gap) / sigma) if smax is not None else 0.0
        est = pb + pa

    # contributions
    contrib = []
    for d in dims:
        wc_share = abs(d["a"]) * d["T"] / wc if wc else 0
        rss_share = (d["c"] * d["a"] * d["T_stat"]) ** 2 / rss_c ** 2 if rss_c else 0
        contrib.append((d, wc_share, rss_share))
    contrib.sort(key=lambda x: -x[2])

    # what tolerance would the top contributors need?
    alloc = allocation(dims, mean_gap, spec, rss_c, wc)
    return {"nominal_gap": nominal_gap, "mean_gap": mean_gap, "stat_gap": stat_gap,
            "any_data": any_data, "methods": rows,
            "mc": mc, "rss_est": est, "contrib": contrib, "alloc": alloc,
            "any_nonnormal": any_nonnormal}


def verdict(lo, hi, spec):
    smin, smax = spec
    if smin is None and smax is None:
        return "no spec given"
    bad = []
    eps = 1e-9 * max(1.0, abs(lo), abs(hi))  # ignore floating-point dust at the limit
    if smin is not None and lo < smin - eps:
        bad.append(f"low end {plain(lo)} < min {plain(smin)}")
    if smax is not None and hi > smax + eps:
        bad.append(f"high end {plain(hi)} > max {plain(smax)}")
    return "PASS" if not bad else "FAIL (" + "; ".join(bad) + ")"


def allocation(dims, mean_gap, spec, rss_c, wc):
    """Largest tolerance the top contributors could have for the stack to pass."""
    smin, smax = spec
    room = []
    if smin is not None:
        room.append(mean_gap - smin)
    if smax is not None:
        room.append(smax - mean_gap)
    if not room:
        return None
    t_req = min(room)
    result = {"t_req": t_req, "rows": []}
    if t_req <= 0:
        result["centering"] = True
        return result
    ranked = sorted(dims, key=lambda d: -(d["c"] * d["a"] * d["T"]) ** 2)
    for d in ranked[:3]:
        k = abs(d["c"] * d["a"])
        other_rss = rss_c ** 2 - (d["c"] * d["a"] * d["T_stat"]) ** 2
        if d["data"]:
            rss_need = "data"  # a drawing change won't change a measured process
        else:
            rss_need = (math.sqrt(t_req ** 2 - other_rss) / k if t_req ** 2 > other_rss
                        else None)
        other_wc = wc - abs(d["a"]) * d["T"]
        wc_need = (t_req - other_wc) / abs(d["a"]) if t_req > other_wc else None
        result["rows"].append((d, rss_need, wc_need))
    return result


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def report(cfg, dims, spec, res, notes):
    u = cfg.get("units", "")
    out = []
    title = cfg.get("gap") or "gap"
    out.append(f"TOLERANCE STACK-UP: {title}" + (f" ({u})" if u else ""))
    out.append("=" * 76)
    for n in notes:
        out.append("NOTE: " + n)
    if notes:
        out.append("")
    out.append("CHAIN (converted to mean +/- T; a = direction x sensitivity)")
    w = max(len(d["name"]) for d in dims)
    for d in dims:
        conv = ""
        if d["shifted"]:
            conv = (f"   [{plain(d['nominal'])} {d['plus']:+g}/{d['minus']:+g} -> "
                    f"{plain(d['mean'])} +/- {plain(d['T'])}]")
        data_s = ""
        if d["data"]:
            data_s = (f"  DATA: process {plain(d['mean_stat'])}, "
                      f"3 sigma {plain(d['T_stat'])}")
        out.append(f"  {d['name']:<{w}}  {plain(d['mean']):>10} +/- {plain(d['T']):<8}"
                   f" a={d['a']:+g}  {d['dist']}"
                   + (f"  shift={d['eta']:.2f}" if d["eta"] else "") + conv + data_s)
    out.append("")
    out.append(f"Nominal gap (from drawing nominals): {plain(res['nominal_gap'])}")
    if abs(res["nominal_gap"] - res["mean_gap"]) > 1e-12:
        out.append(f"Mean gap (after centering unequal tolerances): "
                   f"{plain(res['mean_gap'])}")
    if res["any_data"]:
        out.append(f"Statistical methods use measured process data where given; "
                   f"expected gap from data: {plain(res['stat_gap'])}. Worst case still "
                   "uses the drawing tolerances.")
    smin, smax = spec
    out.append("Spec: " + ("none given" if smin is None and smax is None else
                           f"min {plain(smin) if smin is not None else '-'}, "
                           f"max {plain(smax) if smax is not None else '-'}"))
    out.append("")
    out.append("RESULTS")
    out.append(f"  {'method':<38} {'+/- T':>9}  {'gap range':<21} verdict")
    for r in res["methods"]:
        rng_s = f"{plain(r['low'])} to {plain(r['high'])}"
        out.append(f"  {r['method']:<38} {plain(r['T']):>9}  {rng_s:<21} {r['verdict']}")
    mc = res["mc"]
    out.append(f"  {'Monte Carlo (' + format(mc['samples'], ',') + ' samples)':<38} "
               f"{'sd ' + plain(mc['sd']):>9}  "
               f"{plain(mc['p00135']) + ' to ' + plain(mc['p99865']):<21} "
               "(99.73% interval)")
    if any(r.get("exceeds_wc") for r in res["methods"]):
        out.append("")
        out.append("NOTE: some statistical results came out wider than the worst case, "
                   "which can't really happen. With this few dimensions (or this many "
                   "uniform ones) statistical stacking gives no benefit: judge by worst "
                   "case and Monte Carlo.")
    out.append("")
    out.append("What each method means:")
    for r in res["methods"]:
        out.append(f"  - {r['method']}: {r['meaning']}")
    out.append(f"  - Monte Carlo: simulated assemblies; observed range "
               f"{plain(mc['min'])} to {plain(mc['max'])}")
    if smin is not None or smax is not None:
        out.append("")
        out.append("PREDICTED OUT-OF-SPEC ASSEMBLIES")
        bad = mc["below"] + mc["above"]
        out.append(f"  Monte Carlo: {bad} of {mc['samples']:,} "
                   f"({bad / mc['samples'] * 1e6:,.0f} per million)"
                   f" - {mc['below']} too small, {mc['above']} too large")
        if res["rss_est"] is not None:
            out.append(f"  RSS normal estimate: {res['rss_est'] * 1e6:,.0f} per million")
        if bad == 0:
            out.append("  (zero in the simulation does not mean zero in production; "
                       "it means fewer than ~1 in " + f"{mc['samples']:,})")
    out.append("")
    out.append("CONTRIBUTIONS (which tolerances matter)")
    out.append(f"  {'dimension':<{w}}  {'share of RSS variance':>22}  {'share of worst case':>20}")
    for d, wc_s, rss_s in res["contrib"]:
        out.append(f"  {d['name']:<{w}}  {rss_s * 100:>21.1f}%  {wc_s * 100:>19.1f}%")
    al = res["alloc"]
    if al:
        out.append("")
        out.append("TOLERANCE ALLOCATION (largest tolerance each could have, others "
                   "unchanged)")
        if al.get("centering"):
            out.append("  The mean gap itself is outside the spec: no tolerance change can "
                       "fix this. Change a nominal dimension first.")
        else:
            out.append(f"  Room available: +/- {plain(al['t_req'])} around the mean gap")
            def describe(need, now):
                if need == "data":
                    return "uses measured sigma; improve the process, not the drawing"
                if need is None:
                    return "can't pass by changing this one alone"
                if need >= now - 1e-12:
                    return f"<= +/- {plain(need)} (passes now; could loosen)"
                return f"<= +/- {plain(need)} (tighten)"
            for d, rss_need, wc_need in al["rows"]:
                r_s = describe(rss_need, d["T"])
                w_s = describe(wc_need, d["T"])
                out.append(f"  {d['name']} (now +/- {plain(d['T'])}): to pass RSS {r_s}; "
                           f"to pass worst case {w_s}")
    out.append("")
    out.append("ASSUMPTIONS TO CHALLENGE: linear 1D stack; dimensions independent (parts "
               "from one lot or machine often aren't); tolerance = 3 sigma for 'normal'; "
               "no temperature, deflection, or assembly slop unless you added them as "
               "dimensions.")
    return "\n".join(out)


def ascii_hist(gaps, spec, bins=30, width=46):
    lo, hi = gaps[0], gaps[-1]
    if hi <= lo:
        return ""
    step = (hi - lo) / bins
    counts = [0] * bins
    for g in gaps:
        counts[min(bins - 1, int((g - lo) / step))] += 1
    peak = max(counts)
    lines = ["", "DISTRIBUTION (Monte Carlo)"]
    smin, smax = spec
    for i, c in enumerate(counts):
        left = lo + i * step
        mark = ""
        if smin is not None and left <= smin < left + step:
            mark = "  <- spec min"
        if smax is not None and left <= smax < left + step:
            mark = "  <- spec max"
        lines.append(f"  {left:>10.4f} |{'#' * round(c / peak * width)}{mark}")
    return "\n".join(lines)


def plot(gaps, spec, res, path, units):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib not installed; skipped plot"
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(gaps, bins=80, color="#6b8fb5", edgecolor="white", linewidth=0.3)
    smin, smax = spec
    for x, lab in ((smin, "spec min"), (smax, "spec max")):
        if x is not None:
            ax.axvline(x, color="#c0392b", linewidth=2, label=lab)
    wc = res["methods"][0]
    ax.axvspan(wc["low"], wc["high"], color="#f5b041", alpha=0.12,
               label="worst-case range")
    ax.set_xlabel(f"gap ({units})" if units else "gap")
    ax.set_ylabel("simulated assemblies")
    ax.set_title("Tolerance stack-up: Monte Carlo gap distribution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    return f"plot saved to {path}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chain", nargs="?", help="CHAIN.json or CHAIN.csv")
    ap.add_argument("--template", action="store_true", help="print an example JSON")
    ap.add_argument("--plot", help="save a histogram PNG here")
    ap.add_argument("--samples", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    if args.template:
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if not args.chain:
        ap.error("give a CHAIN file, or --template")
    try:
        cfg = load(args.chain)
        dims, spec, notes = normalize(cfg)
    except (InputError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Input error: {e}", file=sys.stderr)
        return 2
    res = analyze(dims, spec, samples=max(1000, args.samples), seed=args.seed)
    if args.json:
        slim = {k: v for k, v in res.items() if k not in ("mc", "contrib", "alloc")}
        slim["monte_carlo"] = {k: v for k, v in res["mc"].items() if k != "gaps"}
        slim["contributions"] = [{"name": d["name"], "rss_share": r, "wc_share": w}
                                 for d, w, r in res["contrib"]]
        print(json.dumps(slim, indent=2, default=str))
    else:
        print(report(cfg, dims, spec, res, notes))
        print(ascii_hist(res["mc"]["gaps"], spec))
    if args.plot:
        print(plot(res["mc"]["gaps"], spec, res, args.plot, cfg.get("units", "")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
