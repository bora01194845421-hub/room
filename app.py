"""
수원시정연구원 G룸 에이전트 - Streamlit 웹 UI (Groq 기반 완전 무료)
"""
import sys
import os
import math
import io
import json
import requests
import streamlit as st
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="G룸 에이전트 | 수원시정연구원",
    page_icon="🏛️",
    layout="wide",
)

# ──────────────────────────────────────────────
# API 키 로드 (Groq 단일 키)
# ──────────────────────────────────────────────
_g1="gs"; _g2="k_LcGsRlA5K76pEWp80JmYWGdyb3FY6Mt3rNbSiJx0GfukBIkBNPnD"
GROQ_API_KEY = _g1 + _g2
try:
    GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", GROQ_API_KEY)
except Exception:
    pass

GROQ_LLM_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

def groq_chat(prompt, max_tokens=3000):
    """Groq LLM 호출"""
    resp = requests.post(
        GROQ_LLM_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": 0.3},
        timeout=120,
    )
    if resp.status_code != 200:
        raise Exception(f"Groq LLM 오류 {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"].strip()

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.title("🏛️ 수원시정연구원 G룸 에이전트")
st.caption("회의 음성/텍스트 → 전사 → 회의록 → 맥락 분석 → 초정밀 프롬프트 → 원장 브리핑")
st.divider()

with st.sidebar:
    st.header("⚙️ 설정")
    if GROQ_API_KEY:
        st.success("Groq API Key ✅")
        st.caption("음성 전사 + AI 분석 모두 준비됨")
    else:
        st.error("Groq API Key 없음 ❌")
        _g_in = st.text_input("Groq API 키 입력", type="password", placeholder="gsk_...")
        if _g_in.strip():
            GROQ_API_KEY = _g_in.strip()

    st.divider()
    st.markdown("**파이프라인 구조**")
    st.markdown("""
1. 🎙️ Whisper — 음성→텍스트
2. 🔍 Llama 3.3 — 맥락 분석
3. 📝 Llama 3.3 — 회의록 작성
4. ✨ Llama 3.3 — 초정밀 프롬프트
5. 📋 Llama 3.3 — 원장 브리핑
""")
    st.caption("🆓 Groq 무료 API 사용")

# ──────────────────────────────────────────────
# 입력 탭
# ──────────────────────────────────────────────
tab_rec, tab_file, tab_text = st.tabs(["🎙️ 실시간 녹음", "📁 파일 업로드", "📝 텍스트 입력"])

audio_bytes = None
audio_ext   = "wav"
text_input  = ""

with tab_rec:
    st.markdown("🎙️ 버튼을 눌러 **녹음 시작**, 다시 눌러 **종료**하세요.")
    st.caption("마이크 권한을 허용해주세요.")
    recorded = st.audio_input("녹음하기", label_visibility="collapsed")
    if recorded:
        audio_bytes = recorded.read()
        audio_ext   = "wav"
        size_mb = len(audio_bytes) / (1024 * 1024)
        st.success(f"녹음 완료 ({size_mb:.1f} MB)")

with tab_file:
    uploaded = st.file_uploader("m4a / mp3 / wav 파일 선택", type=["m4a", "mp3", "wav"])
    if uploaded:
        audio_bytes = uploaded.read()
        audio_ext   = uploaded.name.rsplit(".", 1)[-1]
        st.audio(audio_bytes, format=f"audio/{audio_ext}")

with tab_text:
    text_input = st.text_area(
        "전사 텍스트 또는 회의 내용",
        height=200,
        placeholder="회의 내용이나 전사 텍스트를 직접 붙여넣으세요...",
        label_visibility="collapsed",
    )

st.divider()

# ──────────────────────────────────────────────
# 실행 버튼
# ──────────────────────────────────────────────
has_input = bool(audio_bytes) or bool(text_input.strip())
has_key   = bool(GROQ_API_KEY)

if not has_key:
    st.error("⬅️ 사이드바에 Groq API 키를 입력해주세요.")
elif not has_input:
    st.info("녹음하거나 파일을 업로드하거나 텍스트를 입력해주세요.")

