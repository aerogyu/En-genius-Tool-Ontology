"""pytest 공통 설정 — 실행 환경 전제를 한 줄로 알린다.

Python UTF-8 모드(PYTHONUTF8=1)가 꺼져 있으면 한국어 Windows(코드 페이지 949)에서 linkml·yaml 이 스키마 YAML 을 cp949 로 읽어
test_lint_clean·test_generated_files_up_to_date·test_help_subprocess 가 UnicodeDecodeError 로 실패한다 (사내 selftest 2026-10-03).
개발 PC 는 사용자 환경변수 PYTHONUTF8=1 이 있어 드러나지 않았다. 사내는 scripts\\env.bat 가 켠다 — 그 밖의 방법으로 돌리면 여기서 바로 멈춘다."""
import sys

import pytest


def pytest_configure(config):
    if not sys.flags.utf8_mode:
        # cp949 콘솔에서도 깨지지 않게 '—'·'·' 같은 기호는 쓰지 않는다
        pytest.exit("Python UTF-8 모드가 꺼져 있다 - `set PYTHONUTF8=1` (scripts\\env.bat 를 거쳐 실행) 뒤 다시 돌린다. "
                    "꺼진 채로는 linkml/yaml 이 한국어 YAML 을 cp949 로 읽어 테스트 3건이 실패한다.", returncode=3)
