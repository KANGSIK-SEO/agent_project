# 미술감정에이전트: 가짜 미술품 검증

작품 설명을 입력하면 LLM이 여러 도구 함수를 호출해 위작 위험 신호를 정리하는 에이전트입니다.

핵심은 단순히 "진품/가짜"를 맞히는 것이 아닙니다. 안료, 노화 상태, provenance, 이미지 메타데이터 같은 단서를 나누어 확인하고, 어떤 검증을 다음에 해야 하는지 알려주는 구조입니다.

## 핵심 파일

```text
art_forgery_verification_agent.py  # 에이전트와 도구 함수가 들어 있는 핵심 파일
app.py                             # Streamlit 웹 화면
requirements.txt                   # 필요한 패키지 목록
```

## 전체 흐름

```text
사용자 입력
  ↓
run_once()
  ↓
build_agent()
  ↓
LLM이 필요한 도구 함수 호출
  ↓
안료 / 노화 / 출처 / 이미지 / 모델 분류 결과 수집
  ↓
최종 감정 리포트 생성
```

LLM이 실패해도 `_offline_fallback_report()`가 로컬 도구 함수만 사용해서 기본 리포트를 만들어 줍니다.

## 가장 중요한 함수: run_once()

```python
run_once(question: str, image_path: str | None = None) -> str
```

이 프로젝트를 함수처럼 쓸 때 가장 먼저 쓰는 진입점입니다.

### 역할

- 사용자의 작품 설명을 받습니다.
- 이미지 경로가 있으면 함께 전달합니다.
- 내부에서 에이전트를 만들고 LLM에게 분석을 요청합니다.
- LLM이 도구 함수들을 호출한 뒤 최종 리포트를 반환합니다.
- LLM 호출이 실패하면 로컬 규칙 기반 리포트를 대신 반환합니다.

### 사용 예시

```python
from art_forgery_verification_agent import run_once

report = run_once(
    "1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 새 바니시가 보입니다."
)

print(report)
```

이미지가 있을 때는 이렇게 씁니다.

```python
from art_forgery_verification_agent import run_once

report = run_once(
    question="19세기 인상주의 유화라고 주장합니다. 서명만 유난히 선명합니다.",
    image_path="/path/to/artwork.jpg",
)

print(report)
```

## 도구 함수 1: check_pigment_anachronism()

```python
check_pigment_anachronism(artwork_description: str) -> str
```

### 쉽게 말하면

작품이 주장하는 연도와 사용된 안료가 시대적으로 맞는지 확인합니다.

예를 들어 1780년 작품이라고 주장하는데 티타늄 화이트가 나왔다면 이상합니다. 티타늄 화이트는 1916년 이후 상용화된 안료이기 때문입니다.

### 무엇을 찾나요?

- 설명 속 제작연도
- 설명 속 안료명
- 안료가 실제로 쓰이기 시작한 연도
- 제작연도보다 늦게 나온 안료가 들어갔는지 여부

### 사용 예시

```python
from art_forgery_verification_agent import check_pigment_anachronism

result = check_pigment_anachronism.invoke({
    "artwork_description": "1780년 작품인데 티타늄 화이트가 검출됐습니다."
})

print(result)
```

### 결과에서 봐야 할 것

```text
risk      # 위험도 점수
findings  # 발견한 이상 신호
evidence  # 주장 연도와 감지된 안료
next_steps # 다음 검증 방법
```

## 도구 함수 2: check_condition_and_aging()

```python
check_condition_and_aging(artwork_description: str) -> str
```

### 쉽게 말하면

작품이 오래됐다고 주장하는데 표면 상태가 너무 새롭거나, 균열과 바니시가 자연스럽지 않은지 확인합니다.

### 무엇을 찾나요?

- 새 바니시
- 이상한 균열
- 인공 균열
- 오래된 캔버스와 새 물감의 조합
- 화학약품 처리 흔적
- 서명만 유난히 선명한 경우
- UV 반응이나 스펙트럼 불일치 언급

