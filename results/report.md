# abkit demo

Eight synthetic experiments, seven implanted defects. Bold values are
flags; each lands on the row where its defect was implanted.

| experiment | implanted defect | SRM p | contam. | fragility | look FPR | novelty gap | uncorrected | exagg. | flags |
|---|---|---|---|---|---|---|---|---|---|
| clean | nothing | 0.89 | 0 | 20 | - | -0.02 | - | 1.0 | none |
| traffic-leak | 3% of traffic diverted to treatment | **4.1e-14** | 0 | 20 | - | -0.02 | - | 1.0 | sample ratio mismatch |
| double-dipper | 25 units assigned to both arms | 0.67 | **25** | 20 | - | -0.03 | - | 1.0 | assignment contamination |
| whale-driven | 3 extreme units carry the significance | 0.11 | 0 | **1** | - | 0.26 | - | 1.2 | outlier fragility |
| peeker | null effect, stopped at the first significant look | 0.55 | 0 | 8 | **0.19** | -0.17 | - | 1.2 | peeking |
| fading-novelty | early-half effect 0.30, late-half effect 0.00 | 0.041 | 0 | 20 | - | **0.31** | - | 1.0 | novelty |
| metric-fisher | null effect, 40 secondary metrics tested | 0.054 | 0 | 0 | - | -0.11 | **2** | 3.4 | uncorrected winners |
| underpowered-winner | true effect 0.1, powered for 0.14 of that chance | 0.91 | 0 | 8 | - | -0.38 | - | **2.7** | winner's curse |

##  clean

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.2163 | [0.1720, 0.2606] | 9.57 | 0 | 4006/3994 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.89 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | 0.02 SMD | [-0.02, 0.07] | [-0.1, 0.1] | - |
| outlier fragility | 20 units | - | > 3 units to overturn | - |
| novelty | -0.02 SD | [-0.11, 0.06] | [-0.1, 0.1] | - |
| winner's curse | 1.00 x | - | power >= 0.5 | - |
| variance ratio | 1.06 ratio | [1.00, 1.13] | descriptive | - |
| CUPED headroom | 37% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=8000): observed control 0.4993, treatment 0.5008 vs intended control 0.5000, treatment 0.5000 (chi2 0.02); flags below p=0.001
- **assignment contamination** (n=8000): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=8000): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=8000): removing 20 most extreme units does not overturn significance
- **novelty** (n=8000): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=8000): power 1.00 at the design MDE of 0.2; a significant estimate is expected to overstate the true effect by 1.0x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=8000): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=8000): CUPED on pre-experiment 'pre_outcome' would have removed 37% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

No probe left its innocent range.

##  traffic-leak

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.2022 | [0.1582, 0.2462] | 9.01 | 0 | 4338/3662 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 4.1e-14 | - | p >= 0.001 | **FLAG** |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | -0.01 SMD | [-0.06, 0.03] | [-0.1, 0.1] | - |
| outlier fragility | 20 units | - | > 3 units to overturn | - |
| novelty | -0.02 SD | [-0.11, 0.07] | [-0.1, 0.1] | - |
| winner's curse | 1.00 x | - | power >= 0.5 | - |
| variance ratio | 0.98 ratio | [0.92, 1.04] | descriptive | - |
| CUPED headroom | 34% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=8000): observed control 0.4577, treatment 0.5423 vs intended control 0.5000, treatment 0.5000 (chi2 57.12); flags below p=0.001
- **assignment contamination** (n=8000): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=8000): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=8000): removing 20 most extreme units does not overturn significance
- **novelty** (n=8000): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=8000): power 1.00 at the design MDE of 0.2; a significant estimate is expected to overstate the true effect by 1.0x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=8000): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=8000): CUPED on pre-experiment 'pre_outcome' would have removed 34% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **sample ratio mismatch**: observed control 0.4577, treatment 0.5423 vs intended control 0.5000, treatment 0.5000 (chi2 57.12); flags below p=0.001

