# -*- coding: utf-8 -*-
"""One command from a holding statement to a deck that is actually safe to send.

WHY THIS EXISTS. Every piece of the chain already works -- the parser reads by ISIN, the builder
renders the desk's calls, the three QA gates catch a deck that has drifted off the page or started
talking like an internal memo. What is missing is that nothing joins them up, so "send it" depends
on a person remembering to run four commands in order and read three lines of output in the middle
of the first one. That is fine on a good day and it is exactly what fails on a Friday afternoon.

So this runs the whole chain, refuses to call a deck sendable unless every stage passed, and says
in one line per statement whether it may go out.

WHAT IT WILL NOT DO. It never derives, fills in or edits a call. When the score file is internally
inconsistent -- two share classes of one scheme carrying different calls -- the honest answer is
that the desk has to fix the exporter and re-issue the pair. Guessing which of the two calls was
meant would be the kit deciding a call, which is the one thing it must never do. So it blocks the
affected client and names the ISINs.

  python run_review.py <statement.xlsx> --client "Family Name"
  python run_review.py --batch <folder-of-statements>
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = ["check_geometry.py", "check_geometry2.py", "tellscan.py"]


def find_kit(explicit):
    """Locate ionic-deck-kit. Named explicitly, or from the environment, or sitting next to us."""
    for c in (explicit, os.environ.get("IONIC_KIT"),
              os.path.join(HERE, "ionic-deck-kit"),
              os.path.join(HERE, "..", "ionic-deck-kit"),
              os.path.join(os.getcwd(), "ionic-deck-kit")):
        if c and os.path.isdir(os.path.join(c, "build")):
            return os.path.abspath(c)
    return None


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def statement_isins(kit, path):
    """The ISINs this statement actually holds, so a file-wide defect only blocks the clients it
    can reach. A split call on a fund nobody in this book owns is the desk's problem, not this
    deck's, and blocking on it would train people to pass --force out of habit."""
    sys.path.insert(0, os.path.join(kit, "parse"))
    try:
        from read_statement import read_statement
        H, _E, notes = read_statement(path)
        return set(H["isin"].astype(str)) if len(H) else set(), notes
    except Exception as e:                                  # noqa: BLE001 - reported, not swallowed
        return None, {"error": "%s: %s" % (type(e).__name__, e)}


def review_one(kit, statement, client, tier, flags, force, outdir):
    """Build and gate one statement. Returns a result dict; never raises on a bad statement."""
    r = dict(statement=os.path.basename(statement), client=client, tier=tier,
             sendable=False, stage=None, notes=[])

    # --- does this client touch a scheme the score file is inconsistent about? --------------------
    isins, notes = statement_isins(kit, statement)
    if isins is None:
        r["stage"] = "parse"
        r["notes"].append("could not read the statement -- %s" % notes.get("error"))
        return r
    recon = notes.get("reconciliation")
    r["holdings"] = notes.get("rows")
    r["total_value"] = notes.get("total_value")
    r["exceptions"] = notes.get("exceptions")
    r["reconciliation"] = ("OK" if recon and recon["ok"] else
                           "MISMATCH" if recon else "no total row to check against")

    if recon and not recon["ok"]:
        r["stage"] = "reconciliation"
        r["notes"].append(
            "parsed total is Rs {:,.0f} against the statement's own Rs {:,.0f} ({:+.2f}%). The deck "
            "would be built on a partial read and every number on it wrong."
            .format(recon["parsed"], recon["stated"], recon["gap_pct"]))
        return r

    # Only one of the three flags is worth stopping a deck for: a holding whose own row says No View
    # while the desk has actually called that scheme. The client would read "no view" and be wrong.
    understated = sorted(isins & flags["understated"])
    also_split = sorted(isins & flags["split_call"] - set(understated))
    odd_score = sorted(isins & flags["odd_score"])

    if also_split:
        r["notes"].append("holds %d ISIN(s) in a scheme whose share classes disagree, but this "
                          "holding's own call is well formed: %s"
                          % (len(also_split), ", ".join(also_split)))
    if odd_score:
        r["notes"].append("holds %d ISIN(s) whose score differs from its own scheme's other share "
                          "classes -- the printed number may come from the wrong pool: %s"
                          % (len(odd_score), ", ".join(odd_score)))
    if understated:
        r["understated_isins"] = understated
        if not force:
            r["stage"] = "score-file conflict"
            r["notes"].append("holds %d ISIN(s) marked No View while another share class of the same "
                              "scheme carries a real call: %s. This deck would tell the client the "
                              "desk has no view on a fund it has called. The desk has to fix the "
                              "exporter and re-issue the pair; the kit must not pick the call itself."
                              % (len(understated), ", ".join(understated)))
            return r
        r["notes"].append("FORCED past %d under-called ISIN(s): %s"
                          % (len(understated), ", ".join(understated)))

    # --- build ------------------------------------------------------------------------------------
    cmd = [sys.executable, os.path.join(kit, "build", "build_review.py"),
           os.path.abspath(statement), "--client", client, "--tier", tier]
    code, log = run(cmd, cwd=os.path.dirname(kit))
    r["build_log"] = log.strip()
    if code != 0:
        r["stage"] = "build"
        r["notes"].append("build_review.py exited %d" % code)
        return r
    if "DEMO" in log.upper() and "invented" in log.lower():
        r["stage"] = "build"
        r["notes"].append("the build used DEMO scores. Nothing from this run may be sent.")
        return r

    deck = os.path.join(kit, "out", "%s_Review_%s.pptx"
                        % (client.replace(" ", "_"), tier))
    if not os.path.exists(deck):
        r["stage"] = "build"
        r["notes"].append("no deck at %s" % deck)
        return r
    r["deck"] = deck

    # --- the three gates, all of them ---------------------------------------------------------------
    # All three run even after one fails. A single finding is usually a symptom, and seeing the other
    # two tells you whether it is a layout slip or the deck being wrong about what it is saying.
    r["gates"] = {}
    failed = []
    for g in GATES:
        code, log = run([sys.executable, os.path.join(kit, "qa", g), deck], cwd=os.path.dirname(kit))
        r["gates"][g] = dict(exit=code, output=log.strip())
        if code != 0 or "0 findings" not in log:
            failed.append(g)
    if failed:
        r["stage"] = "qa"
        r["notes"].append("gate(s) with findings: %s" % ", ".join(failed))
        return r

    if outdir:
        os.makedirs(outdir, exist_ok=True)
        for ext, name in ((".pptx", os.path.basename(deck)),
                          (".xlsx", "%s_Holdings.xlsx" % client.replace(" ", "_"))):
            src = os.path.join(kit, "out", name)
            if os.path.exists(src):
                subprocess.run(["cp", src, os.path.join(outdir, name)])
        r["delivered_to"] = outdir

    r["sendable"] = True
    r["stage"] = "complete"
    return r


