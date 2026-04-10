"""
수원시정연구원 G룸 에이전트 - 설정 파일
"""
import os

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get(
    "ANTHROPIC_API_KEY",
    "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"
)

# OpenAI API (Whisper 전사용)
OPENAI_API_KEY = os.environ.get(
    "OPENAI_API_KEY",
    "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"
)

# 사용 모델
DEFAULT_MODEL = "claude-opus-4-5"
FAST_MODEL = "claude-haiku-4-5-20251001"

# Whisper 모델 설정
WHISPER_MODEL_SIZE = "large-v3"   # tiny / base / small / medium / large-v3
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# 보고서 RAG 검색 상위 결과 수
RAG_TOP_K = 5
