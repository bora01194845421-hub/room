"""
Agent 2: Context Analyzer
전사 텍스트 → 연구 맥락·키워드·연구질문 구조화 (JSON)
"""
import json
import anthropic
from config import DEFAULT_MODEL

CONTEXT_ANALYSIS_PROMPT = """당신은 수원시정연구원의 수석 정책 연구 전문가입니다.
다음 회의/강연 전사 텍스트를 분석하여 아래 항목을 JSON 형식으로 추출하세요.

[전사 텍스트]
{transcript}

추출 항목:
1. main_topic: 핵심 주제 (1문장, 명사형으로 끝낼 것)
2. research_questions: 연구 질문 목록 (최대 5개, 각각 "?" 로 끝나는 의문문)
3. key_issues: 핵심 이슈/문제점 목록 (최대 5개)
4. policy_context: 정책적 맥락 설명 (2-3문장, 수원시 관점 포함)
5. keywords: 선행연구 검색용 키워드 (최대 10개, 단어 단위)
6. stakeholders: 관련 이해관계자 목록 (기관·집단명)
7. region_specificity: 수원시 특수성 관련 내용 (없으면 빈 문자열)
8. suggested_report_title: 보고서 제목 초안 (예: "수원시 ○○ 실태 및 개선방안 연구")

반드시 유효한 JSON 형식만 반환하고, 다른 설명은 포함하지 마세요.
"""


class ContextAnalyzerAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def run(self, transcript: str) -> dict:
        """
        전사 텍스트 분석

        Args:
            transcript: 전사 텍스트 (str)

        Returns:
            context dict (main_topic, research_questions, key_issues, ...)
        """
        message = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": CONTEXT_ANALYSIS_PROMPT.format(transcript=transcript)
            }]
        )

        raw = message.content[0].text.strip()

        # ```json ... ``` 블록 처리
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            context = json.loads(raw)
        except json.JSONDecodeError:
            # 파싱 실패 시 기본 구조 반환
            context = {
                "main_topic": "분석 실패 - 텍스트 재확인 필요",
                "research_questions": [],
                "key_issues": [],
                "policy_context": raw[:500],
                "keywords": [],
                "stakeholders": [],
                "region_specificity": "",
                "suggested_report_title": "수원시 정책연구",
            }

        return context
