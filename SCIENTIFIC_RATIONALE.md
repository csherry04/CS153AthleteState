# Scientific Rationale For Athlete-State Risk Scoring

## Purpose

This document summarizes the scientific ideas used to ground the project's athlete-state risk scoring layer. The goal is not to claim that the system can diagnose injury or precisely predict injury. Instead, the goal is to build a defensible monitoring framework that combines:

- recent workload
- sport-specific stress
- recovery markers
- longitudinal rest/strain patterns
- learned athlete-state embeddings

The core interpretation is:

> A day is not risky just because it is different from history. A day becomes more concerning when the athlete appears under-recovered relative to the workload they recently absorbed or the workload they are about to perform.

## 1. Training Load, Acute:Chronic Workload, And Workload Spikes

Training-load monitoring is commonly used to reason about whether an athlete is prepared for recent stress. Acute:chronic workload ratio (ACWR) compares recent workload against longer-term workload. In simple terms, the acute period estimates what the athlete recently did, while the chronic period estimates what the athlete has been prepared for.

The evidence is mixed. Systematic reviews suggest ACWR may be related to injury risk in some contexts, but the relationship varies substantially across sports, populations, workload definitions, and calculation methods. This means ACWR should be used as one feature in a broader monitoring system, not as a standalone injury predictor.

Relevant points from the literature:

- Maupin et al. reviewed ACWR and injury-risk studies and concluded that external and internal workload ratios may be related to injury risk, but findings are highly variable and ACWR methods need standardization before being used confidently as injury-prevention tools [1].
- Griffin et al. found support for ACWR as part of a broader multifactorial monitoring system, while emphasizing that time windows, workload variables, and model choice depend on sport context [2].
- Workload can be separated into external load, such as distance and duration, and internal load, such as heart-rate response or perceived effort. The same external workload may produce different internal responses depending on athlete readiness and fatigue state [1].

How this project uses it:

- We treat prior-day and recent 3-7 day workload as risk contributors.
- We do not treat high workload alone as automatically risky.
- Workload becomes more meaningful when paired with poor recovery markers.

## 2. HRV, Readiness, And Autonomic Recovery

Heart-rate variability (HRV) is widely used as a marker of autonomic regulation and recovery state. HRV-guided training research suggests that adjusting training intensity based on individual recovery state can improve endurance adaptation or reduce unnecessary high-intensity sessions.

Relevant points from the literature:

- Vesterinen et al. studied HRV-guided endurance training in recreational runners and found that the HRV-guided group improved 3000 m running performance while performing fewer moderate/high-intensity sessions than the predefined training group [3].
- Granero-Gallegos et al. performed a systematic review and meta-analysis of HRV-based training and found a positive effect of HRV-guided training on VO2max improvement in endurance athletes [4].
- HRV should be interpreted relative to the individual athlete's normal range and alongside other indicators. A single daily HRV value is less informative than trends and context [3].

How this project uses it:

- Recovery strain combines readiness, HRV, resting heart rate, sleep, and body-battery-style metrics where available.
- A low-activity day with stable recovery markers should not be treated as risky.
- A low-readiness or suppressed-HRV day after high workload is treated as more concerning.

## 3. Training Monotony, Strain, And Insufficient Rest

Risk can accumulate when high training load is repeated with too little variability or insufficient low-load recovery. Foster's training monotony and training strain concepts are useful here:

- Training monotony is commonly defined as mean daily training load divided by the standard deviation of daily load over a period, often one week.
- Training strain combines total load and monotony.

Relevant points from the literature:

- Foster described training monotony and strain as ways to relate sustained high load and low variability to negative adaptations, illness, and minor injury markers [5].
- High monotony is commonly discussed as a sign that training lacks enough variation or rest, especially when combined with high total load [5].

How this project uses it:

- The `insufficient_rest_score` is designed to capture repeated high workload and repeated low recovery.
- This is distinct from a single-day anomaly. It asks whether the athlete may have gone several days without enough restoration.

## 4. Running Versus Cycling: Sport-Specific Risk

The project should not treat every endurance activity as the same kind of risk. Running is weight-bearing and imposes repetitive musculoskeletal loading. Cycling can generate high metabolic fatigue with lower impact loading. Hiking sits somewhere in between, depending on duration, grade, descent, and load carriage.

