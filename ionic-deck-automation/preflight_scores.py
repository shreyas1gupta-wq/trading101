# -*- coding: utf-8 -*-
"""Check the score file / VERSION.json pair BEFORE it is used to build a client deck.

WHY THIS EXISTS. The kit is careful about the deck and careless about nothing -- except the one
input it cannot see inside. `latest_score_file()` already refuses to mistake the demo for
production, and `build_review.py` already refuses a pair whose dates disagree. Neither looks at
whether the calls INSIDE the file are self-consistent, and that is where the expensive defects have
lived: a share class that could not be reached by the desk's own ruling, a scheme carrying two
different scores because one share class spelled its name with an underscore.

Those are central defects. This script does not repair them -- the kit never derives or edits a
call, and a preflight that "helpfully" filled a gap would be the worst possible place to break that
rule. It reports, names the ISINs, and lets the desk fix the exporter and re-issue the pair.

It carries no method: no thresholds, no percentile arithmetic, no peer construction. Every check
here is an internal-consistency check on the file it is handed, so this script is safe to sit in
the advisor-side kit.

Exit codes:  0 clean (warnings may still be printed)   1 BLOCK   2 could not run
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import sys

CALLS = {"Sell", "Trim", "Hold", "Hold (watch)", "No View"}
ACTIONED = CALLS - {"No View"}
RATIONALE_PREFIX = "QFRA Framework:"

# IDCW is spelled a dozen ways across AMFI's own file. These come off as whole units, never word by
# word: stripping "Payout of Income Distribution cum capital withdrawal" one word at a time once
# left a bare "OF" welded to a fund name, and the orphan became a key of its own that the desk's
# ruling on that fund could never reach.
IDCW_PHRASES = [
    r"PAYOUT\s*(&|AND)?\s*RE-?\s?INVESTMENT\s+OF\s+INCOME\s+DISTRIBUTION\s+CUM\s+CAPITAL\s+WITHDRAWAL(\s+OPTION)?",
    r"PAYOUT\s+OF\s+INCOME\s+DISTRIBUTION\s+CUM\s+CAPITAL\s+WITHDRAWAL(\s+OPTION)?",
    r"RE-?\s?INVESTMENT\s+OF\s+INCOME\s+DISTRIBUTION\s+CUM\s+CAPITAL\s+WITHDRAWAL(\s+OPTION)?",
    r"INCOME\s+DISTRIBUTION\s+CUM\s+CAPITAL\s+WITHDRAWAL(\s+OPTION)?",
    r"IDCW\s*[-/ ]?\s*PAYOUT\s*[/&]?\s*(AND\s+)?RE-?\s?INVESTMENT",
    r"IDCW\s+PAYOUT\s*[/&]\s*RE-?\s?INVESTMENT",
    r"PAYOUT\s*/\s*RE-?\s?INVESTMENT",
]
PLAN_WORDS = ["DIRECT PLAN", "REGULAR PLAN", "DIRECT", "REGULAR", "PLAN",
              "GROWTH OPTION", "GROWTH", "CUMULATIVE", "IDCW", "PAYOUT",
              "REINVESTMENT", "RE-INVESTMENT", "RE INVESTMENT", "OPTION", "BONUS"]
CONNECTIVES = {"OF", "CUM", "AND", "WITH", "FOR", "THE", "-", "&", "_", "/"}


def base_key(name):
    """The scheme identity, with plan and option stripped off.

    Deliberately close to what the exporter should be doing, so that a disagreement this finds is a
    disagreement a client would actually experience: two ISINs the advisor's statement calls the
    same fund, carrying two different calls.
    """
    s = name.upper()
    for p in IDCW_PHRASES:
        s = re.sub(p, " ", s)
    s = re.sub(r"[-_&/,.()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for w in sorted(PLAN_WORDS, key=len, reverse=True):
        s = re.sub(r"\b" + re.escape(w) + r"\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = s.split()
    while toks and toks[-1] in CONNECTIVES:
        toks.pop()
    return " ".join(toks)


def load_pair(scores_dir):
    """The score file and its VERSION, chosen together.

    A production file and a VERSION file are read as a pair or not at all. Pairing them by
    directory listing rather than by name once let a deck print a production as-of date over
    invented demo scores, so the demo is only ever a fallback and says so out loud.
    """
    names = sorted(x for x in os.listdir(scores_dir)
                   if x.startswith("ionic_scores_") and x.endswith(".csv"))
    real = [x for x in names if not x.upper().endswith("_DEMO.CSV")]
    if real:
        csv_path, is_demo = os.path.join(scores_dir, real[-1]), False
        ver = os.path.join(scores_dir, "VERSION.json")
    elif names:
        csv_path, is_demo = os.path.join(scores_dir, names[-1]), True
        ver = os.path.join(scores_dir, "VERSION_DEMO.json")
    else:
        return None, None, None, True
    version = json.load(open(ver)) if os.path.exists(ver) else None
    return csv_path, ver, version, is_demo


def audit(scores_dir, max_age_days):
    blocks, warns, out = [], [], {}

    csv_path, ver_path, version, is_demo = load_pair(scores_dir)
    if csv_path is None:
        return ["no score file in %s. The kit cannot issue a call without one." % scores_dir], [], {}
    out["score_file"] = os.path.basename(csv_path)
    out["is_demo"] = is_demo

    if is_demo:
        blocks.append("the only score file present is the DEMO. Its calls are invented. "
                      "Stop and get a current production pair from the desk.")
    if version is None:
        blocks.append("no VERSION file beside %s. The pair travels together or not at all."
                      % os.path.basename(csv_path))
        version = {}

    rows = list(csv.DictReader(open(csv_path)))
    out["rows"] = len(rows)

    need = {"isin", "scheme", "category", "score", "call", "rationale", "as_of"}
    missing = need - set(rows[0].keys() if rows else [])
    if missing:
        return ["score file is missing column(s): %s" % ", ".join(sorted(missing))], [], out

    # --- the pair agrees with itself -------------------------------------------------------------
    file_dates = {r["as_of"] for r in rows}
    out["as_of"] = sorted(file_dates)
    if len(file_dates) > 1:
        blocks.append("score file carries %d different as_of dates: %s"
                      % (len(file_dates), ", ".join(sorted(file_dates))))
    if version.get("as_of") and file_dates and version["as_of"] not in file_dates:
        blocks.append("VERSION says as_of %s, the score file says %s. Mismatched pair."
                      % (version["as_of"], sorted(file_dates)[0]))
    for key, actual in (("rows", len(rows)),
                        ("scored", sum(1 for r in rows if r["score"].strip()))):
        if key in version and int(version[key]) != actual:
            blocks.append("VERSION says %s=%s, the file has %d." % (key, version[key], actual))
        out[key] = actual
    cap = version.get("single_scheme_cap_pct")
    if cap is None:
        blocks.append("VERSION has no single_scheme_cap_pct. Without it the kit cannot size a Trim.")
    else:
        try:
            out["cap_pct"] = float(cap)
        except (TypeError, ValueError):
            blocks.append("single_scheme_cap_pct is not a number: %r" % (cap,))

    # --- age --------------------------------------------------------------------------------------
    if version.get("as_of"):
        try:
            age = (dt.date.today() - dt.date.fromisoformat(version["as_of"])).days
            out["age_days"] = age
            if age > max_age_days:
                warns.append("the pair is %d days old (as of %s). Ask the desk for a newer one "
                             "before this goes to a client." % (age, version["as_of"]))
        except ValueError:
            warns.append("VERSION as_of %r is not an ISO date." % version["as_of"])

    # --- one row per ISIN ---------------------------------------------------------------------------
    dupes = [i for i, n in collections.Counter(r["isin"] for r in rows).items() if n > 1]
    if dupes:
        blocks.append("%d ISIN(s) appear more than once, so the call an advisor gets depends on row "
                      "order: %s" % (len(dupes), ", ".join(sorted(dupes)[:8])))
    blank = sum(1 for r in rows if not r["isin"].strip())
    if blank:
        blocks.append("%d row(s) carry no ISIN. The file is keyed on ISIN; those rows are unreachable."
                      % blank)

    # --- the call vocabulary ------------------------------------------------------------------------
    vocab = collections.Counter(r["call"] for r in rows)
    out["calls"] = dict(vocab)
    stray = set(vocab) - CALLS
    if stray:
        blocks.append("call(s) outside the vocabulary: %s. Allowed: %s."
                      % (", ".join(sorted(stray)), ", ".join(sorted(CALLS))))
    if "Buy" in vocab:
        blocks.append("the file contains %d Buy call(s). No client Buy is ever issued." % vocab["Buy"])
    if "Trim" in vocab:
        warns.append("the file contains Trim calls. Trim is a judgement on a WEIGHT, not on a fund, "
                     "and an ISIN-keyed file cannot carry it -- the kit derives it from the cap.")

    # --- rationale rules ---------------------------------------------------------------------------
    no_rationale = [r["isin"] for r in rows if r["call"] in ACTIONED and not r["rationale"].strip()]
    has_rationale = [r["isin"] for r in rows if r["call"] == "No View" and r["rationale"].strip()]
    bad_prefix = [r["isin"] for r in rows
                  if r["rationale"].strip() and not r["rationale"].startswith(RATIONALE_PREFIX)]
    if no_rationale:
        blocks.append("%d actioned call(s) carry no rationale: %s"
                      % (len(no_rationale), ", ".join(no_rationale[:8])))
    if has_rationale:
        blocks.append("%d No View row(s) carry a rationale, which is never written: %s"
                      % (len(has_rationale), ", ".join(has_rationale[:8])))
    if bad_prefix:
        blocks.append("%d rationale(s) do not open %r: %s"
                      % (len(bad_prefix), RATIONALE_PREFIX, ", ".join(bad_prefix[:8])))

    # --- share classes of one scheme must agree ------------------------------------------------------
    # This is the check that earns the script's keep. A client holds ONE share class. If the IDCW
    # class of a fund says No View while its Growth class says Sell, the deck tells that client
    # nothing is wrong -- and the desk's actual call never reaches them.
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["category"], base_key(r["scheme"]))].append(r)
    out["scheme_groups"] = len(groups)

    # Two different harms hide inside one "split call", and they are not equally bad.
    #
    # A client holding the share class that got a real call is FINE -- their deck says what the desk
    # thinks. The client who is hurt is the one holding the class that came out No View while a
    # sibling class carries an actioned call: their deck says the desk has no view on a fund the desk
    # has in fact called. That is the failure that shipped before, and it is silent, because No View
    # is also the correct answer for thousands of legitimate rows.
    #
    # Naming that ISIN is not the kit deriving a call. It is the kit saying "this row is
    # under-called, ask the desk" -- which is the only honest thing it can say.
    split_call, split_score = [], []
    understated, in_split_call, odd_score = set(), set(), set()
    for (cat, b), members in sorted(groups.items()):
        calls = {m["call"] for m in members}
        if len(calls) > 1:
            actioned = sorted(calls & ACTIONED)
            split_call.append(dict(scheme=b, category=cat, calls=sorted(calls),
                                   actioned=actioned,
                                   isins=sorted(m["isin"] for m in members)))
            in_split_call.update(m["isin"] for m in members)
            if actioned:
                understated.update(m["isin"] for m in members if m["call"] == "No View")

        # Only NON-BLANK scores count here. A blank is an absence, not a competing number, and
        # counting it made the modal score come out blank whenever a scheme had more IDCW share
        # classes than Growth ones -- which flagged the two correctly-scored rows as the odd ones.
        # Blank-against-scored is a coverage gap, and the call checks above already catch it.
        scored = [m for m in members if m["score"].strip()]
        distinct = {m["score"] for m in scored}
        if len(distinct) > 1:
            counts = collections.Counter(m["score"] for m in scored)
            modal = counts.most_common(1)[0][0]
            split_score.append(dict(scheme=b, category=cat, scores=sorted(distinct),
                                    modal=modal,
                                    isins=sorted(m["isin"] for m in scored)))
            odd_score.update(m["isin"] for m in scored if m["score"] != modal)
    stranded = sorted({b for _, b in groups if b.split() and b.split()[-1] in CONNECTIVES})
    empty_keys = sorted({c for c, b in groups if not b})

    out["split_call"] = split_call
    out["split_score"] = split_score
    # understated_isins is the set worth blocking a client on. The other two only warn.
    out["understated_isins"] = sorted(understated)
    out["split_call_isins"] = sorted(in_split_call)
    out["odd_score_isins"] = sorted(odd_score)

    if understated:
        warns.append("%d ISIN(s) say No View while another share class of the same scheme carries a "
                     "real call. A client holding one of those is told the desk has no view on a "
                     "fund the desk has actually called: %s"
                     % (len(understated), ", ".join(sorted(understated)[:6])))
    if split_call:
        warns.append("%d scheme(s) carry more than one CALL across their share classes (%d ISINs). "
                     "Central fix: the exporter's share-class key."
                     % (len(split_call), sum(len(s["isins"]) for s in split_call)))
    if split_score:
        warns.append("%d scheme(s) carry more than one SCORE across their share classes; %d ISIN(s) "
                     "differ from their scheme's own modal score. One score per scheme, from the "
                     "Direct plan." % (len(split_score), len(odd_score)))
    if stranded:
        warns.append("%d scheme key(s) end on a connective, which is how a name-splitting bug "
                     "announces itself: %s" % (len(stranded), ", ".join(stranded[:5])))
    if empty_keys:
        warns.append("%d scheme key(s) reduced to nothing at all." % len(empty_keys))

    return blocks, warns, out


def main():
    ap = argparse.ArgumentParser(description="Audit a score file / VERSION.json pair before a deck run.")
    ap.add_argument("--scores", required=True, help="the kit's scores/ directory")
    ap.add_argument("--max-age-days", type=int, default=60)
    ap.add_argument("--report", help="write the full findings here as JSON")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.scores):
        print("  no such directory: %s" % a.scores)
        return 2

    blocks, warns, out = audit(a.scores, a.max_age_days)

    if not a.quiet:
        print("  score file : %s" % out.get("score_file", "-"))
        print("  as of      : %s   (%s days old)"
              % (", ".join(out.get("as_of", ["-"])), out.get("age_days", "?")))
        print("  rows       : %s   scored %s   cap %s%%"
              % (out.get("rows", "?"), out.get("scored", "?"), out.get("cap_pct", "?")))
        print("  calls      : %s" % out.get("calls", {}))
        for b in blocks:
            print("  BLOCK  %s" % b)
        for w in warns:
            print("  WARN   %s" % w)
        for s in out.get("split_call", []):
            print("         split call  %-46s %s" % (s["scheme"][:46], "/".join(s["calls"])))
        for s in out.get("split_score", []):
            print("         split score %-46s %s" % (s["scheme"][:46], "/".join(s["scores"])))
        if not blocks and not warns:
            print("  clean.")

    if a.report:
        out["blocks"], out["warnings"] = blocks, warns
        with open(a.report, "w") as fh:
            json.dump(out, fh, indent=1)
        if not a.quiet:
            print("  report     : %s" % a.report)

    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
