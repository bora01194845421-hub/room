"""
수원시정연구원 G룸 에이전트 - Streamlit 웹 UI
"""
import sys
import os
import tempfile
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

st.title("🏛️ 수원시정연구원 G룸 에이전트")
st.caption("회의 음성/텍스트 → 전사 → 회의록 → 맥락 분석 → 초정밀 프롬프트 → CEO 브리핑")
st.divider()

# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="sk-ant-... 형식의 API 키를 입력하세요",
    )
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

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
    st.markdown("버튼을 눌러 녹음을 시작하고, 다시 눌러 종료하세요.")
    try:
        from audio_recorder_streamlit import audio_recorder
        recorded = audio_recorder(
            text="",
            recording_color="#e8293b",
            neutral_color="#1f497d",
            icon_name="microphone",
            icon_size="3x",
            pause_threshold=3.0,
            sample_rate=16000,
        )
        if recorded:
            audio_bytes = recorded
            audio_ext   = "wav"
            st.audio(recorded, format="audio/wav")
            st.success(f"녹음 완료 ({len(recorded):,} bytes)")
    except ImportError:
        st.error("`audio-recorder-streamlit` 패키지가 필요합니다.")

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
has_input    = bool(audio_bytes) or bool(text_input.strip())
run_disabled = not api_key or not has_input

if not api_key:
    st.warning("사이드바에서 Anthropic API Key를 입력해주세요.")
elif not has_input:
    st.info("녹음하거나 파일을 업로드하거나 텍스트를 입력해주세요.")

if st.button("🚀 파이프라인 실행", disabled=run_disabled, use_container_width=True, type="primary"):

    try:
        from agents.context_analyzer import ContextAnalyzerAgent
        from agents.prompt_generator import UltraPromptGeneratorAgent
        from agents.ceo_briefing import CEOBriefingAgent
        from agents.minutes_writer import MinutesWriterAgent
    except ImportError as e:
        st.error(f"에이전트 임포트 오류: {e}")
        st.stop()

    results = {}

    # ── Step 1: 전사 ──────────────────────────────
    with st.status("**[1/5] 음성 전사 중...**", expanded=True) as status:
        if audio_bytes:
            try:
                from agents.transcriber import TranscriberAgent
            except ImportError as e:
                st.error(f"Transcriber 임포트 오류: {e}")
                st.stop()
            with tempfile.NamedTemporaryFile(suffix=f".{audio_ext}", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                result = TranscriberAgent().run(tmp_path)
                transcript = result["transcript"]
                st.write(f"✓ 전사 완료 ({result['duration']:.0f}초, 언어: {result['language']})")
            finally:
                os.unlink(tmp_path)
        else:
            transcript = text_input.strip()
            st.write(f"✓ 텍스트 입력 사용 ({len(transcript):,}자)")
        results["transcript"] = transcript
        status.update(label="**[1/5] 전사 완료** ✅", state="complete")

    # ── Step 2: 맥락 분석 (회의록 작성 전에 주제 파악) ──
    with st.status("**[2/5] 맥락 분석 중...**", expanded=True) as status:
        context = ContextAnalyzerAgent().run(transcript)
        results["context"] = context
        st.write(f"✓ 주제: {context.get('main_topic', '?')}")
        st.write(f"✓ 키워드: {', '.join(context.get('keywords', [])[:6])}")
        status.update(label="**[2/5] 맥락 분석 완료** ✅", state="complete")

    # ── Step 3: 회의록 작성 ──────────────────────────
    with st.status("**[3/5] 회의록 작성 중...**", expanded=True) as status:
        minutes_path, minutes_bytes = MinutesWriterAgent().run(transcript, context)
        results["minutes_path"]  = minutes_path
        results["minutes_bytes"] = minutes_bytes
        st.write(f"✓ 회의록 생성 완료")
        status.update(label="**[3/5] 회의록 완료** ✅", state="complete")

    # ── Step 4: 초정밀 프롬프트 생성 ─────────────────
    with st.status("**[4/5] 울트라 초정밀 프롬프트 생성 중...**", expanded=True) as status:
        ultra_prompt = UltraPromptGeneratorAgent().run(context)
        results["ultra_prompt"] = ultra_prompt
        st.write(f"✓ 프롬프트 생성 완료 ({len(ultra_prompt):,}자)")
        status.update(label="**[4/5] 프롬프트 생성 완료** ✅", state="complete")

    # ── Step 5: CEO 브리핑 생성 ──────────────────────
    with st.status("**[5/5] CEO 브리핑 생성 중...**", expanded=True) as status:
        briefing_path = CEOBriefingAgent().run(ultra_prompt=ultra_prompt, context=context)
        results["briefing_path"] = briefing_path
        status.update(label="**[5/5] CEO 브리핑 완료** ✅", state="complete")

    st.success("🎉 파이프라인 완료!")

    # ──────────────────────────────────────────────
    # 결과 탭
    # ──────────────────────────────────────────────
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

        # 전사본 TXT
        st.download_button(
            label="📄 전사본 TXT 다운로드",
            data=results["transcript"].encode("utf-8"),
            file_name="전사본.txt",
            mime="text/plain",
            use_container_width=True,
        )

        st.markdown("")

        # 회의록 DOCX
        st.download_button(
            label="📝 회의록 DOCX 다운로드",
            data=results["minutes_bytes"],
            file_name=os.path.basename(results["minutes_path"]),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        st.markdown("")

        # CEO 브리핑 DOCX
        if os.path.exists(results["briefing_path"]):
            with open(results["briefing_path"], "rb") as f:
                st.download_button(
                    label="📋 CEO 브리핑 DOCX 다운로드",
                    data=f,
                    file_name=os.path.basename(results["briefing_path"]),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
