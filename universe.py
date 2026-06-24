"""
Survivorship-bias-free index universe  |  NSE Nifty 200 / Nifty 500 (2005-2025)
================================================================================
Turns the semi-annual constituent snapshots (Month-Year x Ticker, the Mar/Sep
NSE reconstitution dates) into a point-in-time membership mask. A backtest that
restricts each day's tradable names to `members_asof(date)` will only ever buy
stocks that were ACTUALLY in the index then -- no peeking at today's survivors.

Why it matters: Nifty 500 has ~1,004 distinct tickers across 2005-2025 but only
~500 live at any time; ignoring that turnover inflates backtest returns badly.

Usage
-----
    uni = IndexUniverse("data/NIFTY500_constituents_2005_2025.xlsx")
    uni.members_asof("2014-07-01")          # set of tickers in the index then
    mask = uni.daily_mask(price_panel.index) # daily bool frame: dates x tickers
    tradable_close = price_panel.where(mask) # NaN where not a member -> untradable
"""

import pandas as pd

NIFTY500 = "data/NIFTY500_constituents_2005_2025.xlsx"
NIFTY200 = "data/NIFTY200_constituents_2005_2025.xlsx"


class IndexUniverse:
    def __init__(self, xlsx_path):
        df = pd.read_excel(xlsx_path)
        df.columns = [str(c).strip() for c in df.columns]
        df["date"]   = pd.to_datetime(df["Month-Year"], format="%b%Y")
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
        self.long = df[["date", "Ticker"]].drop_duplicates().sort_values(["date", "Ticker"])
        self.snapshots = self.long["date"].drop_duplicates().sort_values().reset_index(drop=True)
        self.path = xlsx_path

    # ── point-in-time membership ─────────────────────────────────────────────
    def members_asof(self, date):
        """Set of tickers that were index members on `date` (latest snapshot <= date)."""
        date = pd.Timestamp(date)
        valid = self.snapshots[self.snapshots <= date]
        if len(valid) == 0:                      # before first snapshot -> use earliest
            snap = self.snapshots.iloc[0]
        else:
            snap = valid.iloc[-1]
        return set(self.long.loc[self.long["date"] == snap, "Ticker"])

    def all_tickers(self):
        """Every ticker that was ever a member (the bias-free superset to fetch prices for)."""
        return sorted(self.long["Ticker"].unique())

    # ── daily mask for backtesting ───────────────────────────────────────────
    def daily_mask(self, price_dates, tickers=None):
        """Boolean DataFrame [price_dates x tickers]: True where the ticker was a
        member as of that date. Snapshots are forward-filled to daily frequency."""
        price_dates = pd.DatetimeIndex(price_dates)
        cols = sorted(set(tickers)) if tickers is not None else self.all_tickers()

        # membership matrix at snapshot dates, then reindex+ffill to daily
        snap_mat = (self.long.assign(v=True)
                    .pivot_table(index="date", columns="Ticker", values="v",
                                 aggfunc="any", fill_value=False)
                    .reindex(columns=cols, fill_value=False)
                    .sort_index())
        daily = (snap_mat.reindex(snap_mat.index.union(price_dates))
                 .ffill()                          # carry membership between reconstitutions
                 .reindex(price_dates)
                 .fillna(False)
                 .astype(bool))
        return daily

    def summary(self):
        per = self.long.groupby("date")["Ticker"].nunique()
        return (f"{self.path.split('/')[-1]}: {len(self.snapshots)} snapshots "
                f"{self.snapshots.min():%b%Y}->{self.snapshots.max():%b%Y}, "
                f"~{per.mean():.0f} members/snapshot, "
                f"{self.long['Ticker'].nunique()} unique tickers ever")


def _demo():
    for path in (NIFTY200, NIFTY500):
        uni = IndexUniverse(path)
        print(uni.summary())
        # show membership at three dates + churn between them
        d_old, d_new = "2008-01-15", "2022-01-15"
        a, b = uni.members_asof(d_old), uni.members_asof(d_new)
        print(f"   members {d_old}: {len(a)}   members {d_new}: {len(b)}")
        print(f"   dropped out (in {d_old}, gone by {d_new}): {len(a - b)} names")
        print(f"   e.g. dropped: {sorted(list(a - b))[:8]}")
        # daily mask sanity check on a synthetic 2010-2020 business-day index
        dates = pd.bdate_range("2010-01-01", "2020-12-31")
        mask = uni.daily_mask(dates)
        print(f"   daily_mask shape={mask.shape}; avg members/day={mask.sum(axis=1).mean():.0f}\n")


if __name__ == "__main__":
    _demo()
