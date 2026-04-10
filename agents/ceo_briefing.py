"""
Agent 4: CEO Briefing Agent
Ultra Prompt + 맥락 → A4 1페이지 CEO 브리핑 DOCX 생성
(보고서 작성 에이전트 없이 프롬프트와 맥락만으로 직접 브리핑 생성)
"""
import anthropic
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEFAULT_MODEL, OUTPUT_DIR
from templates.briefing_template import (
    create_briefing_document,
    add_briefing_header,
    add_briefing_section,
    add_schedule_section,
    save_briefing,
)

CEO_BRIEFING_PROMPT = """당신은 수원시정연구원 연구기획 전문가입니다.
아래 연구 맥락과 보고서 설계 지침을 바탕으로, 원장님께 보고할 1페이지 브리핑을 작성해주세요.

[연구 주제]
{main_topic}

[핵심 이슈]
{key_issues}

[정책적 맥락]
{policy_context}

[정책 제언 방향 (보고서 설계 지침 발췌)]
{prompt_excerpt}

아래 JSON 형식으로만 반환하세요 (다른 설명 없이):

{{
  "briefing_title": "보고 제목 (예: 수원시 ○○ 연구 추진 계획 보고)",
  "overview": ["보고 개요 1문장", "연구 목적 1문장"],
  "current_status": ["핵심 현황 1", "핵심 현황 2", "핵심 현황 3"],
  "analysis": ["주요 분석 방향 1", "주요 분석 방향 2", "주요 분석 방향 3"],
  "recommendations": ["정책 제언 방향 1", "정책 제언 방향 2", "정책 제언 방향 3"],
  "schedule": ["1단계: ○○ (YYYY.MM)", "2단계: ○○ (YYYY.MM)", "3단계: ○○ (YYYY.MM)"]
}}

간결하고 임팩트 있게, 공무원 보고서 개조식 스타일로 작성하세요.
"""


class CEOBriefingAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def _generate_briefing_content(
        self, ultra_prompt: str, context: dict
    ) -> dict:
        key_issues_text = "\n".join(
            f"- {item}" for item in context.get("key_issues", [])
        ) or "- (없음)"

        # ultra_prompt 앞부분 발췌 (토큰 절약)
        prompt_excerpt = ultra_prompt[:2000] if len(ultra_prompt) > 2000 else ultra_prompt

        message = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": CEO_BRIEFING_PROMPT.format(
                    main_topic=context.get("main_topic", ""),
                    key_issues=key_issues_text,
                    policy_context=context.get("policy_context", ""),
                    prompt_excerpt=prompt_excerpt,
                )
            }]
        )

        raw = message.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "briefing_title": f"{context.get('suggested_report_title', '정책 연구')} 보고",
                "overview": ["연구 초안 브리핑입니다.", "세부 내용을 확인해주세요."],
                "current_status": ["현황 분석 필요"],
                "analysis": ["분석 방향 수립 중"],
                "recommendations": ["정책 제언 도출 예정"],
                "schedule": ["일정 협의 필요"],
            }

    def _build_docx(self, content: dict) -> str:
        doc = create_briefing_document()

        add_briefing_header(doc, content.get("briefing_title", "정책 연구 보고"))
        add_briefing_section(doc, "보고 개요",      content.get("overview", []))
        add_briefing_section(doc, "핵심 현황",      content.get("current_status", []))
        add_briefing_section(doc, "주요 분석 방향", content.get("analysis", []))
        add_briefing_section(doc, "정책 제언",      content.get("recommendations", []))
        add_schedule_section(doc,                   content.get("schedule", []))

        return save_briefing(doc, OUTPUT_DIR)

    def run(self, ultra_prompt: str, context: dict) -> str:
        """
        Args:
            ultra_prompt: UltraPromptGeneratorAgent 출력 프롬프트
            context: ContextAnalyzerAgent 출력 dict

        Returns:
            briefing_path: 생성된 DOCX 파일 경로
        """
        content = self._generate_briefing_content(ultra_prompt, context)
        return self._build_docx(content)
