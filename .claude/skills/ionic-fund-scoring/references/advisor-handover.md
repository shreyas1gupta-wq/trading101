# Advisor handover

Two attachments, sent as a pair: `ionic_scores_<date>.csv` and `VERSION.json`. Nothing in
the email names a client or quotes a holding. Nothing from `method.md`, `rulings.md`,
`defects.md` or `boundary.md` goes with it.

---

**Subject:** Portfolio review decks from a holding statement

Hi,

You can now produce a full Ionic Wealth portfolio review deck from a client's holding
statement without going through me. Claude Code does the work; you supply the statement.

**One-time setup**

```
git clone https://github.com/shreyas1gupta-wq/ionic-scorecard.git
```

Copy the two files attached to this mail into `ionic-scorecard/ionic-deck-kit/scores/`.
They are the firm's current fund scores and calls. Keep them to yourself and do not
forward them.

You need Python with `pandas`, `openpyxl`, `python-pptx` and `matplotlib`.

**Each review**

Open Claude Code in the `ionic-scorecard` folder and ask it to build a review from the
statement, or run it yourself:

```
python ionic-deck-kit/build/build_review.py <statement.xlsx> --client "Family Name"
```

Three files land in `ionic-deck-kit/out/`: the deck, a workbook of every holding with its
call and rationale, and an exceptions file if anything could not be resolved.

`--tier HNI_DEEP` is the full deck and the default. `--tier STANDARD` and
`--tier RM_SIMPLE` are shorter cuts of the same material.

The statement can be a CAS, a CAMS or Kfintech export, or an AMC's own. It reads holdings
by ISIN rather than by column position, so an unfamiliar layout, a title block above the
header or a total row at the bottom are all fine.

**Three lines of output to read before you send anything**

*Reconciliation.* It adds up what it read and compares that against the total the
statement prints for itself. If it says MISMATCH the deck is built on a partial read and
every number on it is wrong.

*Schemes absent from the score file.* They come out as No View, which is correct behaviour
rather than a failure. If a large holding comes back No View, ask me whether it should be
covered.

*Exceptions.* Rows carrying money that could not be tied to a scheme. Send them back to me
rather than ignoring them.

If you ever see a block of exclamation marks saying the calls are invented demo data, the
score files are not in place. Stop and come back to me for a current pair.

**The calls are not yours or Claude's to set**

Sell, Trim, Hold, Hold (watch) and No View come from the score file, keyed on ISIN. The
kit renders them. It holds no scoring logic at all, so neither you nor Claude can derive a
call, fill a gap with judgement, or override one that looks wrong for a client. If a call
does look wrong, that is a conversation with me and it may well be a good one.

A scheme missing from the file gets No View rather than a guess. Two share classes of the
same scheme always carry the same call.

**Check the date**

`VERSION.json` carries the as-of date and the deck prints it. I refresh on the desk's own
cadence. If what you are holding is months old, ask for a newer pair before it goes to a
client.

The score describes a fund's record against its own category. It is not a forecast, so
please don't let a conversation turn it into one.

`ionic-deck-kit/README.md` covers the rest. Run the three checks in `ionic-deck-kit/qa/`
before sending; a geometry finding means content is off the page or overlapping.

Shout if anything does not run.

Shreyas
