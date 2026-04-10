"""
Agent 1: Transcriber
음성 파일(m4a/mp3/wav) → 한국어 텍스트 전사
faster-whisper 사용
"""
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

# Streamlit Cloud 등 메모리 제한 환경에서는 자동으로 base 모델 사용
import os
_IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_CLOUD")
_MODEL_SIZE = "base" if _IS_CLOUD else WHISPER_MODEL_SIZE


class TranscriberAgent:
    """faster-whisper 기반 음성 전사 에이전트"""

    def __init__(self):
        self._model = None  # 지연 로드 (첫 호출 시 로드)

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                print(f"  Whisper 모델 로딩 중 ({_MODEL_SIZE})...")
                self._model = WhisperModel(
                    _MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                )
                print("  Whisper 모델 로드 완료")
            except ImportError:
                raise ImportError(
                    "faster-whisper가 설치되지 않았습니다.\n"
                    "pip install faster-whisper"
                )

    def run(self, audio_path: str) -> dict:
        """
        음성 파일 전사

        Args:
            audio_path: m4a / mp3 / wav 파일 경로

        Returns:
            {
              "transcript": str,     # 전체 전사 텍스트
              "duration": float,     # 오디오 길이 (초)
              "language": str,       # 감지 언어 코드
              "segments": list[str]  # 구간별 텍스트 리스트
            }
        """
        self._load_model()

        segments, info = self._model.transcribe(
            audio_path,
            language="ko",
            beam_size=5,
            vad_filter=True,          # 무음 구간 자동 제거
            vad_parameters=dict(
                min_silence_duration_ms=500
            ),
        )

        segment_texts = []
        for seg in segments:
            segment_texts.append(seg.text.strip())

        transcript = " ".join(segment_texts)

        return {
            "transcript": transcript,
            "duration": info.duration,
            "language": info.language,
            "segments": segment_texts,
        }
