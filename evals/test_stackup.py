"""Regression tests for scripts/stackup.py. Run: python3 evals/test_stackup.py"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts", "stackup.py")
F = os.path.join(ROOT, "evals", "files")

def run(*a):
    r = subprocess.run([sys.executable, S, *a, "--samples", "50000"],
                       capture_output=True, text=True)
    return r.stdout + r.stderr + f"\nexit={r.returncode}"

cases = [
  ("published bearing example (Wevolver/Scholz): WC 0.45, RSS 0.2398, shares",
   run(f"{F}/bearing_stack.json"),
   ["Worst case                                  0.45  -0.05 to 0.85",
    "RSS                                       0.2398  0.1602 to 0.6398      PASS",
    "69.6%", "17.4%", "4.3%"]),
  ("same chain from CSV gives same answers", run(f"{F}/bearing.csv"),
   ["0.45  -0.05 to 0.85", "0.2398"]),
  ("mean-shift eta=0.2 = 0.2*0.45 + 0.8*0.2398 = 0.2818", run(f"{F}/bearing_stack.json"),
   ["Mean-shift model (eta=0.20)               0.2818"]),
  ("Bender = 1.5 x RSS = 0.3597", run(f"{F}/bearing_stack.json"), ["0.3597"]),
  ("Bender leaves measured sigma alone: sqrt(.12^2 + 1.5^2*(.05^2*3+.1^2)) = 0.2319",
   run(f"{F}/process_data.json"), ["0.2319"]),
  ("asymmetric 10.0 +0.3/-0.0 -> 10.15 +/- 0.15; pin 10 +0/-0.1 -> 9.95 +/- 0.05",
   run(f"{F}/asymmetric.json"),
   ["10.15 +/- 0.15", "9.95 +/- 0.05", "Mean gap (after centering unequal tolerances): 0.2",
    "Worst case                                   0.2  0 to 0.4"]),
  ("uniform distribution inflation factor sqrt(3)", run(f"{F}/uniform_one.json"),
   ["RSS (with distribution factors)           1.7321"]),
  ("sensitivity coefficient 2 doubles that contribution: WC = 2*0.1+0.1 = 0.3",
   run(f"{F}/lever.json"), ["Worst case                                   0.3", "a=+2"]),
  ("plus below minus is rejected with a fix hint", run(f"{F}/bad_minus.json"),
   ["Input error", "Write minus with its sign", "exit=2"]),
  ("dir must be +/-1", run(f"{F}/bad_dir.json"), ["dir must be +1", "exit=2"]),
  ("mean gap outside spec -> change a nominal, not a tolerance", run(f"{F}/off_center.json"),
   ["no tolerance change can fix this"]),
  ("both-positive deviations get a warning", run(f"{F}/both_positive.json"),
   ["NOTE: 'Boss': both deviations are positive"]),
  ("limits input + per-dimension mean shift", run(f"{F}/limits_shift.json"),
   ["100 +/- 0.1", "shift=0.20", "Mean-shift model (eta=per input)"]),
  ("2 uniform parts: statistical wider than worst case is flagged, not passed",
   run(f"{F}/lid_fit.json"),
   ["n/a: wider than worst case", "NOTE: some statistical results came out wider",
    "Worst case                                   0.4  0 to 0.8"]),
  ("asymmetric bracket: worst case 0.05 to 0.55 passes; Bender n/a for 2 parts",
   run(f"{F}/bracket.json"),
   ["24.9 +/- 0.2", "0.25  0.05 to 0.55          PASS", "n/a: wider than worst case"]),
  ("exactly-at-limit result is not a false FAIL (0.4-0.35 = 0.0499999...)",
   run(f"{F}/boundary.json"),
   ["FAIL (high end 0.75 > max 0.7)"]),
  ("measured sigma/process mean: RSS sqrt(.12^2+...) = 0.1786 centered at 0.43; WC unchanged",
   run(f"{F}/process_data.json"),
   ["DATA: process 52.43, 3 sigma 0.12", "0.1786  0.2514 to 0.6086",
    "Worst case                                  0.45  -0.05 to 0.85",
    "Mean-shift model (eta=0.20)                 0.21  0.22 to 0.64"]),
  ("template prints valid JSON", subprocess.run([sys.executable, S, "--template"],
   capture_output=True, text=True).stdout, ['"dimensions"']),
]
fails = 0
for name, out, expects in cases:
    missing = [e for e in expects if e not in out]
    print(("PASS " if not missing else "FAIL ") + name + ("" if not missing else f"\n     missing: {missing}"))
    fails += bool(missing)
print(f"\n{len(cases) - fails}/{len(cases)} passed")
sys.exit(1 if fails else 0)