##  double-dipper

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.1849 | [0.1234, 0.2465] | 5.89 | 3.9e-09 | 2026/1999 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.67 | - | p >= 0.001 | - |
| assignment contamination | 25 units | - | 0 units | **FLAG** |
| covariate balance (pre_outcome) | -0.01 SMD | [-0.07, 0.06] | [-0.1, 0.1] | - |
| outlier fragility | 20 units | - | > 3 units to overturn | - |
| novelty | -0.03 SD | [-0.14, 0.09] | [-0.1, 0.1] | - |
| winner's curse | 1.00 x | - | power >= 0.5 | - |
| variance ratio | 1.04 ratio | [0.94, 1.14] | descriptive | - |
| CUPED headroom | 35% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=4025): observed control 0.4966, treatment 0.5034 vs intended control 0.5000, treatment 0.5000 (chi2 0.18); flags below p=0.001
- **assignment contamination** (n=4000): 25 unit ids appear in more than one arm; e.g. u0, u1, u10
- **covariate balance (pre_outcome)** (n=4025): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=4025): removing 20 most extreme units does not overturn significance
- **novelty** (n=4025): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=4025): power 1.00 at the design MDE of 0.2; a significant estimate is expected to overstate the true effect by 1.0x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=4025): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=4025): CUPED on pre-experiment 'pre_outcome' would have removed 35% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **assignment contamination**: 25 unit ids appear in more than one arm; e.g. u0, u1, u10

##  whale-driven

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.1596 | [0.0036, 0.3156] | 2.01 | 0.045 | 527/476 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.11 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | -0.05 SMD | [-0.16, 0.09] | [-0.1, 0.1] | - |
| outlier fragility | 1 units | - | > 3 units to overturn | **FLAG** |
| novelty | 0.26 SD | [0.03, 0.48] | [-0.1, 0.1] | - |
| winner's curse | 1.19 x | - | power >= 0.5 | - |
| variance ratio | 2.42 ratio | [1.12, 4.33] | descriptive | - |
| CUPED headroom | 23% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=1003): observed control 0.4746, treatment 0.5254 vs intended control 0.5000, treatment 0.5000 (chi2 2.59); flags below p=0.001
- **assignment contamination** (n=1003): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=1003): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=1003): removing the 1 most extreme units lifts the primary p above alpha; flags at 3 or fewer
- **novelty** (n=1003): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=1003): power 0.71 at the design MDE of 0.2; a significant estimate is expected to overstate the true effect by 1.2x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=1003): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=1003): CUPED on pre-experiment 'pre_outcome' would have removed 23% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **outlier fragility**: removing the 1 most extreme units lifts the primary p above alpha; flags at 3 or fewer

##  peeker

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.0971 | [0.0172, 0.1771] | 2.38 | 0.017 | 1265/1235 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.55 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| outlier fragility | 8 units | - | > 3 units to overturn | - |
| peeking | 0.19 FPR | - | FPR <= 1.5x alpha | **FLAG** |
| novelty | -0.17 SD | [-0.32, -0.02] | [-0.1, 0.1] | - |
| winner's curse | 1.23 x | - | power >= 0.5 | - |
| variance ratio | 1.07 ratio | [0.96, 1.20] | descriptive | - |

### Details

- **sample ratio mismatch** (n=2500): observed control 0.4940, treatment 0.5060 vs intended control 0.5000, treatment 0.5000 (chi2 0.36); flags below p=0.001
- **assignment contamination** (n=2500): 0 unit ids appear in more than one arm
- **outlier fragility** (n=2500): removing the 8 most extreme units lifts the primary p above alpha; flags at 3 or fewer
- **peeking** (n=2500): stopping at the first significant look across 10 looks has a true false-positive rate of 0.194 against a nominal alpha of 0.05; flags when significant and FPR exceeds 1.5x alpha
- **novelty** (n=2500): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=2500): power 0.66 at the observed effect (an optimistic bound); a significant estimate is expected to overstate the true effect by 1.2x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=2500): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)

## Skipped checks

- **covariate balance**: no pre-experiment covariates; log them per unit as pre: {"metric": value} to enable this check
- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **CUPED headroom**: no pre-experiment covariates logged

## Verdict

1 flag(s):

- **peeking**: stopping at the first significant look across 10 looks has a true false-positive rate of 0.194 against a nominal alpha of 0.05; flags when significant and FPR exceeds 1.5x alpha

##  fading-novelty

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.1617 | [0.1116, 0.2118] | 6.32 | 2.5e-10 | 2921/3079 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.041 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | 0.04 SMD | [-0.01, 0.09] | [-0.1, 0.1] | - |
| outlier fragility | 20 units | - | > 3 units to overturn | - |
| novelty | 0.31 SD | [0.21, 0.41] | [-0.1, 0.1] | **FLAG** |
| winner's curse | 1.00 x | - | power >= 0.5 | - |
| variance ratio | 1.01 ratio | [0.94, 1.08] | descriptive | - |
| CUPED headroom | 35% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=6000): observed control 0.5132, treatment 0.4868 vs intended control 0.5000, treatment 0.5000 (chi2 4.16); flags below p=0.001
- **assignment contamination** (n=6000): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=6000): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=6000): removing 20 most extreme units does not overturn significance
- **novelty** (n=6000): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=6000): power 1.00 at the design MDE of 0.15; a significant estimate is expected to overstate the true effect by 1.0x (wrong sign with probability 0.000); flags when the result is significant with power below 0.5
- **variance ratio** (n=6000): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=6000): CUPED on pre-experiment 'pre_outcome' would have removed 35% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **novelty**: first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect

