V14 PHASE TRANSITION DETECTOR - HOME + FINDER

What changed:
- Added tabs/home_split/v14_phase_transition_detector.py
- Installed it after V13 in tabs/home_split/doo_prime_deep.py

Purpose:
The old 10-Reversal Decision stays unchanged and still detects reversal danger.
V14 adds an earlier detector for:
Strong trend -> momentum fading -> impulse compression -> accumulation/distribution -> breakout preparation -> possible new one-way trend 2-3 hours later.

New locked table columns:
- phase_transition_score
- phase_transition_raw
- phase_transition_state
- expected_expansion_window
- phase_trend_before
- trend_exhaustion
- impulse_compression
- accumulation_distribution
- breakout_pressure
- breakout_pressure_side
- order_block_rejection
- breakout_already_happened
- body_compression_ratio
- range_compression_ratio
- efficiency_prev_%
- efficiency_now_%
- efficiency_delta
- trend_move_%
- current_hour_move_%
- phase_reasons
- phase_no_future

Score meaning:
1-3  = Normal Trend
4-5  = Momentum Loss
6-7  = Accumulation / Distribution
8-9  = Breakout Preparation
10   = Transition Zone

Important:
- Uses only closed-hour/current-and-previous data.
- Does not use future candles.
- If breakout already happened, the phase score is capped at 6 so late moves are not called early preparation.
