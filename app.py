"""
수원시정연구원 G룸 에이전트 - Streamlit 웹 UI
"""
import sys
import os
import math
import tempfile
import io
import streamlit as st

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
# API 키 로드 (config에 내장 → Secrets 우선)
# ──────────────────────────────────────────────
ANTHROPIC_API_KEY = "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"
OPENAI_API_KEY    = "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"
try:
    ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
    OPENAI_API_KEY    = st.secrets.get("OPENAI_API_KEY", OPENAI_API_KEY)
except Exception:
    pass

os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
os.environ["OPENAI_API_KEY"]    = OPENAI_API_KEY

# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────
st.title("🏛️ 수원시정연구원 G룸 에이전트")
st.caption("회의 음성/텍스트 → 전사 → 회의록 → 맥락 분석 → 초정밀 프롬프트 → CEO 브리핑")
st.divider()

with st.sidebar:
    st.header("⚙️ 설정")
    st.success("API Key 로드됨 ✅")
    st.divider()
    st.markdown("**파이프라인 구조**")
    st.markdown("""
1. 🎙️ Transcriber
2. 📝 Minutes Writer
3. 🔍 Context Analyzer
4. ✨ Ultra Prompt Generator
5. 📋 CEO Briefing
""")

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
        if size_mb > 20:
            st.info(f"자동으로 {math.ceil(size_mb/20)}개로 나눠서 전사합니다.")

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

if not has_input:
    st.info("녹음하거나 파일을 업로드하거나 텍스트를 입력해주세요.")

if st.button("🚀 파이프라인 실행", disabled=not has_input, use_container_width=True, type="primary"):

    import anthropic
    import json
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from datetime import datetime

    results = {}

    # ── Step 1: 전사 (Claude API 사용) ───────────────
    with st.status("**[1/5] 음성 전사 중...**", expanded=True) as status:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        if audio_bytes:
            import base64
            # 오디오를 base64로 인코딩해 Claude에 전달
            audio_b64 = base64.standard_b64encode(audio_bytes).decode("utf-8")
            media_type = f"audio/{audio_ext}" if audio_ext != "mp3" else "audio/mpeg"
            msg = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=8096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": audio_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "이 음성 파일을 한국어로 정확하게 전사해주세요. 전사 텍스트만 출력하고 다른 설명은 하지 마세요."
                        }
                    ],
                }]
            )
            transcript = msg.content[0].text.strip()
            st.write(f"✓ 전사 완료 ({len(transcript):,}자)")
        else:
            transcript = text_input.strip()
            st.write(f"✓ 텍스트 입력 ({len(transcript):,}자)")
        results["transcript"] = transcript
        status.update(label="**[1/5] 전사 완료** ✅", state="complete")

    # ── Step 2: 맥락 분석 ─────────────────────────
    with st.status("**[2/5] 맥락 분석 중...**", expanded=True) as status:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""수원시정연구원 정책 연구 전문가로서 아래 텍스트를 분석해 JSON으로 반환하세요.

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

JSON만 반환하세요."""}]
        )
        raw = msg.content[0].text.strip()
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

    # ── Step 3: 회의록 작성 ──────────────────────────
    with st.status("**[3/5] 회의록 작성 중...**", expanded=True) as status:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=3000,
            messages=[{"role": "user", "content": f"""수원시정연구원 행정 전문가로서 아래 전사 텍스트로 공식 회의록을 JSON으로 작성하세요.

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

JSON만 반환하세요."""}]
        )
        raw2 = msg.content[0].text.strip()
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

        # 회의록 DOCX 메모리 생성
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
    with st.status("**[4/5] 울트라 초정밀 프롬프트 생성 중...**", expanded=True) as status:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4000,
            messages=[{"role": "user", "content": f"""AI 프롬프트 엔지니어링 전문가로서, 아래 맥락의 수원시정연구원 정책 보고서 작성을 위한 초정밀 프롬프트를 작성하세요.

주제: {context.get('main_topic','')}
이슈: {', '.join(context.get('key_issues',[]))}
키워드: {', '.join(context.get('keywords',[]))}
보고서 제목: {context.get('suggested_report_title','')}

포함 요소: 역할설정, 목차(5장 이상), 각 장별 작성지침, 인용방식, 수원시 특수성 반영법, 출력형식.
프롬프트만 출력하세요."""}]
        )
        ultra_prompt = msg.content[0].text.strip()
        results["ultra_prompt"] = ultra_prompt
        st.write(f"✓ 프롬프트 생성 완료 ({len(ultra_prompt):,}자)")
        status.update(label="**[4/5] 프롬프트 생성 완료** ✅", state="complete")

    # ── Step 5: CEO 브리핑 생성 ──────────────────────
    with st.status("**[5/5] CEO 브리핑 생성 중...**", expanded=True) as status:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""수원시정연구원 연구기획 전문가로서 원장님께 보고할 1페이지 브리핑을 JSON으로 작성하세요.

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

JSON만 반환하세요."""}]
        )
        raw3 = msg.content[0].text.strip()
        if raw3.startswith("```"):
            raw3 = raw3.split("```")[1]
            if raw3.startswith("json"): raw3 = raw3[4:]
        try:
            bd = json.loads(raw3.strip())
        except Exception:
            bd = {"briefing_title":"정책 연구 보고","overview":[],"current_status":[],
                  "analysis":[],"recommendations":[],"schedule":[]}

        # 브리핑 DOCX 메모리 생성
        doc2 = Document()
        sec2 = doc2.sections[0]
        sec2.top_margin = sec2.bottom_margin = Cm(2.5)
        sec2.left_margin = sec2.right_margin = Cm(3.0)

        add_para2 = lambda text, bold=False, size=11, align=WD_ALIGN_PARAGRAPH.LEFT: (
            lambda p, r: (setattr(r, 'bold', bold), setattr(r.font, 'size', Pt(size)),
                          setattr(r.font, 'name', '맑은 고딕'), setattr(p, 'alignment', align), p)
        )(*((doc2.add_paragraph(), None)))[0] if False else None

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
        results["briefing_title"] = bd.get("briefing_title","CEO브리핑")
        status.update(label="**[5/5] CEO 브리핑 완료** ✅", state="complete")

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
        st.download_button("📋 CEO 브리핑 DOCX", data=results["briefing_bytes"],
                           file_name="CEO브리핑.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
