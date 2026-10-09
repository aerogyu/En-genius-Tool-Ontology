"""Tool Ontology MCP 서버 실행 파일 — 사내 AI 플랫폼의 En-genius MCP 브리지(또는 다른 MCP 클라이언트)가 이것을 띄운다.

브리지 설정에 적을 것 (경로는 저장소 위치에 맞춘다):
    command : C:\\EnGenius\\engenius-tool-ontology\\.venv\\Scripts\\python.exe
    args    : ["-X", "utf8", "C:\\EnGenius\\engenius-tool-ontology\\scripts\\mcp_server.py"]
전송은 stdio. PYTHONPATH·env.bat 없이 돈다 (여기서 src\\ 를 찾는다). 추가 인자는 `python -m engenius_onto mcp --help` 와 같다
(예: --backend fuseki, --data synthetic). stdout 은 MCP 메시지 전용이라 이 파일은 아무것도 출력하지 않는다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engenius_onto.cli import main  # noqa: E402

sys.exit(main(["mcp", *sys.argv[1:]]))