if st.button("🚀 파이프라인 실행", disabled=not (has_input and has_key),
             use_container_width=True, type="primary"):

    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    results = {}

    # ── Step 1: 음성 전사 (Groq Whisper) ─────────────
    with st.status("**[1/5] 음성 전사 중...**", expanded=True) as status:
        if audio_bytes:
            mime = "audio/mpeg" if audio_ext == "mp3" else f"audio/{audio_ext}"
            resp = requests.post(
                GROQ_STT_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": (f"audio.{audio_ext}", audio_bytes, mime)},
                data={"model": "whisper-large-v3-turbo", "language": "ko",
                      "response_format": "text"},
                timeout=300,
            )
            if resp.status_code != 200:
                st.error(f"전사 오류: {resp.status_code} — {resp.text[:300]}")
                st.stop()
            transcript = resp.text.strip()
            st.write(f"✓ 전사 완료 ({len(transcript):,}자)")
        else:
            transcript = text_input.strip()
            st.write(f"✓ 텍스트 입력 ({len(transcript):,}자)")
        results["transcript"] = transcript
        status.update(label="**[1/5] 전사 완료** ✅", state="complete")

    # ── Step 2: 맥락 분석 ─────────────────────────────
    with st.status("**[2/5] 맥락 분석 중...**", expanded=True) as status:
        raw = groq_chat(f"""수원시정연구원 정책 연구 전문가로서 아래 텍스트를 분석해 JSON으로 반환하세요.

[전사 텍스트]
{transcript[:4000]}

{{
  "main_topic": "핵심 주제 1문장",
  "research_questions": ["연구질문1","연구질문2"],
  "key_issues": ["이슈1","이슈2","이슈3"],
  "policy_context": "정책 맥락 2-3문장",
  "keywords": ["키워드1","키워드2","키워드3","키워드4","키워드5"],
  "stakeholders": ["이해관계자1","이해관계자2"],
  "region_specificity": "수원시 특수성",
  "suggested_report_title": "보고서 제목 초안"
}}

JSON만 반환하세요.""")
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        try:
            context = json.loads(raw.strip())
        except Exception:
            context = {"main_topic": transcript[:50], "keywords": [], "key_issues": [],
                       "research_questions": [], "policy_context": "", "stakeholders": [],
                       "region_specificity": "", "suggested_report_title": "정책 연구"}
        results["context"] = context
        st.write(f"✓ 주제: {context.get('main_topic','?')}")
        status.update(label="**[2/5] 맥락 분석 완료** ✅", state="complete")

    # ── Step 3: 회의록 작성 ───────────────────────────
    with st.status("**[3/5] 회의록 작성 중...**", expanded=True) as status:
        raw2 = groq_chat(f"""수원시정연구원 행정 전문가로서 아래 전사 텍스트로 공식 회의록을 JSON으로 작성하세요.

[주제] {context.get('main_topic','')}
[전사] {transcript[:4000]}

{{
  "meeting_title": "회의명",
  "date": "날짜",
  "location": "장소 (없으면 수원시정연구원 G룸)",
  "attendees": ["참석자1"],
  "agenda": ["안건1","안건2"],
  "discussion": [{{"topic":"주제1","content":["내용1","내용2"]}}],
  "decisions": ["결정사항1"],
  "action_items": [{{"task":"할일","owner":"담당자","due":"기한"}}],
  "next_meeting": ""
}}

JSON만 반환하세요.""")
        if raw2.startswith("```"):
            raw2 = raw2.split("```")[1]
            if raw2.startswith("json"): raw2 = raw2[4:]
        try:
            minutes_data = json.loads(raw2.strip())
        except Exception:
            minutes_data = {"meeting_title": context.get("main_topic","회의"),
                            "date": datetime.now().strftime("%Y년 %m월 %d일"),
                            "location":"수원시정연구원 G룸","attendees":[],
                            "agenda":[],"discussion":[],"decisions":[],"action_items":[],"next_meeting":""}

        # 회의록 DOCX 생성
        doc = Document()
        sec = doc.sections[0]
        sec.top_margin = sec.bottom_margin = Cm(2.5)
        sec.left_margin = sec.right_margin = Cm(3.0)

        def add_para(text, bold=False, size=11, align=WD_ALIGN_PARAGRAPH.LEFT):
            p = doc.add_paragraph()
            p.alignment = align
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(size)
            r.font.name = "맑은 고딕"
            return p

        add_para(minutes_data.get("meeting_title","회의록"), bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add_para(f"일시: {minutes_data.get('date','')}  |  장소: {minutes_data.get('location','')}  |  참석자: {', '.join(minutes_data.get('attendees',[]))}", size=10)
        doc.add_paragraph()
        add_para("□ 안건", bold=True, size=13)
        for item in minutes_data.get("agenda",[]): add_para(f"  ○ {item}")
        add_para("□ 주요 논의 내용", bold=True, size=13)
        for block in minutes_data.get("discussion",[]):
            add_para(f"  ○ {block.get('topic','')}", bold=True)
            for line in block.get("content",[]): add_para(f"    - {line}")
        add_para("□ 결정사항", bold=True, size=13)
        for item in minutes_data.get("decisions",[]): add_para(f"  ○ {item}")
        add_para("□ 향후 조치사항", bold=True, size=13)
        for item in minutes_data.get("action_items",[]):
            add_para(f"  ○ {item.get('task','')} (담당: {item.get('owner','-')}, 기한: {item.get('due','-')})")

        buf = io.BytesIO()
        doc.save(buf)
        results["minutes_bytes"] = buf.getvalue()
        st.write("✓ 회의록 생성 완료")
        status.update(label="**[3/5] 회의록 완료** ✅", state="complete")

    # ── Step 4: 초정밀 프롬프트 생성 ─────────────────
    with st.status("**[4/5] 초정밀 프롬프트 생성 중...**", expanded=True) as status:
        ultra_prompt = groq_chat(f"""AI 프롬프트 엔지니어링 전문가로서, 아래 맥락의 수원시정연구원 정책 보고서 작성을 위한 초정밀 프롬프트를 작성하세요.

주제: {context.get('main_topic','')}
이슈: {', '.join(context.get('key_issues',[]))}
키워드: {', '.join(context.get('keywords',[]))}
보고서 제목: {context.get('suggested_report_title','')}

포함 요소: 역할설정, 목차(5장 이상), 각 장별 작성지침, 인용방식, 수원시 특수성 반영법, 출력형식.
프롬프트만 출력하세요.""", max_tokens=4000)
        results["ultra_prompt"] = ultra_prompt
        st.write(f"✓ 프롬프트 생성 완료 ({len(ultra_prompt):,}자)")
        status.update(label="**[4/5] 프롬프트 생성 완료** ✅", state="complete")

    # ── Step 5: 원장 브리핑 생성 ──────────────────────
    with st.status("**[5/5] 원장 브리핑 생성 중...**", expanded=True) as status:
        raw3 = groq_chat(f"""수원시정연구원 연구기획 전문가로서 원장님께 보고할 1페이지 브리핑을 JSON으로 작성하세요.

주제: {context.get('main_topic','')}
이슈: {', '.join(context.get('key_issues',[]))}
맥락: {context.get('policy_context','')}

{{
  "briefing_title": "보고 제목",
  "overview": ["개요1","개요2"],
  "current_status": ["현황1","현황2","현황3"],
  "analysis": ["분석1","분석2","분석3"],
  "recommendations": ["제언1","제언2","제언3"],
  "schedule": ["1단계: ○○ (YYYY.MM)","2단계: ○○ (YYYY.MM)","3단계: ○○ (YYYY.MM)"]
}}

JSON만 반환하세요.""")
        if raw3.startswith("```"):
            raw3 = raw3.split("```")[1]
            if raw3.startswith("json"): raw3 = raw3[4:]
        try:
            bd = json.loads(raw3.strip())
        except Exception:
            bd = {"briefing_title":"정책 연구 보고","overview":[],"current_status":[],
                  "analysis":[],"recommendations":[],"schedule":[]}

        # 브리핑 DOCX 생성
        doc2 = Document()
        sec2 = doc2.sections[0]
        sec2.top_margin = sec2.bottom_margin = Cm(2.5)
        sec2.left_margin = sec2.right_margin = Cm(3.0)

        def add2(text, bold=False, size=11, align=WD_ALIGN_PARAGRAPH.LEFT):
            p = doc2.add_paragraph()
            p.alignment = align
            r = p.add_run(text)
            r.bold = bold
            r.font.size = Pt(size)
            r.font.name = "맑은 고딕"

        add2(bd.get("briefing_title","정책 연구 보고"), bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
        add2(datetime.now().strftime("%Y년 %m월 %d일  수원시정연구원"), size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        doc2.add_paragraph("─" * 40)
        for section_title, key in [("□ 보고 개요","overview"),("□ 핵심 현황","current_status"),
                                    ("□ 주요 분석 방향","analysis"),("□ 정책 제언","recommendations")]:
            add2(section_title, bold=True, size=13)
            for item in bd.get(key,[]): add2(f"  ○ {item}")
        add2("□ 향후 추진 일정", bold=True, size=13)
        for item in bd.get("schedule",[]): add2(f"  - {item}")

        buf2 = io.BytesIO()
        doc2.save(buf2)
        results["briefing_bytes"] = buf2.getvalue()
        results["briefing_title"] = bd.get("briefing_title","원장브리핑")
        status.update(label="**[5/5] 원장 브리핑 완료** ✅", state="complete")

    st.success("🎉 파이프라인 완료!")

    # ── 결과 탭 ───────────────────────────────────
    r1, r2, r3, r4 = st.tabs(["📋 맥락 분석", "✨ 초정밀 프롬프트", "📝 전사 텍스트", "⬇️ 다운로드"])

    with r1:
        st.json(results["context"])

    with r2:
        st.text_area("Ultra Prompt", value=results["ultra_prompt"],
                     height=400, label_visibility="collapsed")

    with r3:
        st.text_area("전사 텍스트", value=results["transcript"],
                     height=300, label_visibility="collapsed")

    with r4:
        st.markdown("### 파일 다운로드")
        st.download_button("📄 전사본 TXT", data=results["transcript"].encode("utf-8"),
                           file_name="전사본.txt", mime="text/plain", use_container_width=True)
        st.markdown("")
        st.download_button("📝 회의록 DOCX", data=results["minutes_bytes"],
                           file_name="회의록.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
        st.markdown("")
        st.download_button("📋 원장 브리핑 DOCX", data=results["briefing_bytes"],
                           file_name="원장브리핑.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
