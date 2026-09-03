# -*- coding: utf-8 -*-
"""A portfolio review deck for a book that holds BOTH direct equity and mutual funds.

WHY THIS EXISTS. `build_review.py` is deliberately fund-only: it is the advisor-side kit, and an
advisor sends a holding statement, which never carries the quantitative and analyst material the
equity pages need. So it switches those pages off. A book that is 60% direct equity therefore comes
out with 60% of itself missing.

This runs centrally, where the stock scorecard IS in reach, and turns those pages back on. Both
halves keep their own source of truth and neither is allowed to infer the other:

  funds   ionic_scores_<date>.csv, keyed on ISIN, paired with VERSION.json
  stocks  full750_scored_v3.csv for the numbers, pf_qual_<SYM>.json for the analyst's call

WHAT IT WILL NOT DO. It never invents a score. The demo builder reads `portfolio_quant.csv` and
falls back to 50.0 when a symbol is absent, which is fine for a demo and not fine here -- four of a
real eighteen were missing, and a defaulted 50 is indistinguishable on the page from a real one. So
the quantitative source is the v3 freeze, which covers the whole 750, and a symbol it does not cover
is reported rather than filled in.

Weights are percentages of the WHOLE book, never of a sleeve. Running the single-scheme cap against
the fund sleeve alone would read a 6%-of-book fund as 15% and trim it for breaching a cap it is
nowhere near.
"""
import argparse
import csv
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# Pages that need data no source here carries. Left off deliberately rather than rendered empty:
# tax needs lot-level cost and purchase dates, correlation needs the NAV panel, and the methodology
# pages are central method that does not belong in a client deck.
SKIP = {"mf_methodology", "scheme_correlation", "tax_impact", "funds_debt", "score_method"}
KEEP_ANNEX = {"holdings_detail", "appendix"}
ORDER = {"Sell": 0, "Trim": 1, "Hold (watch)": 2, "Hold": 3, "No View": 4}
HELD = ("Hold", "Hold (watch)")


