"""
Agent 1: Transcriber
음성 파일 → 한국어 텍스트 전사

전략:
- Cloud 환경: OpenAI Whisper API 사용 (빠르고 1시간 이상 지원)
  - 25MB 초과 파일은 자동으로 청크 분할 후 순차 처리
- 로컬 환경 (fallback): faster-whisper 사용
"""
import os
import math
import tempfile


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CHUNK_SIZE_MB  = 20   # 청크당 최대 크기 (MB) — Whisper API 한도 25MB 이하


class TranscriberAgent:

    def run(self, audio_path: str) -> dict:
        """
        Args:
            audio_path: 음성 파일 경로 (wav/mp3/m4a/webm 등)
        Returns:
            { transcript, duration, language, segments }
        """
        openai_key = os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY)
        if openai_key:
            return self._run_openai(audio_path, openai_key)
        else:
            return self._run_local(audio_path)

    # ──────────────────────────────────────────
    # OpenAI Whisper API (권장)
    # ──────────────────────────────────────────
    def _run_openai(self, audio_path: str, api_key: str) -> dict:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= CHUNK_SIZE_MB:
            # 작은 파일: 바로 처리
            transcript, duration = self._whisper_api_call(client, audio_path)
        else:
            # 큰 파일: 청크 분할 처리
            transcript, duration = self._chunked_transcribe(client, audio_path)

        return {
            "transcript": transcript,
            "duration":   duration,
            "language":   "ko",
            "segments":   [transcript],
        }

    def _whisper_api_call(self, client, audio_path: str) -> tuple[str, float]:
        """단일 파일 Whisper API 호출"""
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ko",
                response_format="verbose_json",
            )
        duration = getattr(result, "duration", 0) or 0
        return result.text.strip(), float(duration)

    def _chunked_transcribe(self, client, audio_path: str) -> tuple[str, float]:
        """25MB 초과 파일을 청크로 나눠 순차 전사 후 합치기"""
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError("pydub가 필요합니다: pip install pydub")

        audio      = AudioSegment.from_file(audio_path)
        total_ms   = len(audio)
        total_sec  = total_ms / 1000

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        n_chunks     = math.ceil(file_size_mb / CHUNK_SIZE_MB)
        chunk_ms     = math.ceil(total_ms / n_chunks)

        transcripts = []
        for i in range(n_chunks):
            start = i * chunk_ms
            end   = min((i + 1) * chunk_ms, total_ms)
            chunk = audio[start:end]

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                chunk.export(tmp.name, format="mp3", bitrate="64k")
                tmp_path = tmp.name

            try:
                text, _ = self._whisper_api_call(client, tmp_path)
                transcripts.append(text)
                print(f"  청크 {i+1}/{n_chunks} 완료")
            finally:
                os.unlink(tmp_path)

        return " ".join(transcripts), total_sec

    # ──────────────────────────────────────────
    # faster-whisper 로컬 (fallback)
    # ──────────────────────────────────────────
    def _run_local(self, audio_path: str) -> dict:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("OpenAI API 키 또는 faster-whisper 패키지가 필요합니다.")

        model_size = "base"
        print(f"  [로컬] Whisper {model_size} 모델 로딩...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        segments, info = model.transcribe(
            audio_path,
            language="ko",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        texts = [seg.text.strip() for seg in segments]
        return {
            "transcript": " ".join(texts),
            "duration":   info.duration,
            "language":   info.language,
            "segments":   texts,
        }
