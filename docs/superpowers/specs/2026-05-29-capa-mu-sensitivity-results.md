# CAPA μ Sensitivity — Results

Date: 2026-05-30. λ-mode with tuned `λ_c = λ_p = 0.4`, local keeps `(1−μ)·fare` on cross.
Light cross design: μ-sweep at r=0.5, r-sweep at μ=0.7. Shared canonical seed per preset.

## Headline

- **total TR decreases monotonically in μ** (both presets). At realistic scale CAMA matches
  most parcels locally (local keeps `(1−ζ)=0.8·fare`); raising μ diverts parcels local→cross
  where local keeps only `(1−μ)·fare < 0.8·fare`, plus DAPA-rejected parcels at low μ are
  rescued locally on retry. So total TR is maximized at the lowest μ.
- **cross_TR (cross-platform revenue) has the interior peak** — the intended μ mechanism:
  low μ → cooperating platform refuses (bid > μ·fare) → tiny cross; high μ → `(1−μ)` penalty.
  Peak at **μ=0.7 (ny)** / **μ=0.6 (formal)** — scale shifts the optimum slightly left.

## ny @ 5000

μ-curve (r=0.5):

| μ | total_TR | local_TR | cross_TR | CR |
|---|---|---|---|---|
|0.5|25685.7|25419.6|266.1|0.730|
|0.6|24849.5|22420.9|2428.6|0.770|
|0.7|22286.9|19158.5|**3128.3**|0.777|
|0.8|21214.7|19143.2|2071.5|0.775|
|0.9|20179.0|19143.2|1035.8|0.775|

cross_TR peak @ μ=0.7.

r-curve (μ=0.7):

| r | total_TR | local_TR | cross_TR | CR |
|---|---|---|---|---|
|0.2|25811.7|25811.7|0.0|0.729|
|0.3|24438.4|22604.8|1833.6|0.776|
|0.4|22184.5|18966.7|**3217.8**|0.778|
|0.5–0.8|22286.9|19158.5|3128.3|0.777|

cross_TR peak @ r=0.4, then plateau (μ1 large enough that courier bids all pass validity).

## formal @ 50000

μ-curve (r=0.5):

| μ | total_TR | local_TR | cross_TR | CR |
|---|---|---|---|---|
|0.5|285916.1|277164.9|8751.1|0.825|
|0.6|282585.3|267348.8|**15236.5**|0.844|
|0.7|279028.0|267694.3|11333.7|0.845|
|0.8|275250.1|267694.3|7555.8|0.845|
|0.9|271472.2|267694.3|3777.9|0.845|

cross_TR peak @ μ=0.6.

r-curve (μ=0.7):

| r | total_TR | local_TR | cross_TR | CR |
|---|---|---|---|---|
|0.2|284555.1|284555.1|0.0|0.808|
|0.3|278507.1|265383.0|**13124.1**|0.852|
|0.4|279288.1|268054.2|11233.8|0.846|
|0.5–0.8|279028.0|267694.3|11333.7|0.845|

cross_TR peak @ r=0.3, then plateau.

## Reading

- The r=0.2 column has cross_TR=0: courier share μ1 = 0.2·0.7 = 0.14 is too low, every FPSA
  courier bid exceeds μ1·fare and is invalidated, so no cross matches form — pure courier-side
  refusal. cross_TR climbs sharply once r (hence μ1) clears the courier validity cap, then
  plateaus.
- Default (μ=0.7, r=0.5) sits on the cross_TR plateau for r and near the cross_TR peak for μ;
  it is a reasonable operating point though formal's cross_TR peak is μ=0.6.

Aggregates: `outputs/plots/sens_mu_{ny_5000,formal_50000}/aggregate_{preset}.json`.
Per-point summaries: `outputs/plots/sens_mu_{preset}_{point}/<label>/summary.json`.
