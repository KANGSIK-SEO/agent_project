# 미술감정에이전트: 가짜 미술품 검증

LLM이 여러 도구 함수를 호출해서 작품의 위작 위험 신호를 분석하는 미술감정 에이전트입니다.

이 프로젝트는 진품/위작을 단정하는 감정서가 아니라, 작품을 더 깊게 검증하기 위한 **위험 신호 탐지와 다음 실험 설계**에 초점을 둡니다.

## 무엇을 검증하나요?

- 주장 제작연도와 안료 상용화 시점이 충돌하는지 확인합니다.
- 바니시, 균열, 지지체, 서명 상태가 자연 노화와 맞는지 점검합니다.
- provenance, 즉 소장 이력과 경매/전시 기록의 공백을 찾습니다.
- 이미지 파일의 기본 메타데이터를 확인합니다.
- Azure Custom Vision Prediction 설정이 있으면 이미지 분류 API도 호출합니다.
- 마지막에는 LLM이 도구 결과를 종합해 한국어 감정 리포트를 작성합니다.

## 폴더 구조

```text
.
├── app.py
├── art_forgery_verification_agent.py
├── requirements.txt
├── README.md
└── .gitignore
```

`art_forgery_verification_agent.py`가 핵심 에이전트 파일이고, `app.py`는 웹에서 사용할 수 있는 Streamlit 앱입니다.

## 환경변수 준비

로컬 실행에서는 상위 폴더의 `.env`를 자동으로 읽습니다.

```text
agent0506/.env
```

최소로 필요한 값은 아래 하나입니다.

```env
OPENAI_API_KEY=your_openai_api_key
```

모델을 바꾸고 싶으면 선택적으로 추가합니다.

```env
OPENAI_MODEL=gpt-4o-mini
```

Azure Custom Vision까지 쓰려면 아래 값도 `.env`에 넣습니다.

```env
PREDICTION_ENDPOINT=your_prediction_endpoint
PREDICTION_KEY=your_prediction_key
PROJECT_NAME=your_project_name_or_id
PUBLISH_NAME=your_iteration_publish_name
GENUINE_LABEL=genuine
FAKE_LABEL=fake
```

## 설치

```bash
cd "/Users/kangsikseo/Downloads/agent0506/미술감정에이전트(가짜미술품검증)"
python -m pip install -r requirements.txt
```

이미 `agent0506/.venv`를 쓰고 있다면 이렇게 실행할 수 있습니다.

```bash
/Users/kangsikseo/Downloads/agent0506/.venv/bin/python -m pip install -r requirements.txt
```

## CLI로 사용하기

작품 설명만 넣어 실행합니다.

```bash
python art_forgery_verification_agent.py \
  --question "1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 새 바니시가 보입니다. 1930년 개인 소장 이후 1985년 경매 기록만 있습니다."
```

이미지 파일도 함께 분석하려면 `--image`를 추가합니다.

```bash
python art_forgery_verification_agent.py \
  --question "19세기 인상주의 유화라고 주장합니다. 서명만 유난히 선명합니다." \
  --image "/path/to/artwork.jpg"
```

대화형 모드도 지원합니다.

```bash
python art_forgery_verification_agent.py --interactive
```

## 웹앱으로 사용하기

Streamlit으로 웹 화면을 실행합니다.

```bash
streamlit run app.py
```

브라우저에서 보통 아래 주소로 접속합니다.

```text
http://localhost:8501
```

## 배포하기

Streamlit Community Cloud에 배포할 때는 아래처럼 설정합니다.

```text
Repository: KANGSIK-SEO/agent_project
Branch: main
Main file path: app.py
```

Streamlit Cloud의 Secrets에는 아래처럼 API 키를 넣습니다.

```toml
OPENAI_API_KEY = "your_openai_api_key"
OPENAI_MODEL = "gpt-4o-mini"
```

Azure Custom Vision을 쓴다면 Secrets에 추가합니다.

```toml
PREDICTION_ENDPOINT = "your_prediction_endpoint"
PREDICTION_KEY = "your_prediction_key"
PROJECT_NAME = "your_project_name_or_id"
PUBLISH_NAME = "your_iteration_publish_name"
GENUINE_LABEL = "genuine"
FAKE_LABEL = "fake"
```

## 코드에서 직접 쓰기

다른 Python 코드에서 에이전트를 함수처럼 호출할 수도 있습니다.

```python
from art_forgery_verification_agent import run_once

report = run_once(
    "1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 새 바니시가 보입니다."
)

print(report)
```

이미지 경로를 함께 넘기는 예시입니다.

```python
from art_forgery_verification_agent import run_once

report = run_once(
    question="19세기 인상주의 유화라고 주장합니다. 서명만 유난히 선명합니다.",
    image_path="/path/to/artwork.jpg",
)

print(report)
```

## 주요 도구 함수

```python
check_pigment_anachronism("1780년 작품인데 티타늄 화이트가 검출됨")
```

주장 연도와 안료 상용화 시점이 충돌하는지 확인합니다.

```python
check_condition_and_aging("캔버스는 오래됐지만 새 바니시와 서명만 선명함")
```

바니시, 균열, 지지체, 서명 등 자연 노화와 맞지 않는 단서를 찾습니다.

```python
check_provenance_risk("1930년 개인 소장, 1985년 경매. 감정서 없음")
```

소장 이력과 거래 기록의 공백, 약한 표현, 감정서 부재를 점검합니다.

## 결과 해석

리포트는 보통 아래 형식으로 나옵니다.

```text
1. 한줄 판단
2. 위작 의심도(0-100)와 이유
3. 도구가 찾은 핵심 이상신호
4. 다음 검증 실험/자료 요청
5. 거래/감정상 주의 문구
```

위작 의심도는 법적 결론이 아닙니다. 안료 분석, 현미경 조사, UV/IR 촬영, provenance 원본 자료 확인 같은 추가 검증 순서를 잡기 위한 점수입니다.

## 주의

이 에이전트는 법적 감정서가 아닙니다. 최종 판단은 원본 실물 조사, 과학 분석, provenance 원본 자료, 공인 감정 절차와 함께 내려야 합니다.
