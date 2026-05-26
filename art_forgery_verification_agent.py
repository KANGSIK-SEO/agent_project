from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool


APP_DIR = Path(__file__).resolve().parent
ENV_PATH = APP_DIR.parent / ".env"
load_dotenv(ENV_PATH)


PIGMENT_INTRODUCTION_YEARS = {
    "lead white": -400,
    "flake white": -400,
    "납백": -400,
    "azurite": -300,
    "석청": -300,
    "vermilion": 800,
    "버밀리온": 800,
    "smalt": 1500,
    "스몰트": 1500,
    "prussian blue": 1704,
    "프러시안 블루": 1704,
    "cobalt blue": 1802,
    "코발트 블루": 1802,
    "emerald green": 1814,
    "에메랄드 그린": 1814,
    "synthetic ultramarine": 1828,
    "합성 울트라마린": 1828,
    "cadmium yellow": 1840,
    "카드뮴 옐로": 1840,
    "zinc white": 1834,
    "징크 화이트": 1834,
    "viridian": 1859,
    "비리디언": 1859,
    "alizarin crimson": 1868,
    "알리자린 크림슨": 1868,
    "titanium white": 1916,
    "티타늄 화이트": 1916,
    "phthalocyanine blue": 1935,
    "프탈로시아닌 블루": 1935,
    "quinacridone": 1958,
    "퀴나크리돈": 1958,
}

SUSPICIOUS_CONDITION_PATTERNS = {
    "새 바니시": "오래된 작품 주장과 표면 바니시의 신선도가 충돌할 수 있습니다.",
    "균열이 이상": "크라클뤼르 패턴이 건조 시간, 지지체 움직임, 자연 노화와 맞지 않을 수 있습니다.",
    "인공 균열": "가열, 화학 처리, 물리적 압박으로 만든 위조 노화 가능성이 있습니다.",
    "캔버스는 오래": "오래된 지지체 위에 최근 물감을 올린 조합 위작 가능성을 점검해야 합니다.",
    "화학약품": "인위적 aging 처리 흔적일 수 있습니다.",
    "자외선 반응": "UV 형광 반응이 보수재, 바니시, 신구 도막 구분 단서가 됩니다.",
    "스펙트럼 불일치": "Raman/FTIR/XRF 스펙트럼이 기준 재료와 다를 수 있습니다.",
    "서명만 선명": "서명층과 본 도막의 노화가 다르면 사후 서명 가능성이 있습니다.",
}