The scientific nuance is important: simple "impact" metrics do not perfectly predict running injury. Running injury mechanisms are multifactorial and involve tissue capacity, training history, biomechanics, fatigue, recovery, and prior injury history.

Relevant points from the literature:

- Schmitz et al. found that vertical loading rate was not prospectively associated with running injury regardless of calculation method, highlighting that simple loading-rate metrics are not sufficient injury predictors [6].
- Biomechanical work suggests external force metrics may not directly represent internal tissue loading, because internal tissue stress depends on muscle forces, joint mechanics, anatomy, speed, slope, fatigue, and other factors [7].

How this project should use sport-specific weighting:

- Running should receive a higher tissue-load weight than cycling because it is weight-bearing and repetitive.
- Cycling should still contribute to fatigue and autonomic recovery risk, especially when long or intense.
- Running while under-recovered should be more concerning than cycling while under-recovered, because the musculoskeletal/tissue stress is likely higher.
- The system should avoid claiming that any single running impact metric directly predicts injury.

## 5. Preparedness Mismatch: The Central Project Hypothesis

The most useful risk concept for this project is preparedness mismatch:

> Risk increases when recent or planned workload exceeds what the athlete appears prepared to absorb, especially when recovery markers are suppressed.

This is more nuanced than anomaly detection. A rest day may be unusual but healthy. A hard running day when readiness, HRV, or resting HR are poor may be more concerning. A low-readiness day after a large bike ride may represent metabolic/autonomic fatigue, while a hard run under the same recovery state may represent both fatigue and tissue-load risk.

Proposed conceptual score:

```text
preparedness_mismatch =
    prior_workload_stress
    x recovery_strain
    x sport_specific_tissue_weight
    x insufficient_rest_context
```

Embedding novelty can support this interpretation, but should not dominate it:

```text
final_risk =
    preparedness_mismatch
    + accumulated_under_recovery
    + small novelty_residual_if_recovery_is_poor
```

## 6. Current Implementation Mapping

The current project implements the first version of this idea in `scripts/score_athlete_risk.py`.

Current components:

- `state_novelty_score`: normalized embedding anomaly score.
- `recovery_strain_score`: readiness, HRV, resting HR, sleep, and body battery deviations.
- `prior_workload_score`: previous-day and recent workload/duration/distance context.
- `rest_context_score`: detects easy/rest days so they are not automatically risky.
- `insufficient_rest_score`: repeated high load or low recovery across recent days.
- `risk_score`: final risk score weighted toward recovery strain after workload.

Important caveat:

The current implementation does not yet fully separate running, cycling, and hiking tissue load. That should be the next scientific upgrade.

## 7. Current Sport-Specific Extension

The project now adds sport-specific activity decomposition in `src/garmin_pipeline.py`:

- running duration, distance, heart rate, and activity count
- cycling duration, distance, heart rate, and activity count
- hiking duration, distance, heart rate, and activity count
- impact-weighted duration and distance
- fatigue-weighted duration

The weighting is intentionally conservative and heuristic:

- running receives the highest tissue-load weight because it is repetitive and weight-bearing
- hiking receives moderate tissue-load weight because grade, descent, and time-on-feet can matter
- cycling receives lower tissue-load weight but meaningful fatigue weight because it can drive large autonomic/metabolic fatigue with lower impact exposure

This distinction is important for interpretation. A large bike ride may create a next-day recovery problem, but it should not be treated the same as a hard run performed while under-recovered. The risk layer therefore separates:

- metabolic fatigue risk
- tissue-load risk
- autonomic recovery risk
- preparedness mismatch risk

These are not medical diagnoses. They are structured monitoring features designed to make the model's outputs more physiologically plausible and more useful for training decisions.

## 9. Bone-Stress Running Risk (Parallel Track)

General preparedness risk must stay sport-balanced: a large bike block can be metabolically stressful without implying the same musculoskeletal loading as running. For bone-stress and repetitive loading concerns, the project adds a **separate running-only track** that does not change the main `risk_score`.

This track is motivated by cases where sustained running volume accumulates even when daily readiness or HRV still look acceptable. Bone and connective tissue adaptation often lag behind cardiorespiratory fitness. It is scored across the **full daily feature history** (currently 2018–2026), not only the embedding modeling window.

### Literature basis

Bone stress injuries (BSIs) in runners occur when repetitive loading cycles and loading magnitude exceed tissue capacity [8]. Key ideas used here:

