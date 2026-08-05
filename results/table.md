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
