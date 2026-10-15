# Reflection

The hardest cases are small distribution shifts, feature skew, and corpus drift. Their values can stay inside the published three-sigma limits, close to ordinary clean variation. Runtime and freshness delays have the same ambiguity. I use narrower thresholds for those numerical signals, while schema and type violations and graph mismatches have direct checks. Narrower thresholds can catch more subtle faults but also create false alerts.

Each event calls only its corresponding toolkit method. I accept a small budget overage to keep checking late events, since the score also rewards catching their faults. With another pass, I would compare false alerts against missed faults across several streams, then adjust thresholds by metric. I would also keep a small history of clean-looking values in `ctx.state` to estimate each stream's usual range. That could help with subtle faults, but only after enough observations and with care not to learn from undetected faulty events.