- **Volume (loading cycles):** More running distance/duration increases exposure in a roughly linear way [8].
- **Magnitude (speed / intensity):** BSI risk rises faster with running speed than with volume alone; small increases in tissue stress can sharply reduce fatigue life [8,9]. Napier et al. recommend progressing duration before intensity in mature athletes [8].
- **Internal load proxies:** Muscle-generated forces dominate internal bone loading relative to simple foot-ground impact metrics [7,8]. Heart rate, training effect, and speed are used here as imperfect internal-load proxies, not direct bone-stress measurements.
- **Workload spikes:** Acute:chronic load ratios and rapid load increases are common monitoring features, but must be individualized [1,2,8,10].
- **Monotony:** Repeated high running with too little variation or rest contributes to cumulative strain [5,8].
- **Holistic capacity:** Prior bone injury, energy availability, sleep, and nutrition modify tissue capacity but are not fully captured in Garmin-only features [10].

### Composite running bone-stress load (`running_bone_stress_load`)

Each day computes a running-only composite load unit from Garmin aggregates:

| Component | Weight | Rationale |
|---|---:|---|
| Distance (m) | 1.0 | Loading cycles / volume exposure [8] |
| Duration × speed (m²/s) | 0.45 | Speed/magnitude proxy; magnitude weighted below volume but above zero [8,9] |
| Elevation gain (m) | 1.0 | Uphill running increases musculoskeletal demand |
| Aerobic training effect | 2500 | Workout difficulty / internal load proxy |
| Anaerobic training effect | 5000 | Hard sessions weighted higher than easy aerobic work [8] |
| Avg HR × duration (hr) | 30 | Internal load proxy when training effect is missing |

Rolling 7-day and 28-day sums of this composite drive ACWR-style monitoring. Component scores now run on **three parallel tracks**:

| Track | What it uses | Role |
|---|---|---|
| **Literature** | Gabbett ACWR zones (0.8 / 1.3 / 1.5), Edwards speed bands (2.5 / 3.5 / 4.5 m/s), Foster monotony (>2.0) and strain [5,45] | Defensible objective monitoring |
| **Personalized** | Percentile scoring vs your own running history | Individualized progression detection |
| **Frontier** | TCN embedding novelty, readiness forecast error, similarity to labeled reference blocks | Multivariate learned-state signal |

The operational `bone_stress_risk_score` blends literature and personalized components (50/50 base, with spike terms). Where embeddings exist, `integrated_bone_stress_score` adds frontier strain (65% literature+personalized, 35% frontier). `scripts/compare_monitoring_signals.py` reports agreement and disagreement across tracks.

Implementation modules:

- `src/bone_stress_literature.py` — literature anchors
- `src/frontier_monitoring.py` — embedding / forecast-error signals

### Score components

| Component | What it captures |
|---|---|
| `running_7d_load_score` / `running_28d_load_score` | Recent composite running load vs baseline, capped by absolute weekly volume |
| `running_progression_score` | Rapid volume ramp / acute:chronic workload ratio [1,2,8,10] |
| `running_intensity_score` | Speed and internal load vs baseline, gated by absolute magnitude [8,9] |
| `running_workout_score` | Aerobic/anaerobic training-effect load, gated by absolute TE |
| `running_acwr_score` | `4 × 7-day load / 28-day load`, blended with absolute ACWR anchors |
| `running_monotony_score` | Repeated run days with too few off/easy days [5] |
| `run_under_recovered_score` | Hard running while recovery markers are suppressed [3,4] |

Final `bone_stress_risk_score` blends these channels (25% 7-day load, 18% 28-day load, 15% progression, 12% intensity, 12% workout, 10% ACWR, 8% monotony) and takes the higher of that blend, under-recovery interactions, and spike terms. Reason strings distinguish volume progression, sustained high volume, hard sessions, and intensity blocks rather than treating all elevated days as hard workouts. Days with <1 km in the last 7 days are capped low.

**Outputs:**
- `bone_stress_risk_score`, `bone_stress_risk_level`, `bone_stress_risk_reason`
- `accumulated_bone_stress_state` with slower decay than general risk (default 0.91)
- `bone_stress_carryover_score` (21-day rolling max of accumulated state)
- Full history file: `outputs/analysis/athlete_bone_stress_scores.csv`

