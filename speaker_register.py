import os
import numpy as np
import tempfile
import soundfile as sf

import nemo.collections.asr as nemo_asr
from utils import get_logger

logger = get_logger("speaker")

from config import (
    AUDIO_SR as SR,
    SPEAKER_EMBED_PATH as EMBED_PATH,
    SPEAKER_HIGH_THRESHOLD as HIGH_THRESHOLD,
    SPEAKER_LOW_THRESHOLD as LOW_THRESHOLD
)


class SpeakerVerifier:
    """TitaNet-based speaker verification"""

    def __init__(self, embed_path: str = EMBED_PATH):
        self.embed_path = embed_path

        logger.info("Loading TitaNet model...")
        self.model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(
            model_name="titanet_large"
        )
        logger.info("TitaNet ready ✓")

        self.driver_embed = None

        if os.path.isfile(self.embed_path):
            try:
                self.driver_embed = np.load(self.embed_path)
                logger.info(f"Driver embedding loaded from {self.embed_path}")
            except Exception as e:
                logger.error(f"Failed to load driver embedding from {self.embed_path}: {e}")
                self.driver_embed = None
        else:
            logger.warning("No driver embedding found — enroll first")

    # ───────────────────────────────────────────────
    def _audio_to_embedding(self, audio: np.ndarray):
        """
        Convert numpy audio → temp wav → TitaNet embedding
        """
        audio = np.asarray(audio, dtype=np.float32).flatten()

        # normalize to safe range
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / (np.max(np.abs(audio)) + 1e-9)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            
        try:
            sf.write(temp_path, audio, SR)
            emb = self.model.get_embedding(temp_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Failed to remove temp file {temp_path}: {e}")

        # handle torch tensor / numpy safely
        if hasattr(emb, "detach"):
            emb = emb.detach().cpu().numpy()

        return emb.flatten()

    # ───────────────────────────────────────────────
    def enrol(self, audio: np.ndarray):
        """
        Enroll driver voice
        """
        try:
            embed = self._audio_to_embedding(audio)
            np.save(self.embed_path, embed)
            self.driver_embed = embed
            logger.info(f"Driver enrolled → {self.embed_path}")
        except Exception as e:
            logger.exception(f"Failed to enroll driver voice: {e}")
            raise

    # ───────────────────────────────────────────────
    def identify(self, audio: np.ndarray):
        """
        Identify speaker
        """
        if self.driver_embed is None:
            return ("UNKNOWN", 0.0)

        try:
            embed = self._audio_to_embedding(audio)

            # cosine similarity
            score = float(
                np.dot(self.driver_embed, embed) /
                (np.linalg.norm(self.driver_embed) *
                 np.linalg.norm(embed) + 1e-9)
            )

            # decision logic
            if score >= HIGH_THRESHOLD:
                label = "DRIVER"
            elif score >= LOW_THRESHOLD:
                label = "UNCERTAIN"
            else:
                label = "NOT_DRIVER"

            logger.debug(f"score={score:.4f} → {label}")

            return (label, round(score, 3))
        except Exception as e:
            logger.error(f"Error identifying speaker: {e}")
            return ("UNKNOWN", 0.0)

    # ───────────────────────────────────────────────
    def status(self):
        return {
            "enrolled": self.driver_embed is not None,
            "embed_path": self.embed_path,
            "high_threshold": HIGH_THRESHOLD,
            "low_threshold": LOW_THRESHOLD,
            "driver_name": os.path.splitext(os.path.basename(self.embed_path))[0]
                        if self.driver_embed is not None else None,
        }