### 사용 예시

```python
from art_forgery_verification_agent import check_condition_and_aging

result = check_condition_and_aging.invoke({
    "artwork_description": "캔버스는 오래됐지만 새 바니시가 있고 서명만 선명합니다."
})

print(result)
```

### 왜 중요하나요?

위작은 오래된 캔버스 위에 새 그림을 그리거나, 표면에 인공 균열을 만들거나, 바니시를 조작하는 경우가 있습니다. 이 함수는 그런 "노화의 앞뒤가 안 맞는 부분"을 찾습니다.

## 도구 함수 3: check_provenance_risk()

```python
check_provenance_risk(provenance_text: str) -> str
```

### 쉽게 말하면

작품의 소장 이력과 거래 기록이 믿을 만한지 확인합니다.

### 무엇을 찾나요?

- "개인 소장"처럼 구체성이 약한 표현
- "attributed to", "style of", "after" 같은 조심해야 하는 거래 표현
- 감정서 없음
- 출처 불명
- 기록상 긴 공백

### 사용 예시

```python
from art_forgery_verification_agent import check_provenance_risk

result = check_provenance_risk.invoke({
    "provenance_text": "1930년 개인 소장, 1985년 경매. 감정서 없음."
})

print(result)
```

### 왜 중요하나요?

진짜 작품은 보통 전시, 경매, 갤러리, 소장자 기록이 이어집니다. 중간 기록이 비어 있거나 표현이 애매하면 작품 자체가 좋아 보여도 거래 위험이 커집니다.

## 도구 함수 4: inspect_image_metadata()

```python
inspect_image_metadata(image_path: str) -> str
```

### 쉽게 말하면

이미지 파일의 기본 정보를 확인합니다.

이 함수는 작품 자체를 감정한다기보다, 업로드된 이미지가 원본 촬영 파일인지, 편집 흔적이 있는지, EXIF 정보가 남아 있는지 확인하는 보조 도구입니다.

### 무엇을 찾나요?

- 이미지 크기
- 파일 형식
- 파일 용량
- EXIF 존재 여부
- 편집 소프트웨어 정보

### 사용 예시

```python
from art_forgery_verification_agent import inspect_image_metadata

result = inspect_image_metadata.invoke({
    "image_path": "/path/to/artwork.jpg"
})

print(result)
```

### 주의

EXIF가 없다고 바로 위작은 아닙니다. 다만 촬영 원본성 판단이 어려워집니다.

## 도구 함수 5: call_custom_vision_classifier()

```python
call_custom_vision_classifier(image_path: str) -> str
```

### 쉽게 말하면

Azure Custom Vision에 학습된 이미지 분류 모델이 있으면, 그 모델로 작품 이미지를 분류합니다.

### 필요한 환경변수

```env
PREDICTION_ENDPOINT=your_prediction_endpoint
PREDICTION_KEY=your_prediction_key
PROJECT_NAME=your_project_name_or_id
PUBLISH_NAME=your_iteration_publish_name
GENUINE_LABEL=genuine
FAKE_LABEL=fake
```

### 사용 예시

```python
from art_forgery_verification_agent import call_custom_vision_classifier

result = call_custom_vision_classifier.invoke({
    "image_path": "/path/to/artwork.jpg"
})

print(result)
```

### 주의

이미지 분류 모델은 보조 신호입니다. 안료 분석, provenance, 현미경 사진, UV/IR 사진과 함께 봐야 합니다.

## 도구 함수 6: synthesize_risk_score()

```python
synthesize_risk_score(tool_results_json: str) -> str
```

### 쉽게 말하면

여러 도구 함수의 결과를 합쳐서 종합 위험도를 계산합니다.

### 사용 예시

