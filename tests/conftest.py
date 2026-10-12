"""pytest 공통 설정 — 실행 환경 전제를 한 줄로 알린다.

Python UTF-8 모드(PYTHONUTF8=1)가 꺼져 있으면 한국어 Windows(코드 페이지 949)에서 linkml·yaml 이 스키마 YAML 을 cp949 로 읽어
test_lint_clean·test_generated_files_up_to_date·test_help_subprocess 가 UnicodeDecodeError 로 실패한다 (사내 selftest 2026-10-03).
개발 PC 는 사용자 환경변수 PYTHONUTF8=1 이 있어 드러나지 않았다. 사내는 scripts\\env.bat 가 켠다 — 그 밖의 방법으로 돌리면 여기서 바로 멈춘다.

합성 레지스트리(data/synthetic/registry)에 강제 종료된 적재가 남긴 잠금 파일(.load.lock, docs/09 7장)이 있으면 바로 멈춘다 — 시험은 레지스트리를
잠금 없이 복사하지만(registry.copy_registry), 그 잠금은 `load.bat synthetic` 도 막으므로 사람이 지워야 한다 (2026-10-12 검토 수리:
전에는 잠금까지 복사돼 시험 수십 건이 엉뚱한 임시 폴더의 잠금을 가리키며 실패했다)."""
import sys
from pathlib import Path

import pytest

SYNTH_LOCK = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "registry" / ".load.lock"


def pytest_configure(config):
    if not sys.flags.utf8_mode:
        # cp949 콘솔에서도 깨지지 않게 '—'·'·' 같은 기호는 쓰지 않는다
        pytest.exit("Python UTF-8 모드가 꺼져 있다 - `set PYTHONUTF8=1` (scripts\\env.bat 를 거쳐 실행) 뒤 다시 돌린다. "
                    "꺼진 채로는 linkml/yaml 이 한국어 YAML 을 cp949 로 읽어 테스트 3건이 실패한다.", returncode=3)
    if SYNTH_LOCK.exists():
        # 경로는 저장소 기준 상대 경로로만 (selftest .txt 는 밖으로 가져갈 수 있다 — 절대 경로에 사용자 폴더 이름이 섞일 수 있다)
        pytest.exit("합성 레지스트리에 남은 잠금 파일이 있다 - data\\synthetic\\registry\\.load.lock (적재 창을 강제로 닫았거나 PC 가 꺼져 남은 것). "
                    "열린 적재 창이 없으면 그 파일을 지우고 다시 돌린다.", returncode=3)
