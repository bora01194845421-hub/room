"""
수원시정연구원 G룸 에이전트 - 오케스트레이터
4개 에이전트 순차 실행: 전사 → 맥락분석 → 초정밀 프롬프트 → CEO 브리핑
"""
import json
import os
from datetime import datetime
from agents.transcriber import TranscriberAgent
from agents.context_analyzer import ContextAnalyzerAgent
from agents.prompt_generator import UltraPromptGeneratorAgent
from agents.ceo_briefing import CEOBriefingAgent
from config import OUTPUT_DIR


class GRoomOrchestrator:
    """
    수원시정연구원 G룸 에이전트 오케스트레이터
    """

    def __init__(self):
        self.transcriber      = TranscriberAgent()
        self.context_analyzer = ContextAnalyzerAgent()
        self.prompt_generator = UltraPromptGeneratorAgent()
        self.ceo_briefing     = CEOBriefingAgent()

        self.pipeline_state: dict = {}

    def _step(self, num: int, label: str):
        print(f"\n[{num}/4] {label}...")

    def _ok(self, msg: str):
        print(f"  ✓ {msg}")

    def _save_state(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(OUTPUT_DIR, f"pipeline_state_{ts}.json")
        safe = {
            k: v for k, v in self.pipeline_state.items()
            if isinstance(v, (str, int, float, list, dict, bool, type(None)))
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False, indent=2)
        return path

    def run(self, input_path: str, input_type: str = "audio") -> dict:
        """
        전체 파이프라인 실행

        Args:
            input_path: 음성 파일 또는 텍스트 파일 경로
            input_type: "audio" | "text"

        Returns:
            { transcript, context, ultra_prompt, briefing_path, state_path }
        """
        print("=" * 62)
        print("  수원시정연구원 G룸 에이전트 시작")
        print(f"  입력: {input_path}  [{input_type}]")
        print("=" * 62)

        # ── Step 1: 전사 ──────────────────────────────────────
        self._step(1, "음성 전사" if input_type == "audio" else "텍스트 입력")

        if input_type == "audio":
            result = self.transcriber.run(input_path)
            transcript = result["transcript"]
            self.pipeline_state.update({
                "transcript": transcript,
                "duration":   result["duration"],
                "language":   result["language"],
            })
            self._ok(f"전사 완료 ({result['duration']:.0f}초, 언어: {result['language']})")
        else:
            with open(input_path, encoding="utf-8") as f:
                transcript = f.read()
            self.pipeline_state["transcript"] = transcript
            self._ok(f"텍스트 로드 완료 ({len(transcript):,}자)")

        # ── Step 2: 맥락 분석 ───────────────────────────────
        self._step(2, "맥락 분석")
        context = self.context_analyzer.run(transcript)
        self.pipeline_state["context"] = context
        self._ok(f"주제: {context.get('main_topic', '?')}")
        self._ok(f"키워드: {', '.join(context.get('keywords', [])[:5])}")

        # ── Step 3: 초정밀 프롬프트 생성 ────────────────────
        self._step(3, "울트라 초정밀 프롬프트 생성")
        ultra_prompt = self.prompt_generator.run(context)
        self.pipeline_state["ultra_prompt"] = ultra_prompt
        self._ok(f"프롬프트 생성 완료 ({len(ultra_prompt):,}자)")

        # ── Step 4: CEO 브리핑 생성 ──────────────────────────
        self._step(4, "CEO 브리핑 생성")
        briefing_path = self.ceo_briefing.run(
            ultra_prompt=ultra_prompt,
            context=context,
        )
        self.pipeline_state["briefing_path"] = briefing_path
        self._ok(f"브리핑 저장: {briefing_path}")

        state_path = self._save_state()

        print("\n" + "=" * 62)
        print("  파이프라인 완료!")
        print("=" * 62)

        return {
            "transcript":   transcript,
            "context":      context,
            "ultra_prompt": ultra_prompt,
            "briefing_path": briefing_path,
            "state_path":   state_path,
        }
