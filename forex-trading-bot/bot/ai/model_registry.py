import time
import uuid
import hashlib
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from bot.storage.db import db

class ModelMetadata(BaseModel):
    id: str
    version: str
    model_type: str
    stage: str  # "CHAMPION", "CHALLENGER", "ARCHIVED"
    code_sha: str = "HEAD"
    dataset_version: str = "v1"
    feature_version: str = "v1"
    training_timestamp: str
    hyperparameters: Dict = Field(default_factory=dict)
    validation_accuracy: float = 0.0
    brier_score: float = 0.0
    log_loss: float = 0.0
    artifact_hash: str = ""

class ModelRegistry:
    """
    Persistent Model Registry managing versioned ML artifacts,
    Champion/Challenger stages, and statistically sound promotion gates.
    """

    def register_model(
        self,
        version: str,
        model_type: str,
        stage: str,
        hyperparameters: Dict,
        validation_accuracy: float,
        brier_score: float,
        log_loss: float,
        model_bytes: bytes,
        code_sha: str = "HEAD",
        dataset_version: str = "v1",
        feature_version: str = "v1"
    ) -> ModelMetadata:
        model_id = f"model_{uuid.uuid4().hex[:10]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        artifact_hash = hashlib.sha256(model_bytes).hexdigest()

        meta = ModelMetadata(
            id=model_id,
            version=version,
            model_type=model_type,
            stage=stage,
            code_sha=code_sha,
            dataset_version=dataset_version,
            feature_version=feature_version,
            training_timestamp=now,
            hyperparameters=hyperparameters,
            validation_accuracy=validation_accuracy,
            brier_score=brier_score,
            log_loss=log_loss,
            artifact_hash=artifact_hash
        )

        conn = db.get_connection()
        cursor = conn.cursor()

        # If this is champion, demote existing champion to ARCHIVED
        if stage == "CHAMPION":
            cursor.execute("UPDATE model_registry SET stage = 'ARCHIVED' WHERE stage = 'CHAMPION'")

        cursor.execute("""
            INSERT INTO model_registry (
                id, version, model_type, stage, code_sha, dataset_version,
                feature_version, training_timestamp, hyperparameters,
                validation_accuracy, brier_score, log_loss, artifact_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            meta.id, meta.version, meta.model_type, meta.stage, meta.code_sha,
            meta.dataset_version, meta.feature_version, meta.training_timestamp,
            str(meta.hyperparameters), meta.validation_accuracy, meta.brier_score,
            meta.log_loss, meta.artifact_hash
        ))
        conn.commit()
        conn.close()

        print(f"[ModelRegistry] Registered model {meta.version} as {meta.stage} (Brier: {brier_score:.4f})")
        return meta

    def get_champion(self) -> Optional[Dict]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_registry WHERE stage = 'CHAMPION' ORDER BY training_timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_challenger(self) -> Optional[Dict]:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_registry WHERE stage = 'CHALLENGER' ORDER BY training_timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def promote_challenger(
        self,
        challenger_id: str,
        min_accuracy: float = 55.0,
        max_brier_score: float = 0.25
    ) -> bool:
        """
        Promotes a challenger to champion ONLY if it passes strict validation gates.
        """
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_registry WHERE id = ?", (challenger_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        challenger = dict(row)
        acc = float(challenger["validation_accuracy"])
        brier = float(challenger["brier_score"])

        # Validation gates
        if acc < min_accuracy:
            print(f"[ModelRegistry] Promotion gate failed: Accuracy {acc:.2f}% < {min_accuracy}%")
            conn.close()
            return False

        if brier > max_brier_score:
            print(f"[ModelRegistry] Promotion gate failed: Brier score {brier:.4f} > {max_brier_score}")
            conn.close()
            return False

        # Demote existing champion
        cursor.execute("UPDATE model_registry SET stage = 'ARCHIVED' WHERE stage = 'CHAMPION'")
        # Promote challenger
        cursor.execute("UPDATE model_registry SET stage = 'CHAMPION' WHERE id = ?", (challenger_id,))
        conn.commit()
        conn.close()

        print(f"[ModelRegistry] 🏆 Promoted model {challenger['version']} ({challenger_id}) to CHAMPION!")
        return True

    def rollback_to_previous(self) -> bool:
        """Rolls back to the most recently archived champion."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_registry WHERE stage = 'ARCHIVED' ORDER BY training_timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        archived = dict(row)
        cursor.execute("UPDATE model_registry SET stage = 'ARCHIVED' WHERE stage = 'CHAMPION'")
        cursor.execute("UPDATE model_registry SET stage = 'CHAMPION' WHERE id = ?", (archived["id"],))
        conn.commit()
        conn.close()

        print(f"[ModelRegistry] ⏪ Rolled back to model {archived['version']} ({archived['id']})")
        return True

model_registry = ModelRegistry()
