"""
Agent 3: Ultra Prompt Generator  ⭐ 핵심 신규 에이전트
맥락 dict → 보고서 작성용 초정밀 프롬프트 자동 생성
유영철 박사 "치트키" 구현: Claude에게 최적 프롬프트를 요청하는 메타 프롬프트
"""
import anthropic
from config import DEFAULT_MODEL

META_PROMPT_TEMPLATE = """당신은 AI 프롬프트 엔지니어링 및 한국 정책연구 보고서 작성 전문가입니다.
수원시정연구원 연구진이 아래 맥락의 정책 보고서를 작성하려 합니다.

[연구 맥락]
- 주제: {main_topic}
- 연구 질문:
{research_questions_formatted}
- 핵심 이슈:
{key_issues_formatted}
- 정책적 맥락: {policy_context}
- 검색 키워드: {keywords_formatted}
- 관련 이해관계자: {stakeholders_formatted}
- 수원시 특수성: {region_specificity}
- 보고서 제목 초안: {suggested_report_title}

목표:
- 100~150페이지 분량의 심층 정책 연구 보고서 초안 작성
- 맥킨지 컨설팅 스타일의 논리적 목차 구성과 MECE 원칙 적용
- 수원시 맥락에 특화된 현황 분석, 타 지자체 사례 비교, 정책 제언 포함
- 한국 행정문서 개조식 형식 (□ ○ - ⦁) 준수

위 목표를 달성하기 위한 "울트라 초정밀 프롬프트"를 작성해주세요.
이 프롬프트는 별도의 Claude API 호출에서 보고서 초안 생성에 사용됩니다.

프롬프트는 반드시 다음 6가지 요소를 모두 포함해야 합니다:

1. 역할 설정 (페르소나)
   - 연구원의 배경, 전문성, 기관 소속 명시

2. 보고서 구조 명세 (목차 초안)
   - 최소 5개 장(章) 구성
   - 각 장 제목 및 주요 절(節) 포함

3. 각 장별 작성 지침
   - 포함해야 할 분석 내용, 데이터 유형, 논리 전개 방식

4. 인용 및 근거 제시 방식
   - 통계, 선행연구, 타 지자체 사례 활용 방법

5. 수원시 특수성 반영 방법
   - 수원시 맥락 데이터 삽입 지점 및 방법

6. 출력 형식 명세
   - 개조식 계층 구조 적용 규칙
   - 표/그래프 배치 제안

프롬프트만 출력하세요. 설명이나 서문은 포함하지 마세요.
"""


class UltraPromptGeneratorAgent:
    def __init__(self):
        self.client = anthropic.Anthropic()

    def run(self, context: dict) -> str:
        """
        맥락 기반 초정밀 프롬프트 생성

        Args:
            context: ContextAnalyzerAgent 출력 dict

        Returns:
            ultra_prompt: str (보고서 작성 에이전트에 전달할 프롬프트)
        """

        def fmt_list(items: list, indent: str = "  - ") -> str:
            if not items:
                return "  - (없음)"
            return "\n".join(f"{indent}{item}" for item in items)

        filled = META_PROMPT_TEMPLATE.format(
            main_topic=context.get("main_topic", ""),
            research_questions_formatted=fmt_list(context.get("research_questions", [])),
            key_issues_formatted=fmt_list(context.get("key_issues", [])),
            policy_context=context.get("policy_context", ""),
            keywords_formatted=", ".join(context.get("keywords", [])),
            stakeholders_formatted=", ".join(context.get("stakeholders", [])),
            region_specificity=context.get("region_specificity", ""),
            suggested_report_title=context.get("suggested_report_title", "정책 연구"),
        )

        message = self.client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": filled
            }]
        )

        return message.content[0].text.strip()
