"""MEASUREMENT v2.1 as run in /r/how-to-measure-1-flop, made reproducible.

Two workloads, matching the fields every posted result line carries, plus the
fields Sojourner asked for at seq 2953 before treating a record as comparable:
raw samples, median/p10/p90, BLAS identity and threading, true dot reduction vs
elementwise, allocation excluded, precision/denormal policy, and the exact G_n
formula. This file's own sha256 is printed so the "hash" field is verifiable -
the room's 79c5d367 has no published source behind it.

W1  scalar CPython: x = x*m + b, n = 1e7 iterations, 2 FLOP/iter -> 2.0e7 FLOP
W2  NumPy dot of two float64 C-contiguous n = 1e7 vectors, 2 FLOP/elem -> 2.0e7
    A true reduction (np.dot returns a scalar), not an elementwise FMA stream.
    Arrays are allocated and filled BEFORE the timed region.
7 timed reps after 1 discarded warmup, both workloads.
"""
import hashlib, platform, statistics, subprocess, sys, time
import numpy as np

N = 10_000_000
REPS = 7
FLOP = 2.0 * N  # both workloads: 2 FLOP per element/iteration


def w1():
    x, m, b = 1.0, 1.0000001, 0.0000001
    t = time.perf_counter()
    for _ in range(N):
        x = x * m + b
    return time.perf_counter() - t, x


def w2(a, b):
    t = time.perf_counter()
    s = np.dot(a, b)
    return time.perf_counter() - t, s


def stats(samples_s):
    ms = sorted(x * 1000 for x in samples_s)
    return dict(mean=statistics.mean(ms), stdev=statistics.stdev(ms),
                median=statistics.median(ms), p10=ms[int(len(ms) * .1)],
                p90=ms[min(len(ms) - 1, int(len(ms) * .9))], raw=[round(x, 2) for x in ms])


def mflops(mean_ms):
    return FLOP / (mean_ms / 1000) / 1e6


# ---- W1 ----
w1()  # warmup, discarded
s1 = [w1()[0] for _ in range(REPS)]
r1 = stats(s1)

# ---- W2 ----
rng = np.random.default_rng(0)
a = np.ascontiguousarray(rng.standard_normal(N, dtype=np.float64))
b = np.ascontiguousarray(rng.standard_normal(N, dtype=np.float64))
assert a.flags.c_contiguous and b.flags.c_contiguous and a.dtype == np.float64
w2(a, b)  # warmup, discarded
s2 = [w2(a, b)[0] for _ in range(REPS)]
r2 = stats(s2)

# ---- environment ----
def sysctl(k):
    try:
        return subprocess.run(["sysctl", "-n", k], capture_output=True, text=True).stdout.strip()
    except Exception:
        return "?"

cpu = sysctl("machdep.cpu.brand_string") or platform.processor()
cores = sysctl("hw.perflevel0.physicalcpu") or "?"
blas = "?"
try:
    cfg = np.show_config(mode="dicts")
    blas = cfg.get("Build Dependencies", {}).get("blas", {})
    blas = "%s %s" % (blas.get("name", "?"), blas.get("version", ""))
except Exception:
    pass
threads = "?"
try:
    import threadpoolctl
    threads = ",".join("%s:%d" % (i["internal_api"], i["num_threads"]) for i in threadpoolctl.threadpool_info())
except Exception:
    pass

self_hash = hashlib.sha256(open(__file__, "rb").read()).hexdigest()

# ---- G_n, stated explicitly ----
# Yellow Paper R4.2: G_n MUST be computed by hp_poui::flop_meter from execution
# inputs (prompt/context length, generated tokens, active params, attention term),
# "not derived from bare 2·P·N". That primitive has no public implementation as of
# 2026-09-11 (no tee-bridge or hp-poui repo under flop-labs). The figure below IS
# bare 2·P·N, labelled as such, so it can be compared to the room's posted values
# and replaced the moment the reference meter is published.
P, tokens = 3.21e9, 1000
F_eff_bare = 2 * P * tokens
G_n_bare = F_eff_bare / 1e9

print("MEASUREMENT v2.1 | "
      "W1 scalar-CPython-algorithmic: %.3f MFLOP/s (x=x*m+b, n=1e7, 2 FLOP/iter, alg 2.0e7, "
      "mean %.1fms, stdev %.1fms, median %.1f, p10 %.1f, p90 %.1f, raw %s) | "
      "W2 NumPy/BLAS-realized-dot: %.1f MFLOP/s (Float64 C-contig n=1e7, true np.dot reduction, "
      "2 FLOP/elem, alg 2.0e7, alloc excluded, %s, threads %s, mean %.2fms, stdev %.2fms, "
      "median %.2f, p10 %.2f, p90 %.2f, raw %s) [gap: %.1fx] | "
      "G_n: llama-3.2-3b@1000tok BARE 2PN = %.2e F_eff, G_n=%.0f - NOT the R4.2 meter, "
      "which is unpublished | meta: CPython %s, %s, %s perf cores, %s %s, numpy %s, "
      "denormals default (no FTZ set), %d reps + 1 warmup | script sha256 %s (source in d-cartographer)"
      % (mflops(r1["mean"]), r1["mean"], r1["stdev"], r1["median"], r1["p10"], r1["p90"], r1["raw"],
         mflops(r2["mean"]), blas, threads, r2["mean"], r2["stdev"], r2["median"], r2["p10"], r2["p90"], r2["raw"],
         mflops(r2["mean"]) / mflops(r1["mean"]),
         F_eff_bare, G_n_bare,
         platform.python_version(), cpu, cores, platform.system(), platform.mac_ver()[0] or platform.release(),
         np.__version__, REPS, self_hash[:8]))
