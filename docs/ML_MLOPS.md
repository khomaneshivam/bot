# Machine Learning & MLOps Governance Specification

## 1. Validation Methodology & Leakage Prevention

Financial time-series data possesses temporal autocorrelation and non-stationarity. Standard cross-validation techniques (such as `KFold` with shuffle) introduce severe lookahead bias and target leakage.

### 1.1 Strict Chronological Validation Split
Every model training sequence executes a time-ordered partition:
```
[================ TRAIN (60%) ================] [=== VALIDATION (20%) ===] [=== UNTOUCHED OUT-OF-SAMPLE (20%) ===]
                     |                                       |                                   |
              Fit Scaler & Trees                     Hyperparameter Tuning              Final Performance Gate
```
- **Preprocessing Leakage Prevention**: `RobustScaler` and feature scalers are fitted **strictly** on the `Train` fold. Validation and out-of-sample data are transformed using train parameters only.
- **Target Leakage Prevention**: Future target lookahead windows (`forward_bars = 4`) exclude the final 4 bars of each split.

---

## 2. Model Registry & Champion/Challenger Governance

```
                    NEW TRAINING BATCH
                            |
                            v
               CHALLENGER MODEL EVALUATION
            - Out-of-Sample Brier Score
            - Profit Factor with Friction (Spread + Slippage)
            - Max Drawdown on Validation Period
                            |
                            v
               PROMOTION VALIDATION GATE
           Is Challenger Sharpe > Champion Sharpe
           AND Challenger Profit Factor > 1.25?
                  /                  \
             YES /                    \ NO
                v                      v
    PROMOTE TO CHAMPION         DISCARD / ARCHIVE
    Archive previous Champion     Retain existing Champion
```

### 2.1 Model Registry Metadata Schema
Each model artifact is saved with:
- `model_id`: UUIDv4 identifier
- `version`: Semantic version string
- `commit_sha`: Git commit hash of code used to generate the model
- `dataset_hash`: SHA256 digest of input dataset
- `feature_set_version`: Canonical feature definition version
- `trained_at_utc`: UTC timestamp
- `metrics`:
  - `out_of_sample_accuracy`: Percentage
  - `brier_score`: Probability calibration error
  - `simulated_profit_factor`: Post-friction trading performance
- `status`: `CHAMPION` | `CHALLENGER` | `ARCHIVED` | `ROLLED_BACK`

---

## 3. Probability Calibration vs. Confidence Scoring

Raw outputs from decision tree ensembles or heuristics cannot be reported as empirical win probabilities without statistical calibration.
- **Uncalibrated Model Scores**: Must be explicitly labeled in telemetry and UI as `confidence_score` (ranging 0.0 to 1.0).
- **Calibrated Probabilities**: Fitted via isotonic regression or Platt scaling on the holdout validation set. Evaluated using the **Brier Score**:
$$BS = \frac{1}{N} \sum_{t=1}^N (f_t - o_t)^2$$
Where $f_t$ is the forecast probability and $o_t \in \{0, 1\}$ is the actual outcome.

---

## 4. Retraining Policy

- **Elimination of Single-Loss Retraining**: The bot will NOT retrain upon individual losing trades.
- **Batch Retraining Trigger**: Scheduled upon accumulation of ≥ 100 verified closed trades or significant feature distribution drift (Kolmogorov-Smirnov test $p < 0.01$).