def main():
    ap = argparse.ArgumentParser(description="Statement -> gated, sendable portfolio review deck.")
    ap.add_argument("statement", nargs="?", help="one holding statement")
    ap.add_argument("--batch", help="a folder of statements; the client name comes from the filename")
    ap.add_argument("--client", default="Client")
    ap.add_argument("--tier", default="HNI_DEEP", choices=["HNI_DEEP", "STANDARD", "RM_SIMPLE"])
    ap.add_argument("--kit", help="path to ionic-deck-kit")
    ap.add_argument("--out", help="copy the sendable deck and workbook here")
    ap.add_argument("--max-age-days", type=int, default=60)
    ap.add_argument("--force", action="store_true",
                    help="build even for a client holding an under-called ISIN. Recorded in the run "
                         "log; the conflict is still real and the deck still understates a call.")
    ap.add_argument("--log", help="write the full run log here as JSON")
    a = ap.parse_args()

    kit = find_kit(a.kit)
    if not kit:
        print("  cannot find ionic-deck-kit. Pass --kit or set IONIC_KIT.")
        return 2
    print("  kit        : %s" % kit)

    # --- 1. the pair, before anything is built --------------------------------------------------
    sys.path.insert(0, HERE)
    from preflight_scores import audit
    blocks, warns, pf = audit(os.path.join(kit, "scores"), a.max_age_days)
    print("  score file : %s   as of %s   (%s days old)"
          % (pf.get("score_file", "-"), ", ".join(pf.get("as_of", ["-"])), pf.get("age_days", "?")))
    for b in blocks:
        print("  BLOCK  %s" % b)
    for w in warns:
        print("  WARN   %s" % w)
    if blocks:
        print("\n  nothing was built. The pair has to be fixed first.")
        return 1
    flags = dict(understated=set(pf.get("understated_isins", [])),
                 split_call=set(pf.get("split_call_isins", [])),
                 odd_score=set(pf.get("odd_score_isins", [])))

    # --- 2. the statements ------------------------------------------------------------------------
    jobs = []
    if a.batch:
        for p in sorted(glob.glob(os.path.join(a.batch, "*.xls*"))):
            if os.path.basename(p).startswith("~$"):
                continue
            name = os.path.splitext(os.path.basename(p))[0].replace("_", " ").strip()
            jobs.append((p, name))
    elif a.statement:
        jobs.append((a.statement, a.client))
    else:
        print("  give a statement, or --batch a folder of them.")
        return 2

    print()
    results = []
    for path, client in jobs:
        res = review_one(kit, path, client, a.tier, flags, a.force, a.out)
        results.append(res)
        mark = "SENDABLE" if res["sendable"] else "BLOCKED "
        print("  %s  %-34s %s" % (mark, res["statement"][:34], client))
        if res.get("holdings") is not None:
            print("            %s holdings, Rs %s, reconciliation %s, %s exception(s)"
                  % (res["holdings"], format(int(res.get("total_value") or 0), ","),
                     res["reconciliation"], res.get("exceptions")))
        for n in res["notes"]:
            print("            %s" % n)
        print()

    ok = sum(1 for r in results if r["sendable"])
    print("  %d of %d sendable." % (ok, len(results)))
    if ok < len(results):
        print("  A blocked deck is not a failed run. It is the check doing its job -- send the")
        print("  named ISINs or the reconciliation gap back to the desk.")

    if a.log:
        with open(a.log, "w") as fh:
            json.dump(dict(run_at=dt.datetime.now().isoformat(timespec="seconds"),
                           kit=kit, preflight=pf, preflight_warnings=warns,
                           results=results), fh, indent=1)
        print("  run log    : %s" % a.log)

    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