Important caveats:
- This is **not** a bone-injury prediction model.
- Simple impact, speed, or distance metrics do not fully represent internal bone loading [6,7,8].
- Prior injury history (for example a spring 2024 bone-stress episode) should be treated as additional context outside wearable-only features [10].

## 10. Recommended Next Implementation

Add sport-specific load decomposition:

- `running_duration_seconds`
- `running_distance_m`
- `running_elevation_gain`
- `running_intensity_proxy`
- `cycling_duration_seconds`
- `cycling_distance_m`
- `cycling_intensity_proxy`
- `hiking_duration_seconds`
- `hiking_elevation_gain`
- `impact_weighted_duration`
- `impact_weighted_distance`
- `fatigue_weighted_load`

Then split risk into:

- `metabolic_fatigue_risk`: high cycling/running load plus poor recovery.
- `tissue_load_risk`: running/hiking impact-like exposure, especially after poor recovery.
- `autonomic_recovery_risk`: HRV/readiness/resting HR/sleep strain.
- `preparedness_mismatch_risk`: high workload demand while under-recovered.

This would make the project more scientifically meaningful and more novel than a generic wearable anomaly detector.

## References

[1] Maupin, D., Schram, B., Canetti, E., & Orr, R. (2020). The relationship between acute:chronic workload ratios and injury risk in sports: a systematic review. *Open Access Journal of Sports Medicine*, 11, 51-75. https://doi.org/10.2147/OAJSM.S231405

[2] Griffin, A., Kenny, I. C., Comyns, T. M., & Lyons, M. (2020). The association between the acute:chronic workload ratio and injury and its application in team sports: a systematic review. *Sports Medicine*, 50, 561-580. https://doi.org/10.1007/s40279-019-01218-2

[3] Vesterinen, V., Nummela, A., Heikura, I., Laine, T., Hynynen, E., Botella, J., & Hakkinen, K. (2016). Individual endurance training prescription with heart rate variability. *Medicine & Science in Sports & Exercise*, 48(7), 1347-1354. https://doi.org/10.1249/MSS.0000000000000910

[4] Granero-Gallegos, A., Gonzalez-Quilez, A., Plews, D., & Carrasco-Poyatos, M. (2020). HRV-based training for improving VO2max in endurance athletes: a systematic review with meta-analysis. *International Journal of Environmental Research and Public Health*, 17(21), 7999. https://doi.org/10.3390/ijerph17217999

[5] Foster, C. (1998). Monitoring training in athletes with reference to overtraining syndrome. *Medicine & Science in Sports & Exercise*, 30(7), 1164-1168. https://journals.lww.com/acsm-msse/fulltext/1998/07000/monitoring_training_in_athletes__with_reference_to.23.aspx

[6] Schmitz, E. A., Wille, C. M., Stiffler-Joachim, M. R., Kliethermes, S. A., & Heiderscheit, B. C. (2022). Vertical loading rate is not associated with running injury, regardless of calculation method. *Medicine & Science in Sports & Exercise*, 54(8), 1382-1388. https://doi.org/10.1249/MSS.0000000000002917

[7] Matijevich, E. S., Branscombe, L. M., Scott, L. R., & Zelik, K. E. (2020). Combining wearable sensor signals, machine learning and biomechanics to estimate tibial bone force and damage during running. *Computer Methods in Biomechanics and Biomedical Engineering*, 23(10), 451-461. https://doi.org/10.1080/10255842.2020.1751064

[8] Napier, C., Willy, R. W., & Taunton, J. E. (2021). Preventing bone stress injuries in runners with optimal workload. *Current Osteoporosis Reports*, 19, 298-307. https://doi.org/10.1007/s11914-021-00666-y

[9] Edwards, W. B., Taylor, D., Rudolphi, T. J., Gillette, J. C., & Derrick, T. R. (2010). Effects of running speed on a probabilistic stress fracture model. *Clinical Biomechanics*, 25(4), 372-377. https://doi.org/10.1016/j.clinbiomech.2010.01.001

[10] Tenforde, A. S., Hamstra-Wright, K. L., Kim, J. H., & Hulstyn, M. J. (2021). Training load capacity, cumulative risk, and bone stress injuries: a narrative review of a holistic approach. *Frontiers in Sports and Active Living*, 3, 665683. https://doi.org/10.3389/fspor.2021.665683
