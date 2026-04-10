"""
수원시정연구원 G룸 에이전트 - 메인 실행 파일

사용법:
  python main.py --input 회의록.m4a --type audio
  python main.py --input 전사본.txt --type text
"""
import argparse
import sys
from orchestrator import GRoomOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="수원시정연구원 G룸 에이전트",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input",
        required=True,
        help="입력 파일 경로\n  음성: .m4a / .mp3 / .wav\n  텍스트: .txt",
    )
    parser.add_argument(
        "--type",
        choices=["audio", "text"],
        default="audio",
        help="입력 타입 (기본값: audio)",
    )
    args = parser.parse_args()

    if not __import__("os").path.exists(args.input):
        print(f"[오류] 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)

    orchestrator = GRoomOrchestrator()
    try:
        results = orchestrator.run(
            input_path=args.input,
            input_type=args.type,
        )
    except KeyboardInterrupt:
        print("\n\n[중단] 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[오류] 파이프라인 실행 중 오류 발생:\n{e}")
        raise

    print(f"\n생성된 파일:")
    print(f"  CEO 브리핑  : {results['briefing_path']}")
    print(f"  파이프라인 상태: {results['state_path']}")
    print(f"\n초정밀 프롬프트 ({len(results['ultra_prompt']):,}자) 는 state JSON에 저장됨")


if __name__ == "__main__":
    main()
