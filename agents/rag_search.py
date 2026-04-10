"""
Agent 4: RAG Search Agent
수원시정연구원 knowledge_base 선행연구 검색
Phase 1: 키워드 기반 검색 (즉시 사용 가능)
Phase 2: 임베딩 기반 의미 검색 (선택적 확장)
"""
import json
import os
from pathlib import Path
from config import KNOWLEDGE_BASE_DIR, RAG_TOP_K


class RAGSearchAgent:
    """
    knowledge_base/index.json 을 읽어 키워드 매칭 점수로 관련 보고서 반환.
    Phase 2: USE_EMBEDDINGS=True 시 sentence-transformers 코사인 유사도 추가.
    """

    USE_EMBEDDINGS = False   # True 로 바꾸면 Phase 2 활성화

    def __init__(self, knowledge_base_path: str = None):
        self.kb_path = Path(knowledge_base_path or KNOWLEDGE_BASE_DIR)
        self.index_path = self.kb_path / "index.json"
        self.index = self._load_index()
        self._embed_model = None

    # ──────────────────────────────────────────
    # 인덱스 로드
    # ──────────────────────────────────────────
    def _load_index(self) -> dict:
        if not self.index_path.exists():
            # 인덱스 파일이 없으면 빈 구조 반환
            return {"reports": []}
        with open(self.index_path, encoding="utf-8") as f:
            return json.load(f)

    # ──────────────────────────────────────────
    # Phase 1: 키워드 매칭
    # ──────────────────────────────────────────
    def _keyword_score(self, report: dict, keywords: list, main_topic: str) -> int:
        target_text = (
            " ".join(report.get("keywords", []))
            + " " + report.get("title", "")
            + " " + report.get("summary", "")
        ).lower()

        score = 0
        for kw in keywords:
            if kw.lower() in target_text:
                score += 2   # 키워드 직접 포함 +2
        for word in main_topic.split():
            if word in target_text:
                score += 1   # 주제 단어 포함 +1
        return score

    # ──────────────────────────────────────────
    # Phase 2: 임베딩 유사도 (선택)
    # ──────────────────────────────────────────
    def _embedding_score(self, report: dict, query: str) -> float:
        if self._embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import numpy as np
                self._embed_model = SentenceTransformer(
                    "snunlp/KR-ELECTRA-discriminator"   # 한국어 임베딩 모델
                )
                self._np = np
            except ImportError:
                return 0.0

        report_text = report.get("title", "") + " " + report.get("summary", "")
        vq = self._embed_model.encode(query)
        vr = self._embed_model.encode(report_text)
        cos = self._np.dot(vq, vr) / (
            self._np.linalg.norm(vq) * self._np.linalg.norm(vr) + 1e-9
        )
        return float(cos)

    # ──────────────────────────────────────────
    # 메인 실행
    # ──────────────────────────────────────────
    def run(self, keywords: list, main_topic: str) -> list:
        """
        Args:
            keywords: 검색 키워드 목록
            main_topic: 핵심 주제 문자열

        Returns:
            관련 보고서 목록 (relevance_score 포함, 상위 RAG_TOP_K 개)
            각 항목: { id, title, year, author, keywords, summary, file_path, relevance_score }
        """
        reports = self.index.get("reports", [])

        if not reports:
            return []

        scored = []
        query = main_topic + " " + " ".join(keywords)

        for report in reports:
            kw_score = self._keyword_score(report, keywords, main_topic)
            em_score = 0.0
            if self.USE_EMBEDDINGS:
                em_score = self._embedding_score(report, query) * 5   # 스케일 조정

            total = kw_score + em_score
            if total > 0:
                scored.append({**report, "relevance_score": round(total, 3)})

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:RAG_TOP_K]

    # ──────────────────────────────────────────
    # 보고서 전문 읽기 (선택)
    # ──────────────────────────────────────────
    def read_report_text(self, report: dict) -> str:
        """해당 보고서의 본문 텍스트 반환 (존재하는 경우)"""
        file_path = self.kb_path / report.get("file_path", "")
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return ""