def _f(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def mcap_band(mc):
    mc = _f(mc)
    if mc is None:
        return "Large"
    return "Large" if mc >= 30000 else "Mid" if mc >= 10000 else "Small" if mc >= 3000 else "Micro"


def build_equity(repo, holdings, grand):
    """One row per stock, from the v3 freeze plus the analyst file. Nothing defaulted."""
    res = os.path.join(repo, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
    f7 = {r["symbol"]: r for r in csv.DictReader(open(os.path.join(res, "full750_scored_v3.csv")))}

    rows, missing = [], []
    for sym, label, wt in holdings:
        r = f7.get(sym)
        if r is None or not r.get("ionic_score_v3"):
            missing.append(label)
            continue
        qp = os.path.join(res, "pf_qual_%s.json" % sym)
        q = json.load(open(qp, encoding="utf-8")) if os.path.exists(qp) else {}

        ionic = _f(r["ionic_score_v3"])
        s3, s1 = _f(r.get("final_score_3y_v3")), _f(r.get("final_score_1y_v3"))
        # The analyst's call governs. The mechanical recommendation_v3 is the input to it, not a
        # second opinion that overrides it -- Asian Paints scores 40.2 (mechanically a Hold) and is
        # an analyst Sell, and the deck has to say Sell.
        rec = q.get("your_recommendation") or r.get("analyst_call") or r.get("recommendation_v3") or "Hold"
        rows.append({
            "symbol": sym, "name": label, "sector": (r.get("sector") or "Diversified").title(),
            "weight_pct": wt, "value_inr": round(grand * wt / 100.0),
            "ionic_score": round(ionic, 1),
            "score_3y": None if s3 is None else round(s3, 1),
            "score_1y": None if s1 is None else round(s1, 1),
            "pe": _f(r.get("pe_current")), "roe": (_f(r.get("roe")) or 0) * 100,
            "mcap_band": mcap_band(r.get("market_cap_approx")),
            "rec": rec,
            "reason_category": (q.get("reason_category") or "") if rec == "Sell" else "",
            "exceptional_override": ((q.get("negative_para") or q.get("summary") or "")[:160].strip()
                                     if (rec == "Sell" and ionic >= 40) else None),
            "binding_trigger": (q.get("summary", "")[:130]) if rec == "Sell" else "",
            "analyst_read": (q.get("summary", "") or "").split(". ")[0][:150],
            "growth_pct": q.get("expected_next_3y_growth_pct"),
            "summary": q.get("summary", ""), "positive": q.get("positive_para", ""),
            "negative": q.get("negative_para", ""), "reverse_dcf": q.get("reverse_dcf_judgment", ""),
            "client_case": None, "detailed": q.get("detailed_rationale", ""),
            "escalation": bool(q.get("escalation_flag")),
            "conviction": "Core" if (ionic >= 58 and wt >= 2) else ("Watch" if rec == "Hold" else "Exit"),
        })
    rows.sort(key=lambda x: (ORDER.get(x["rec"], 9), -x["weight_pct"]))
    return rows, missing


def write_fund_statement(path, funds, grand):
    """A real holding statement, so the funds go through the kit's own parser and reconcile."""
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active; ws.title = "Holdings"
    ws.append(["Portfolio Holding Statement"]); ws.append([])
    ws.append(["Investor Name", "Scheme Name", "ISIN", "Folio No", "Units", "Market Value"])
    tot = 0.0
    for isin, name, wt in funds:
        v = round(grand * wt / 100.0)
        tot += v
        ws.append(["Client", name, isin, "-", "", v])
    ws.append(["", "TOTAL", "", "", "", tot])
    wb.save(path)
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="clone of ionic-scorecard")
    ap.add_argument("--holdings", required=True, help="JSON: {grand_inr, stocks:[[sym,name,wt]], funds:[[isin,name,wt]]}")
    ap.add_argument("--client", default="Client")
    ap.add_argument("--tier", default="HNI_DEEP")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    repo = os.path.abspath(a.repo)
    kit = os.path.join(repo, "ionic-deck-kit")
    engine_dir = os.path.join(repo, "Shreyas_Ionic_AMC", "09_PRODUCT", "pr_template")
    for p in (os.path.join(kit, "parse"), engine_dir,
              os.path.join(repo, "Shreyas_Ionic_AMC", "09_PRODUCT", "scripts"), HERE):
        sys.path.insert(0, p)

    from read_statement import read_statement
    import engine as ENG
    import tiers
    from preflight_scores import audit

    spec = json.load(open(a.holdings))
    grand = float(spec["grand_inr"])
    stocks = [tuple(x) for x in spec["stocks"]]
    fundspec = [tuple(x) for x in spec["funds"]]

    # ---- the pair, before anything is built ------------------------------------------------------
    blocks, warns, pf = audit(os.path.join(kit, "scores"), 60)
    for b in blocks:
        print("  BLOCK  %s" % b)
    if blocks:
        return 1
    for w in warns:
        print("  WARN   %s" % w)

    scores_csv = os.path.join(kit, "scores", pf["score_file"])
    ver = json.load(open(os.path.join(kit, "scores", "VERSION.json")))
    S = pd.read_csv(scores_csv)

    # ---- funds, through the kit's own parser -----------------------------------------------------
    out_dir = a.out or os.path.join(kit, "out")
    os.makedirs(out_dir, exist_ok=True)
    stmt = os.path.join(out_dir, "_fund_sleeve.xlsx")
    write_fund_statement(stmt, fundspec, grand)
    H, E, notes = read_statement(stmt)
    recon = notes.get("reconciliation")
    print("  funds      : %d rows, Rs %s, reconciliation %s"
          % (notes["rows"], format(int(notes["total_value"]), ","),
             "OK" if recon and recon["ok"] else "MISMATCH" if recon else "no total row"))
    if recon and not recon["ok"]:
        print("  BLOCK  the fund sleeve does not reconcile.")
        return 1

    # The statement carries a scheme name too, so suffix ITS columns and leave the score file's
    # unsuffixed. The score file's name is the one the desk published the call against; the
    # statement's spelling is only a fallback for a scheme the file does not carry.
    M = H.merge(S, on="isin", how="left", suffixes=("_stmt", ""))
    miss = sorted(M.loc[M["call"].isna(), "isin"].tolist())
    M["call"] = M["call"].fillna("No View")
    M["scheme"] = M["scheme"].fillna(M["scheme_stmt"])
    M["category"] = M["category"].fillna("Not in the score file")
    M["rationale"] = M["rationale"].fillna("")
    if miss:
        print("  %d fund(s) absent from the score file, rendered as No View: %s" % (len(miss), miss))

    G = (M.groupby(["isin", "scheme", "category", "call", "rationale"], dropna=False)
           .agg(value=("value", "sum"), score=("score", "first")).reset_index())
    # Weight is of the WHOLE book, so the cap means what it says.
    G["weight_pct"] = G["value"] / grand * 100
    G["trim_to_pct"] = None
    G["trim_value"] = 0.0
    cap = _f(ver.get("single_scheme_cap_pct"))
    if cap:
        over = G["call"].isin(HELD) & (G["weight_pct"] > cap)
        for i in G.index[over]:
            w = G.at[i, "weight_pct"]
            G.at[i, "trim_to_pct"] = cap
            G.at[i, "trim_value"] = G.at[i, "value"] - grand * cap / 100.0
            G.at[i, "call"] = "Trim"
            G.at[i, "rationale"] = (G.at[i, "rationale"].rstrip() + " " if G.at[i, "rationale"] else "") + (
                "At %.1f%% of the portfolio it is above the firm's %.0f%% single-scheme cap, so the "
                "weight comes down to %.0f%% rather than the fund being sold." % (w, cap, cap))
        print("  %d fund(s) above the %.0f%% cap of the whole book" % (int(over.sum()), cap))
    G["_o"] = G["call"].map(ORDER).fillna(9)
    G = G.sort_values(["_o", "value"], ascending=[True, False]).drop(columns="_o")

    # ---- stocks ------------------------------------------------------------------------------------
    equity, eq_missing = build_equity(repo, stocks, grand)
    if eq_missing:
        print("  %d stock(s) not scored in the v3 freeze, left out rather than defaulted: %s"
              % (len(eq_missing), ", ".join(eq_missing)))
    eq_value = sum(e["value_inr"] for e in equity)
    mf_value = float(G["value"].sum())

    residual = grand - eq_value - mf_value
    residual_pct = residual / grand * 100.0
    print("  stocks     : %d, Rs %s   funds: %d, Rs %s"
          % (len(equity), format(int(eq_value), ","), len(G), format(int(mf_value), ",")))
    if abs(residual_pct) > 0.05:
        print("  RESIDUAL   the named holdings account for %.1f%% of the stated Rs %s. "
              "Rs %s (%.1f%%) is unexplained and is shown as unallocated, not spread."
              % (100 - residual_pct, format(int(grand), ","),
                 format(int(residual), ","), residual_pct))
    print("  calls      : stocks " + " ".join("%s %d" % (k, sum(1 for e in equity if e["rec"] == k))
                                              for k in ("Sell", "Hold"))
          + "  |  funds " + "  ".join("%s %d" % (k, v) for k, v in G["call"].value_counts().items()))

    funds = [dict(name=r.scheme, isin=r.isin, category="equity", plan="Direct", amc="-",
                  sebi_category=r.category, value_inr=float(r.value), cost_inr=float(r.value),
                  unrealised_pnl=0.0, weight_pct=round(r.weight_pct, 2), verdict=r.call,
                  action=("Sell in full" if r.call == "Sell" else
                          ("Trim to %.0f%% of the portfolio" % r.trim_to_pct)
                          if (r.call == "Trim" and r.trim_to_pct is not None) else "Hold"),
                  trim_to_pct=(None if r.trim_to_pct is None else float(r.trim_to_pct)),
                  trim_value_inr=float(r.trim_value or 0),
                  qfra=(None if pd.isna(r.score) else float(r.score)), merit=None,
                  structural_reason=r.rationale, bench_label="", exemplar="-",
                  hit3y=None, alpha_t=None, ter=None, up_capture=None, down_capture=None,
                  max_dd=None, worst_1y=None, sortino=None, calmar=None, cagr3y=None,
                  bench_cagr3y=None, alpha_ann=None, info_ratio=None, r2=None, flags=[],
                  perf_flag=(r.call in ("Sell", "Trim", "Hold (watch)")))
             for r in G.itertuples()]

    n_sell = int((G["call"] == "Sell").sum()) + sum(1 for e in equity if e["rec"] == "Sell")
    ctx = {
        "client": {"name": a.client, "code": "-", "account_type": "Portfolio review",
                   "profile": "-", "horizon": "-", "construction": "Direct equity and mutual funds",
                   "aum_inr": grand, "as_of": ver["as_of"]},
        "ips": {"on_file": False, "single_name_cap_pct": 8.0, "single_amc_cap_pct": None,
                "locked_in_cap_pct": None, "cash_cap_pct": None, "alloc_bands": {},
                "mcap_bands": {}, "risk_tier": None, "objective": None, "horizon_yrs": None},
        "funds": funds, "equity": equity, "fund_churn": {},
        "totals": {"grand_inr": grand,
                   "eq_pct": round(eq_value / grand * 100, 1),
                   "mf_pct": round(mf_value / grand * 100, 1),
                   # Whatever the named rows do not account for. Shown rather than spread across
                   # the holdings: a book whose rows do not sum to its own stated total has an
                   # error in it somewhere, and hiding the gap is how it survives to the client.
                   "cash_pct": round(residual_pct, 1),
                   "n_stocks": len(equity), "n_funds": len(funds), "n_sell": n_sell,
                   "n_trim": int((G["call"] == "Trim").sum()),
                   "n_hold": int(G["call"].isin(HELD).sum()) + sum(1 for e in equity if e["rec"] == "Hold"),
                   "top10_pct": round(sum(sorted([e["weight_pct"] for e in equity] +
                                                 G["weight_pct"].tolist(), reverse=True)[:10]), 1),
                   "lookthrough": {}},
        "house_view": {"stance": {"Domestic equity": "Constructive, quality-biased",
                                  "Foreign equity": "none held", "Gold & silver": "none held",
                                  "Momentum": "Neutral", "Low-vol / value": "Favoured"},
                       "alloc_gap": {}, "sector_bands": {}},
        "tax": {"fund_rows": [], "gross": 0, "ltcg": 0, "stcg": 0, "net": 0},
        "deployment": {"proceeds_inr": 0, "tax_leak_inr": 0, "net_inr": 0, "personalization": []},
        "cost": {"reg_drag_inr": 0, "rows": []},
        "actions": [], "meeting_history": [], "goals": [], "chart_top_n": 6,
        "data_notes": {
            "suspended": [],
            "no_view": [{"name": r.scheme, "category": r.category,
                         "reason": "Outside the coverage of the firm's fund-quality frameworks."}
                        for r in G[G["call"] == "No View"].itertuples()],
            "flags": ["Fund scores are as of %s." % ver["as_of"],
                      "Stock scores are the v3 freeze of the 750 scorecard; the analyst call governs "
                      "where it differs from the mechanical recommendation.",
                      "No purchase cost or acquisition date was supplied, so no gain, loss or tax "
                      "figure is shown."]
                     + (["The named holdings account for %.1f%% of the stated portfolio value; "
                         "Rs %s (%.1f%%) is unallocated and needs to be identified."
                         % (100 - residual_pct, format(int(residual), ","), residual_pct)]
                        if abs(residual_pct) > 0.05 else [])
                     + (["%d fund(s) in this book are absent from the score file and carry no view."
                         % len(miss)] if miss else [])
                     + (["%d stock(s) are not scored and were left out." % len(eq_missing)]
                        if eq_missing else []),
        },
    }

    _orig = tiers.get

    def _get(name):
        t = _orig(name)
        t["skip_core"] = set(t.get("skip_core", set())) | SKIP
        t["optional_on"] = set(t["optional_on"]) & KEEP_ANNEX
        return t

    tiers.get = _get
    ENG.T = tiers

    deck, _manifest = ENG.build(ctx, a.tier, verbose=False)
    safe = "".join(c for c in a.client if c.isalnum() or c in " _-").strip().replace(" ", "_")
    path = os.path.join(out_dir, "%s_Review_%s.pptx" % (safe, a.tier))
    deck.save(path)

    wb = pd.concat([
        pd.DataFrame([{"kind": "Stock", "name": e["name"], "id": e["symbol"], "weight_pct": e["weight_pct"],
                       "value_inr": e["value_inr"], "call": e["rec"], "score": e["ionic_score"],
                       "rationale": e["analyst_read"]} for e in equity]),
        pd.DataFrame([{"kind": "Fund", "name": r.scheme, "id": r.isin, "weight_pct": round(r.weight_pct, 2),
                       "value_inr": r.value, "call": r.call, "score": r.score,
                       "rationale": r.rationale} for r in G.itertuples()])])
    wb.to_excel(os.path.join(out_dir, "%s_Holdings.xlsx" % safe), index=False)
    os.remove(stmt)

    print("  deck       : %d slides -> %s" % (len(deck.prs.slides._sldIdLst), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