##  metric-fisher

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.0320 | [-0.0563, 0.1203] | 0.71 | 0.48 | 1043/957 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.054 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | 0.03 SMD | [-0.06, 0.12] | [-0.1, 0.1] | - |
| outlier fragility | 0 units | - | > 3 units to overturn | - |
| uncorrected winners | 2 metrics | - | 0 metrics | **FLAG** |
| novelty | -0.11 SD | [-0.30, 0.06] | [-0.1, 0.1] | - |
| winner's curse | 3.43 x | - | power >= 0.5 | - |
| variance ratio | 0.95 ratio | [0.84, 1.07] | descriptive | - |
| CUPED headroom | 35% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=2000): observed control 0.4785, treatment 0.5215 vs intended control 0.5000, treatment 0.5000 (chi2 3.70); flags below p=0.001
- **assignment contamination** (n=2000): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=2000): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=2000): primary result is not significant, so there is nothing to overturn
- **uncorrected winners** (n=41): 2 of 41 tested metrics are significant raw but not after Benjamini-Hochberg: m13, m27
- **novelty** (n=2000): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=2000): power 0.11 at the observed effect (an optimistic bound); a significant estimate is expected to overstate the true effect by 3.4x (wrong sign with probability 0.035); flags when the result is significant with power below 0.5
- **variance ratio** (n=2000): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=2000): CUPED on pre-experiment 'pre_outcome' would have removed 35% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **uncorrected winners**: 2 of 41 tested metrics are significant raw but not after Benjamini-Hochberg: m13, m27

##  underpowered-winner

## Primary readout

| metric | effect | 95% CI | z | p | n (treatment/control) |
|---|---|---|---|---|---|
| outcome | 0.3149 | [0.1004, 0.5293] | 2.88 | 0.004 | 149/151 |

## Probes

| probe | value | 95% CI | innocent | flag |
|---|---|---|---|---|
| sample ratio mismatch | 0.91 | - | p >= 0.001 | - |
| assignment contamination | 0 units | - | 0 units | - |
| covariate balance (pre_outcome) | 0.04 SMD | [-0.18, 0.25] | [-0.1, 0.1] | - |
| outlier fragility | 8 units | - | > 3 units to overturn | - |
| novelty | -0.38 SD | [-0.83, 0.07] | [-0.1, 0.1] | - |
| winner's curse | 2.71 x | - | power >= 0.5 | **FLAG** |
| variance ratio | 0.98 ratio | [0.73, 1.34] | descriptive | - |
| CUPED headroom | 33% | - | descriptive | - |

### Details

- **sample ratio mismatch** (n=300): observed control 0.5033, treatment 0.4967 vs intended control 0.5000, treatment 0.5000 (chi2 0.01); flags below p=0.001
- **assignment contamination** (n=300): 0 unit ids appear in more than one arm
- **covariate balance (pre_outcome)** (n=300): pre-experiment pre_outcome: treatment minus control in pooled-SD units
- **outlier fragility** (n=300): removing the 8 most extreme units lifts the primary p above alpha; flags at 3 or fewer
- **novelty** (n=300): first-half minus second-half effect on the primary metric, in pooled-SD units; a nonzero gap means the single reported number averages over a changing effect
- **winner's curse** (n=300): power 0.15 at the design MDE of 0.1; a significant estimate is expected to overstate the true effect by 2.7x (wrong sign with probability 0.014); flags when the result is significant with power below 0.5
- **variance ratio** (n=300): treatment variance over control variance on the primary metric; a shift here means the treatment changes the distribution, not just the mean (descriptive, never flags)
- **CUPED headroom** (n=300): CUPED on pre-experiment 'pre_outcome' would have removed 33% of the primary metric's variance — the confidence interval could have been that much tighter (descriptive, never flags)

## Skipped checks

- **uncorrected winners**: fewer than two tested metrics; list them in design.metrics if more were tested than logged
- **peeking**: no interim looks recorded; log each analysis as design.looks = [{n, z}, ...] to enable this check

## Verdict

1 flag(s):

- **winner's curse**: power 0.15 at the design MDE of 0.1; a significant estimate is expected to overstate the true effect by 2.7x (wrong sign with probability 0.014); flags when the result is significant with power below 0.5
