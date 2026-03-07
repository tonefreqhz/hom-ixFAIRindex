METHOD NOTE (repeatability / reviewer)
====================================

This folder contains outputs produced by backtest_ew_crash_warning.py.

Purpose
-------
The figures/tables are intended to evaluate whether FAIR-based regime signals
provide *advance warning* ahead of exogenously defined "crisis regime onsets".

Key design choice (important)
-----------------------------
'Crisis starts' in this analysis are NOT detected from house price drawdowns.
They are MANUALLY defined, paper-aligned regime onset dates:

  MANUAL_CRISIS_STARTS = ['2007-09-30 00:00:00', '2019-09-30 00:00:00']

Rationale: nominal house prices may not exhibit a >=15% drawdown within a short horizon,
while affordability / stress regimes can worsen materially (the focus of this work).

Signals (current draft)
-----------------------
A: FAIR > 20 for 2 consecutive quarters
B: Î”FAIR > 5 for 2 consecutive quarters
C: FAIR > 0 AND Î”FAIR >= 0

Lead time definition
--------------------
For each crisis_start, we compute the last quarter prior to crisis_start where the
signal condition was true, then lead time is:

  lead_time_q = (crisis_start_quarter - signal_quarter) in quarters

False positives (evaluation policy)
-----------------------------------
Signals are scored for false positives only OUTSIDE excluded crisis-policy regimes:

  EXCLUDE_WINDOWS = [('2007-07-01', '2013-12-31'), ('2019-07-01', '2025-12-31')]

For a signal quarter t (outside excluded windows), it is counted as 'followed by crisis'
if any crisis_start occurs within [t, t + follow_window_q].

Files written (main)
--------------------
Paper assets:
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets\fig_price_and_fair_with_crash_starts.png :
  Price and FAIR series with vertical lines at MANUAL_CRISIS_STARTS.
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets\fig_avg_leadtime_by_signal.png :
  Bar chart of average lead time (quarters) by signal definition.
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets\ew_events_lead_times.csv :
  Row-per-crisis_start lead times for each signal (wide format).
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\draft_paper_assets\ew_summary.json :
  Summary metrics including false positive rates (eval-only) and configuration.

Datasets (reproducibility):
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\datasets\leadtime_by_signal_events.csv :
  Same as ew_events_lead_times.csv (canonical dataset output).
- C:\Users\peewe\OneDrive\Desktop\homeix\outputs\datasets\avg_leadtime_by_signal.csv :
  Aggregate table underlying the bar chart.

How to re-run
-------------
From the script directory:
  py .\backtest_ew_crash_warning.py

Edits you may make explicitly in the paper
------------------------------------------
- The exact MANUAL_CRISIS_STARTS quarters (and justification)
- The EXCLUDE_WINDOWS ranges (and justification)
- Signal thresholds (A/B/C) and follow_window_q