```python
import json
from art_forgery_verification_agent import (
    check_pigment_anachronism,
    check_condition_and_aging,
    synthesize_risk_score,
)

pigment = check_pigment_anachronism.invoke({
    "artwork_description": "1780년 작품인데 티타늄 화이트가 검출됐습니다."
})

aging = check_condition_and_aging.invoke({
    "artwork_description": "새 바니시가 있고 서명만 선명합니다."
})

result = synthesize_risk_score.invoke({
    "tool_results_json": json.dumps([json.loads(pigment), json.loads(aging)], ensure_ascii=False)
})

print(result)
```

### 왜 따로 있나요?

각 도구는 자기 분야만 봅니다. 안료 도구는 안료를 보고, provenance 도구는 출처를 봅니다. 이 함수는 여러 결과를 한 번에 모아 전체 위험도를 계산합니다.

## 에이전트 생성 함수: build_agent()

```python
build_agent()
```

### 역할

LLM 에이전트를 만듭니다.

내부에서 아래 도구들을 LLM에게 연결합니다.

```text
check_pigment_anachronism
check_condition_and_aging
check_provenance_risk
inspect_image_metadata
call_custom_vision_classifier
synthesize_risk_score
```

직접 쓸 일은 많지 않습니다. 보통은 `run_once()`를 쓰면 됩니다.

## 보조 함수들

아래 함수들은 내부에서 쓰는 보조 함수입니다. 직접 호출할 수도 있지만, 일반 사용자는 몰라도 됩니다.

### _years_from_text()

```python
_years_from_text(text: str) -> list[int]
```

문장에서 `1780`, `1930`, `1985` 같은 연도를 찾아 리스트로 반환합니다.

### _claim_year()

```python
_claim_year(text: str) -> int | None
```

문장에서 가장 이른 연도를 주장 제작연도로 추정합니다.

### _mentioned_pigments()

```python
_mentioned_pigments(text: str) -> list[dict]
```

문장에서 안료명을 찾아 안료명과 상용화 연도를 반환합니다.

### _offline_fallback_report()

```python
_offline_fallback_report(question: str, image_path: str | None, error: Exception) -> str
```

LLM 호출이 실패했을 때 로컬 도구 결과만으로 기본 리포트를 만듭니다.

## 결과 데이터 구조: ToolResult

각 도구 함수는 내부적으로 아래 구조를 사용합니다.

```python
ToolResult(
    tool="도구 이름",
    risk=50,
    findings=["발견한 이상 신호"],
    evidence={"근거": "값"},
    next_steps=["다음 검증 단계"],
)
```

결과는 JSON 문자열로 반환됩니다.

### 필드 설명

```text
tool        어떤 도구가 만든 결과인지
risk        0-100 사이 위험도
findings    발견한 이상 신호 목록
evidence    판단에 사용한 근거 데이터
next_steps  다음에 해야 할 검증 방법
```

## 설치와 실행

```bash
cd "/Users/kangsikseo/Downloads/agent0506/미술감정에이전트(가짜미술품검증)"
python -m pip install -r requirements.txt
```

CLI 실행:

```bash
python art_forgery_verification_agent.py \
  --question "1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 새 바니시가 보입니다."
```

웹 화면 실행:

```bash
streamlit run app.py
```

## 환경변수

상위 `agent0506/.env`를 자동으로 읽습니다.

최소 필요:

```env
OPENAI_API_KEY=your_openai_api_key
```

선택:

```env
OPENAI_MODEL=gpt-4o-mini
```

## 리포트 해석 방법

에이전트 리포트는 보통 아래 형식입니다.

```text
1. 한줄 판단
2. 위작 의심도(0-100)와 이유
3. 도구가 찾은 핵심 이상신호
4. 다음 검증 실험/자료 요청
5. 거래/감정상 주의 문구
```

위작 의심도는 최종 감정 결과가 아닙니다. 어떤 단서가 위험하고, 어떤 검증을 먼저 해야 하는지 정리하는 점수입니다.

## 주의

이 에이전트는 법적 감정서가 아닙니다. 최종 판단은 원본 실물 조사, 안료 분석, 현미경 조사, UV/IR 촬영, provenance 원본 자료, 공인 감정 절차와 함께 내려야 합니다.
