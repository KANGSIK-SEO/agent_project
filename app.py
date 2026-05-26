from __future__ import annotations

import tempfile
import os
from pathlib import Path

import streamlit as st

for key, value in st.secrets.items():
    os.environ.setdefault(key, str(value))

from art_forgery_verification_agent import run_once  # noqa: E402


st.set_page_config(
    page_title="미술감정에이전트",
    page_icon="🎨",
    layout="wide",
)

st.title("미술감정에이전트")
st.caption("가짜 미술품 검증을 위한 안료, 노화, provenance, 이미지 단서 분석")

with st.sidebar:
    st.header("입력 자료")
    st.markdown(
        """
        작품 설명에는 가능한 한 아래 정보를 함께 적어 주세요.

        - 주장 제작연도 또는 시대
        - 작가명, 작품명, 매체
        - 안료/재료 분석 결과
        - 바니시, 균열, 서명, 캔버스 상태
        - 소장 이력, 전시 이력, 경매 기록
        """
    )

description = st.text_area(
    "작품 설명",
    height=220,
    placeholder=(
        "예: 1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 "
        "새 바니시가 보입니다. 1930년 개인 소장 이후 1985년 경매 기록만 있습니다."
    ),
)

uploaded_image = st.file_uploader(
    "작품 이미지 또는 확대 사진",
    type=["jpg", "jpeg", "png", "webp", "tif", "tiff"],
)

if st.button("검증 리포트 생성", type="primary", use_container_width=True):
    if not description.strip():
        st.warning("작품 설명을 먼저 입력해 주세요.")
    else:
        image_path = None
        temp_path = None
        if uploaded_image is not None:
            suffix = Path(uploaded_image.name).suffix or ".jpg"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(uploaded_image.getbuffer())
            temp_file.close()
            temp_path = Path(temp_file.name)
            image_path = str(temp_path)
            st.image(uploaded_image, caption=uploaded_image.name, use_container_width=True)

        with st.spinner("도구를 호출해 위작 위험 신호를 분석하는 중입니다..."):
            report = run_once(description, image_path=image_path)

        st.subheader("검증 리포트")
        st.markdown(report)

        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)

st.divider()
st.markdown(
    """
### 빠른 테스트 문장

```text
1780년 유럽 유화라고 주장합니다. 티타늄 화이트가 검출됐고 새 바니시가 보입니다.
1930년 개인 소장 이후 1985년 경매 기록만 있습니다.
```
"""
)
