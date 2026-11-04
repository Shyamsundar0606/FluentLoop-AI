"""No numeric output until an independently calibrated French assessor exists."""

from typing import Protocol


class AcousticAssessor(Protocol):
    def assess(self, audio: bytes, target_text: str) -> dict: ...


class UnavailableAcousticAssessor:
    def assess(self, audio: bytes, target_text: str) -> dict:
        return {
            "assessment_status": "not_available",
            "acoustic_quality_measure": None,
            "phoneme_feedback": [],
            "model_identifier": None,
            "score_calibration_version": None,
        }
