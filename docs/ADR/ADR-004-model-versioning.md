# ADR-004: Model Registry, Walk-Forward Validation & Safe Retraining

## Status
Accepted

## Context
The legacy model training pipeline in `bot/ai/ml_engine.py` suffered from:
1. Evaluating training accuracy on the exact same dataset used for training (100% false accuracy).
2. Knee-jerk retraining on individual losing trades with a 4.0x mistake multiplier, distorting the decision boundary based on noise.
3. No artifact versioning, no dataset hashing, no champion/challenger governance, and no model rollback capability.

## Decision
1. **Walk-Forward Validation Protocol**:
   - Time-series data must strictly avoid shuffle splits.
   - Use chronological split: `Train` (60%) ➔ `Validation` (20%) ➔ `Out-of-Sample Walk-Forward` (20%).
   - Performance evaluation must include realistic trading friction (spread, commission, slippage).
2. **Model Registry (`ModelRegistry`)**:
   - Models are registered with metadata:
     - `model_id`: UUIDv4
     - `version`: SemVer (e.g. `1.0.0`)
     - `code_commit_sha`: Git commit hash
     - `dataset_hash`: SHA256 of training dataset
     - `feature_version`: Canonical feature set version
     - `created_at`: UTC timestamp
     - `validation_metrics`: Brier score, log-loss, expected value, profit factor
     - `status`: `CHAMPION`, `CHALLENGER`, `ARCHIVED`, `ROLLED_BACK`
3. **Decoupled Retraining Policy**:
   - Retraining is triggered on statistical drift or accumulated batch windows (e.g. minimum 100 new closed trades or weekly scheduled walk-forward review).
   - A newly trained `CHALLENGER` model must beat the `CHAMPION` on untouched out-of-sample data before automated promotion.
   - Instant 1-click or automated rollback to previous `CHAMPION` on degraded live performance.

## Consequences
- Prevents catastrophic overfitting and regime overreaction.
- Ensures reproducibility and auditability of all AI decisions.
