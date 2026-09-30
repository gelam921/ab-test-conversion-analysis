# Marketing A/B Test: Ads vs. PSA — Findings & Recommendation

## TL;DR

Ads beat PSA on conversion — and it's a real effect, not noise. It holds up even after controlling for how many ads someone saw, so it's not just "more messaging = more sales." No cost data here, though, so this confirms the effect is real, not that it's profitable — that needs ad spend and margin numbers layered on top.

## The question

Does showing ads (vs. a neutral PSA) actually drive more conversions, or is the gap we see just noise?

## Findings

**1. Ad group converts meaningfully more than PSA.**

| | Users | Conversions | Conversion rate |
|---|---|---|---|
| Ad | 564,577 | 14,423 | 2.55% |
| PSA | 23,524 | 420 | 1.79% |

0.77pt gap, 43% relative lift. A gap this size happening by chance: about 1 in 5.8 trillion. 95% CI for the true lift: 0.60–0.94 points.

**2. The lift isn't just "ad group saw more ads."**

Ad-group users were shown more messaging overall than PSA users, so the obvious follow-up: is the whole effect just volume? No — controlling for total ad exposure, being shown an ad vs. a PSA still means ~48% higher odds of converting. The content itself, not just the quantity, matters.

**3. Conversion climbs hard with exposure — but this one's correlational, not causal.**

Top 10% by exposure: 14.46% conversion. Bottom 10%: 0.15%. Striking, but unlike Finding 1, exposure volume wasn't randomly assigned — people already inclined to buy likely browsed more and got served more ads as a result. This is a candidate for its own randomized experiment, not a green light to just max out ad frequency.

## Recommendation

Ads over PSA is well-supported — real effect, large enough to matter. Before scaling spend, pair this with actual cost-per-ad and margin-per-conversion, since this dataset can't speak to ROI alone. Test exposure frequency (Finding 3) as its own randomized experiment before acting on it.

## Limitations

- No cost/revenue data — this answers "is it real," not "is it worth it."
- `total_ads`, `most_ads_day`, `most_ads_hour` are behavior, not randomized — Finding 3 is correlational.
- Day-of-week pattern (Monday highest, Saturday lowest) shows up in *both* groups — looks like general engagement, not an ad effect. Not dug into further here.

---

## Methodology

**Data:** 588,101 users, real marketing experiment (Kaggle, "Marketing A/B Testing"). Ad vs. PSA, `converted` = purchased.

**Test 1 — Two-proportion z-test**
Z = 7.370, p = 1.71×10⁻¹³. 95% CI: [0.595%, 0.943%]. Proportion test, not t-test, since the outcome is binary.

**Test 2 — Logistic regression** (`converted ~ is_ad + total_ads`)
`is_ad`: OR = 1.476, CI [1.33, 1.63], p < 0.001. `total_ads`: OR = 1.0102/ad, p < 0.001. Run to check whether Test 1's effect was confounded by exposure — it wasn't; both hold independently.

**Exploratory — exposure deciles** (`NTILE(10)` in SQL)
0.15% → 14.46% across deciles, steepest at the top — motivated the confound check in Test 2.

All queries and code in `analysis/`.