@dataclass
class ToolResult:
    tool: str
    risk: int
    findings: list[str]
    evidence: dict[str, Any]
    next_steps: list[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def _years_from_text(text: str) -> list[int]:
    return [int(value) for value in re.findall(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})(?!\d)", text)]


def _claim_year(text: str) -> int | None:
    years = _years_from_text(text)
    return min(years) if years else None


def _mentioned_pigments(text: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    found = []
    for pigment, intro_year in PIGMENT_INTRODUCTION_YEARS.items():
        if pigment.lower() in lowered:
            found.append({"pigment": pigment, "introduced_year": intro_year})
    return found


@tool
def check_pigment_anachronism(artwork_description: str) -> str:
    """작품 설명에서 주장 연도와 안료명을 찾아 시대착오적 재료 사용 가능성을 검사합니다."""
    claim_year = _claim_year(artwork_description)
    pigments = _mentioned_pigments(artwork_description)
    findings: list[str] = []
    risk = 15

    if claim_year is None:
        findings.append("작품의 주장 제작 연도 또는 시대가 명확하지 않습니다.")
        risk += 10

    if not pigments:
        findings.append("설명에서 알려진 안료명이 감지되지 않았습니다.")
        risk += 5

    for item in pigments:
        intro_year = item["introduced_year"]
        pigment = item["pigment"]
        if claim_year is not None and intro_year > claim_year:
            findings.append(
                f"{claim_year}년 작품 주장과 {pigment} 상용화 시점({intro_year}년)이 충돌합니다."
            )
            risk += 35
        else:
            findings.append(f"{pigment}는 현재 입력만으로는 주장 연도와 직접 충돌하지 않습니다.")

    return ToolResult(
        tool="check_pigment_anachronism",
        risk=min(risk, 95),
        findings=findings,
        evidence={"claim_year": claim_year, "pigments": pigments},
        next_steps=[
            "Raman 또는 FTIR로 유기/무기 안료 피크를 확인하세요.",
            "XRF로 Ti, Cd, Co, Zn, Cr, Cu 등 핵심 원소를 확인하세요.",
            "도막 단면 분석으로 안료층과 보수층을 구분하세요.",
        ],
    ).to_json()


@tool
def check_condition_and_aging(artwork_description: str) -> str:
    """바니시, 균열, 지지체, 서명, 보수 흔적 등 자연 노화와 맞지 않는 단서를 검사합니다."""
    lowered = artwork_description.lower()
    findings = []
    risk = 20

    for pattern, message in SUSPICIOUS_CONDITION_PATTERNS.items():
        if pattern.lower() in lowered:
            findings.append(message)
            risk += 15

    if "오래" in lowered and ("새" in lowered or "선명" in lowered):
        findings.append("오래된 부분과 새로워 보이는 부분이 함께 언급되어 층위별 분석이 필요합니다.")
        risk += 10

    if not findings:
        findings.append("설명만으로는 강한 노화 불일치 신호가 감지되지 않았습니다.")

    return ToolResult(
        tool="check_condition_and_aging",
        risk=min(risk, 90),
        findings=findings,
        evidence={"matched_patterns": [p for p in SUSPICIOUS_CONDITION_PATTERNS if p.lower() in lowered]},
        next_steps=[
            "측광/사광 사진으로 균열 방향과 도막 수축 패턴을 비교하세요.",
            "UV 형광 사진으로 바니시와 보수재 영역을 분리하세요.",
            "현미경으로 균열 안쪽의 오염 축적 여부를 확인하세요.",
        ],
    ).to_json()


@tool
def check_provenance_risk(provenance_text: str) -> str:
    """소장 이력, 전시 이력, 감정서, 경매 기록 텍스트에서 출처 위험 신호를 점검합니다."""
    lowered = provenance_text.lower()
    findings = []
    risk = 10

    weak_terms = {
        "private collection": "구체적 소장자 없는 private collection 표기는 출처 공백을 숨길 수 있습니다.",
        "개인 소장": "개인 소장만 있고 기간/소장자/거래 기록이 없으면 provenance 공백입니다.",
        "attributed to": "attributed to는 작가 확정이 아니라 귀속 추정 표현입니다.",
        "추정": "추정 표현은 확정 감정이 아닙니다.",
        "style of": "style of는 작가 본인 작품이라는 뜻이 아닙니다.",
        "after": "after 표기는 원작 이후 제작 또는 모작 가능성을 포함합니다.",
        "감정서 없음": "감정서 부재는 단독으로 위작 증거는 아니지만 거래 위험을 높입니다.",
        "출처 불명": "출처 불명은 강한 시장 리스크입니다.",
    }

    for term, message in weak_terms.items():
        if term in lowered:
            findings.append(message)
            risk += 18

    years = sorted(set(_years_from_text(provenance_text)))
    if len(years) >= 2:
        gaps = [b - a for a, b in zip(years, years[1:]) if b - a >= 30]
        for gap in gaps:
            findings.append(f"기록상 {gap}년 이상 공백이 있어 중간 소유 이력 확인이 필요합니다.")
            risk += 12
    elif not years:
        findings.append("연도 기반 provenance가 거의 없어 이력 검증력이 낮습니다.")
        risk += 15

    if not findings:
        findings.append("입력된 출처 정보에서 즉각적인 고위험 표현은 적습니다.")

    return ToolResult(
        tool="check_provenance_risk",
        risk=min(risk, 95),
        findings=findings,
        evidence={"years": years},
        next_steps=[
            "작가 catalogue raisonne 등재 여부를 확인하세요.",
            "전시 도록, 경매 카탈로그, 갤러리 인보이스를 원본 이미지와 대조하세요.",
            "감정서 발행 기관과 서명자의 권위를 확인하세요.",
        ],
    ).to_json()


@tool
def inspect_image_metadata(image_path: str) -> str:
    """로컬 이미지 파일의 기본 메타데이터를 읽어 재촬영/편집 흔적 점검에 필요한 단서를 반환합니다."""
    path = Path(image_path).expanduser()
    findings: list[str] = []
    risk = 10

    if not path.exists():
        return ToolResult(
            tool="inspect_image_metadata",
            risk=30,
            findings=[f"이미지 파일을 찾지 못했습니다: {path}"],
            evidence={"image_path": str(path)},
            next_steps=["정확한 로컬 이미지 경로를 다시 입력하세요."],
        ).to_json()

    evidence: dict[str, Any] = {"image_path": str(path), "file_size_bytes": path.stat().st_size}

    try:
        from PIL import Image, ExifTags

        with Image.open(path) as image:
            evidence.update({"format": image.format, "mode": image.mode, "width": image.width, "height": image.height})
            raw_exif = image.getexif()
            exif = {}
            for key, value in raw_exif.items():
                label = ExifTags.TAGS.get(key, str(key))
                exif[label] = str(value)
            evidence["exif_keys"] = sorted(exif.keys())

            software = exif.get("Software", "")
            if software:
                findings.append(f"이미지 편집/생성 소프트웨어 메타데이터가 있습니다: {software}")
                risk += 15
            if not raw_exif:
                findings.append("EXIF가 없거나 제거되어 촬영 원본성 판단이 제한됩니다.")
                risk += 8
    except ImportError:
        findings.append("Pillow가 설치되어 있지 않아 이미지 내부 메타데이터를 읽지 못했습니다.")
        risk += 5
    except Exception as exc:
        findings.append(f"이미지 메타데이터 읽기 실패: {exc}")
        risk += 10

    if not findings:
        findings.append("이미지 메타데이터에서 즉각적인 고위험 신호는 감지되지 않았습니다.")

    return ToolResult(
        tool="inspect_image_metadata",
        risk=min(risk, 75),
        findings=findings,
        evidence=evidence,
        next_steps=[
            "원본 촬영 파일, 현미경 사진, UV/IR 사진을 별도로 확보하세요.",
            "작품 전체, 서명, 가장자리, 뒷면, 균열 확대 사진을 같은 조명 조건에서 촬영하세요.",
        ],
    ).to_json()


@tool
def call_custom_vision_classifier(image_path: str) -> str:
    """Azure Custom Vision Prediction 환경변수가 있으면 이미지 진품/위작 분류 API를 호출합니다."""
    path = Path(image_path).expanduser()
    endpoint = os.getenv("PREDICTION_ENDPOINT")
    key = os.getenv("PREDICTION_KEY")
    project_name = os.getenv("PROJECT_NAME")
    publish_name = os.getenv("PUBLISH_NAME")

    missing = [
        name
        for name, value in {
            "PREDICTION_ENDPOINT": endpoint,
            "PREDICTION_KEY": key,
            "PROJECT_NAME": project_name,
            "PUBLISH_NAME": publish_name,
        }.items()
        if not value
    ]
    if missing:
        return ToolResult(
            tool="call_custom_vision_classifier",
            risk=20,
            findings=[f"Custom Vision 호출에 필요한 환경변수가 없습니다: {', '.join(missing)}"],
            evidence={"configured": False},
            next_steps=[".env에 Azure Custom Vision Prediction 정보를 채우면 이미지 분류 도구가 활성화됩니다."],
        ).to_json()

    if not path.exists():
        return ToolResult(
            tool="call_custom_vision_classifier",
            risk=30,
            findings=[f"이미지 파일을 찾지 못했습니다: {path}"],
            evidence={"image_path": str(path)},
            next_steps=["정확한 로컬 이미지 경로를 다시 입력하세요."],
        ).to_json()

    url = endpoint.rstrip("/")
    if "/classify/iterations/" not in url:
        url = f"{url}/customvision/v3.0/Prediction/{project_name}/classify/iterations/{publish_name}/image"

    headers = {"Prediction-Key": key, "Content-Type": "application/octet-stream"}
    try:
        with path.open("rb") as image_file:
            response = requests.post(url, headers=headers, data=image_file.read(), timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return ToolResult(
            tool="call_custom_vision_classifier",
            risk=35,
            findings=[f"Custom Vision 호출 실패: {exc}"],
            evidence={"configured": True, "url": url},
            next_steps=["엔드포인트, publish name, prediction key, 네트워크 연결을 확인하세요."],
        ).to_json()

    predictions = data.get("predictions", [])
    fake_label = os.getenv("FAKE_LABEL", "fake").lower()
    top = max(predictions, key=lambda item: item.get("probability", 0), default={})
    top_tag = str(top.get("tagName", "")).lower()
    probability = float(top.get("probability", 0) or 0)
    risk = int(probability * 100) if fake_label in top_tag else int((1 - probability) * 45)

    return ToolResult(
        tool="call_custom_vision_classifier",
        risk=min(max(risk, 5), 95),
        findings=[f"이미지 분류 최상위 결과: {top.get('tagName', 'unknown')} ({probability:.2%})"],
        evidence={"top_prediction": top, "prediction_count": len(predictions)},
        next_steps=[
            "분류 결과는 보조 신호입니다. 안료, provenance, 현미경/스펙트럼 결과와 함께 판단하세요.",
            "학습 데이터의 작가/시대/매체 분포가 현재 작품과 맞는지 확인하세요.",
        ],
    ).to_json()


@tool
def run_photoholmes_image_forensics(image_path: str, method: str = "zero") -> str:
    """PhotoHolmes CLI가 설치되어 있으면 디지털 이미지 위조 탐지 분석을 실행합니다."""
    path = Path(image_path).expanduser()
    if not path.exists():
        return ToolResult(
            tool="run_photoholmes_image_forensics",
            risk=30,
            findings=[f"이미지 파일을 찾지 못했습니다: {path}"],
            evidence={"image_path": str(path)},
            next_steps=["정확한 로컬 이미지 경로를 다시 입력하세요."],
        ).to_json()

    executable = shutil.which("photoholmes")
    if executable is None:
        return ToolResult(
            tool="run_photoholmes_image_forensics",
            risk=20,
            findings=["PhotoHolmes CLI가 설치되어 있지 않아 이미지 포렌식 분석을 건너뛰었습니다."],
            evidence={"installed": False, "expected_cli": "photoholmes"},
            next_steps=[
                "선택 설치: pip install git+https://github.com/photoholmes/photoholmes.git",
                "설치 후 다시 실행하면 photoholmes run zero 명령으로 이미지 조작 흔적을 검사합니다.",
            ],
        ).to_json()

    with tempfile.TemporaryDirectory(prefix="photoholmes_") as output_dir:
        command = [executable, "run", method, "--output-folder", output_dir, str(path)]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool="run_photoholmes_image_forensics",
                risk=45,
                findings=["PhotoHolmes 분석이 제한 시간 안에 끝나지 않았습니다."],
                evidence={"command": command},
                next_steps=["이미지 크기를 줄이거나 더 가벼운 분석 method를 사용하세요."],
            ).to_json()
        except Exception as exc:
            return ToolResult(
                tool="run_photoholmes_image_forensics",
                risk=35,
                findings=[f"PhotoHolmes 실행 실패: {exc}"],
                evidence={"command": command},
                next_steps=["PhotoHolmes 설치 상태와 CLI 실행 권한을 확인하세요."],
            ).to_json()

        output_files = sorted(str(file.relative_to(output_dir)) for file in Path(output_dir).rglob("*") if file.is_file())
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        findings = []
        risk = 25
        if completed.returncode == 0:
            findings.append("PhotoHolmes 이미지 포렌식 분석이 완료되었습니다.")
            if output_files:
                findings.append(f"분석 산출물 {len(output_files)}개가 생성되었습니다.")
                risk += 10
        else:
            findings.append(f"PhotoHolmes가 오류 코드 {completed.returncode}로 종료되었습니다.")
            risk += 20
        if stderr:
            findings.append(f"PhotoHolmes stderr: {stderr[:500]}")
            risk += 5

        return ToolResult(
            tool="run_photoholmes_image_forensics",
            risk=min(risk, 80),
            findings=findings,
            evidence={
                "installed": True,
                "method": method,
                "returncode": completed.returncode,
                "stdout": stdout[:1000],
                "stderr": stderr[:1000],
                "output_files": output_files[:30],
            },
            next_steps=[
                "PhotoHolmes 산출물의 heatmap 또는 localization 결과를 원본 이미지와 대조하세요.",
                "디지털 조작 신호는 작품 위작 신호가 아니라 이미지 파일 조작 신호로 해석하세요.",
            ],
        ).to_json()


@tool
def run_artsleuth_analysis(image_path: str, artwork_description: str = "") -> str:
    """ArtSleuth가 설치되어 있거나 ARTSLEUTH_COMMAND_TEMPLATE이 설정되어 있으면 미술 이미지 분석을 실행합니다."""
    path = Path(image_path).expanduser()
    if not path.exists():
        return ToolResult(
            tool="run_artsleuth_analysis",
            risk=30,
            findings=[f"이미지 파일을 찾지 못했습니다: {path}"],
            evidence={"image_path": str(path)},
            next_steps=["정확한 로컬 이미지 경로를 다시 입력하세요."],
        ).to_json()

    package_available = importlib.util.find_spec("artsleuth") is not None
    cli = shutil.which("artsleuth")
    command_template = os.getenv("ARTSLEUTH_COMMAND_TEMPLATE")

    if command_template:
        command = shlex.split(command_template.format(image_path=str(path), description=artwork_description))
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool="run_artsleuth_analysis",
                risk=45,
                findings=["ArtSleuth 분석이 제한 시간 안에 끝나지 않았습니다."],
                evidence={"command_template": command_template},
                next_steps=["이미지 크기를 줄이거나 ArtSleuth 명령 템플릿을 더 가벼운 분석으로 바꾸세요."],
            ).to_json()
        except Exception as exc:
            return ToolResult(
                tool="run_artsleuth_analysis",
                risk=35,
                findings=[f"ArtSleuth 실행 실패: {exc}"],
                evidence={"command_template": command_template},
                next_steps=["ARTSLEUTH_COMMAND_TEMPLATE 값을 확인하세요."],
            ).to_json()

        findings = ["ArtSleuth 명령 템플릿 실행이 완료되었습니다."]
        if completed.returncode != 0:
            findings.append(f"ArtSleuth가 오류 코드 {completed.returncode}로 종료되었습니다.")
        return ToolResult(
            tool="run_artsleuth_analysis",
            risk=35 if completed.returncode == 0 else 55,
            findings=findings,
            evidence={
                "installed_package": package_available,
                "cli": cli,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip()[:1500],
                "stderr": completed.stderr.strip()[:1500],
            },
            next_steps=[
                "ArtSleuth 결과를 브러시스트로크, 작풍 귀속, anomaly 신호로 나누어 해석하세요.",
                "모델 학습 작가/시대/매체가 현재 작품과 맞는지 확인하세요.",
            ],
        ).to_json()

    if cli:
        return ToolResult(
            tool="run_artsleuth_analysis",
            risk=25,
            findings=["ArtSleuth CLI는 감지됐지만 호출 형식이 고정되어 있지 않아 자동 실행하지 않았습니다."],
            evidence={"installed_package": package_available, "cli": cli},
            next_steps=[
                "환경변수 ARTSLEUTH_COMMAND_TEMPLATE을 설정하세요.",
                "예: ARTSLEUTH_COMMAND_TEMPLATE='artsleuth analyze {image_path}'",
            ],
        ).to_json()

    if package_available:
        return ToolResult(
            tool="run_artsleuth_analysis",
            risk=25,
            findings=["ArtSleuth Python 패키지는 감지됐지만 안정적인 공개 함수 API를 자동 확인하지 못했습니다."],
            evidence={"installed_package": True, "cli": cli},
            next_steps=[
                "패키지 문서에 맞는 CLI 또는 Python 호출을 ARTSLEUTH_COMMAND_TEMPLATE으로 연결하세요.",
                "예: ARTSLEUTH_COMMAND_TEMPLATE='artsleuth analyze {image_path}'",
            ],
        ).to_json()

    return ToolResult(
        tool="run_artsleuth_analysis",
        risk=20,
        findings=["ArtSleuth가 설치되어 있지 않아 미술 이미지 분석을 건너뛰었습니다."],
        evidence={"installed_package": False, "cli": None},
        next_steps=[
            "선택 설치: pip install artsleuth",
            "설치 후 문서에 맞춰 ARTSLEUTH_COMMAND_TEMPLATE을 설정하면 에이전트 도구로 호출됩니다.",
        ],
    ).to_json()


@tool
def synthesize_risk_score(tool_results_json: str) -> str:
    """여러 도구의 JSON 결과를 받아 종합 위험도를 보수적으로 계산합니다."""
    try:
        payload = json.loads(tool_results_json)
        if isinstance(payload, dict):
            payload = [payload]
    except json.JSONDecodeError:
        return ToolResult(
            tool="synthesize_risk_score",
            risk=40,
            findings=["도구 결과 JSON 파싱에 실패했습니다."],
            evidence={"raw": tool_results_json[:500]},
            next_steps=["각 도구 결과를 JSON 배열로 전달하세요."],
        ).to_json()

    risks = [int(item.get("risk", 0)) for item in payload if isinstance(item, dict)]
    if not risks:
        score = 35
    else:
        score = min(95, round(max(risks) * 0.55 + (sum(risks) / len(risks)) * 0.45))

    findings = []
    for item in payload:
        if isinstance(item, dict):
            findings.extend(item.get("findings", [])[:2])

    return ToolResult(
        tool="synthesize_risk_score",
        risk=score,
        findings=findings[:8] or ["종합할 도구 신호가 부족합니다."],
        evidence={"component_risks": risks},
        next_steps=[
            "고위험 신호가 나온 항목부터 실험실 검증 순서를 잡으세요.",
            "LLM 판단은 법적 감정서가 아니라 검증 설계와 리스크 요약으로 사용하세요.",
        ],
    ).to_json()


SYSTEM_PROMPT = """
너는 미술감정에이전트(가짜미술품검증)다.
정체성:
- 데이터사이언티스트처럼 증거, 불확실성, 검증 가능성을 분리한다.
- 실리콘밸리 개발자처럼 도구를 호출해 근거를 계산한다.
- 앙브르아즈 볼라르와 폴 기욤처럼 시장 provenance, 작가성, 거래 언어의 함정을 읽는다.

규칙:
- 진품/위작을 단정하지 말고 "위작 의심도"와 "검증 우선순위"로 말한다.
- 사용자가 작품 설명을 주면 안료, 노화, provenance 도구를 반드시 고려한다.
- 이미지 경로가 있으면 이미지 메타데이터, Custom Vision, PhotoHolmes, ArtSleuth 도구를 고려한다.
- PhotoHolmes와 ArtSleuth가 미설치라고 나오면 설치/설정 필요성을 리포트에 간단히 적는다.
- 도구 결과를 근거로 사용하고, 근거 없는 확신을 만들지 않는다.
- 답변은 한국어로 작성한다.

최종 출력 형식:
1. 한줄 판단
2. 위작 의심도(0-100)와 이유
3. 도구가 찾은 핵심 이상신호
4. 다음 검증 실험/자료 요청
5. 거래/감정상 주의 문구
""".strip()


def _agent_model_name() -> str:
    raw = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return raw if ":" in raw else f"openai:{raw}"


def build_agent():
    tools = [
        check_pigment_anachronism,
        check_condition_and_aging,
        check_provenance_risk,
        inspect_image_metadata,
        call_custom_vision_classifier,
        run_photoholmes_image_forensics,
        run_artsleuth_analysis,
        synthesize_risk_score,
    ]
    return create_agent(model=_agent_model_name(), tools=tools, system_prompt=SYSTEM_PROMPT)


def _loads_tool_result(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"tool": "unknown", "risk": 35, "findings": [text], "next_steps": []}


def _offline_fallback_report(question: str, image_path: str | None, error: Exception) -> str:
    results = [
        _loads_tool_result(check_pigment_anachronism.invoke({"artwork_description": question})),
        _loads_tool_result(check_condition_and_aging.invoke({"artwork_description": question})),
        _loads_tool_result(check_provenance_risk.invoke({"provenance_text": question})),
    ]
    if image_path:
        results.append(_loads_tool_result(inspect_image_metadata.invoke({"image_path": image_path})))
        results.append(_loads_tool_result(run_photoholmes_image_forensics.invoke({"image_path": image_path})))
        results.append(
            _loads_tool_result(
                run_artsleuth_analysis.invoke({"image_path": image_path, "artwork_description": question})
            )
        )

    risks = [int(item.get("risk", 0)) for item in results]
    score = min(95, round(max(risks) * 0.55 + (sum(risks) / len(risks)) * 0.45)) if risks else 35
    findings = [finding for item in results for finding in item.get("findings", [])]
    next_steps = []
    for item in results:
        next_steps.extend(item.get("next_steps", []))

    findings_text = "\n".join(f"- {finding}" for finding in findings[:8])
    next_steps_text = "\n".join(f"- {step}" for step in dict.fromkeys(next_steps[:8]))

    return f"""1. 한줄 판단
LLM 호출은 실패했지만 로컬 도구 기준 위작 의심도는 {score}/100입니다.

2. 위작 의심도와 이유
도구별 위험도: {risks}

3. 도구가 찾은 핵심 이상신호
{findings_text}

4. 다음 검증 실험/자료 요청
{next_steps_text}

5. 거래/감정상 주의 문구
이 결과는 로컬 규칙 기반 예비 점검입니다. 실물 조사와 과학 분석 전에는 진품/위작을 단정하지 마세요.

LLM 호출 실패 사유: {error}
"""


def run_once(question: str, image_path: str | None = None) -> str:
    agent = build_agent()
    content = question.strip()
    if image_path:
        content += f"\n\n이미지 경로: {image_path}"
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": content}]})
        return result["messages"][-1].content
    except Exception as exc:
        return _offline_fallback_report(question, image_path, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="미술감정에이전트(가짜미술품검증)")
    parser.add_argument("--question", "-q", help="작품 설명, 출처, 의심 단서")
    parser.add_argument("--image", "-i", help="분석할 로컬 이미지 경로")
    parser.add_argument("--interactive", action="store_true", help="대화형 모드 실행")
    args = parser.parse_args()

    if args.interactive:
        print("미술감정에이전트 시작. 종료하려면 exit 입력.")
        while True:
            question = input("\n작품 설명> ").strip()
            if question.lower() in {"exit", "quit", "q"}:
                break
            if not question:
                continue
            print(run_once(question, args.image))
        return

    question = args.question or input("작품 설명을 입력하세요: ").strip()
    if not question:
        raise SystemExit("작품 설명이 비어 있습니다.")
    print(run_once(question, args.image))


if __name__ == "__main__":
    main()
