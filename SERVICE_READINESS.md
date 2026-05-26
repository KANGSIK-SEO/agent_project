# 서비스 보완 설계

이 프로젝트는 데모용 규칙 에이전트에서 실제 서비스형 감정 보조 시스템으로 확장하기 위한 최소 구조를 포함합니다.

## 현재 반영된 보완

- 안료 기준표를 `data/pigments.json`로 분리했습니다.
- 노화/상태 위험 패턴을 `data/condition_patterns.json`로 분리했습니다.
- provenance 위험 표현을 `data/provenance_terms.json`로 분리했습니다.
- 도구 결과에 `sources`, `confidence`, `service_notes` 필드를 추가했습니다.
- 오프라인 fallback 리포트가 도구별 위험도, 신뢰도, 근거 출처를 함께 표시합니다.
- PhotoHolmes와 ArtSleuth는 외부 도구로 분리하고, 설치되지 않아도 서비스가 실패하지 않게 했습니다.

## 운영 서비스에서 추가해야 할 것

- 기준 데이터 출처를 논문, 보존과학 기관, catalogue raisonne, 경매 DB 단위로 검증합니다.
- JSON 기준표를 SQLite/PostgreSQL로 이전하고 관리자 검수 화면을 둡니다.
- XRF, Raman, FTIR, UV, IR, 현미경 이미지를 구조화된 첨부 자료로 받습니다.
- 전문가 리뷰 상태, 정정 이력, 리포트 버전, 사용 동의와 법적 고지를 저장합니다.
- LLM 출력은 진품/위작 확정이 아니라 검증 우선순위와 리스크 요약으로 제한합니다.

## 권장 데이터 모델

```text
pigments
- id
- canonical_name
- aliases
- introduced_year
- commercial_year
- region_notes
- source_url
- source_quality
- reviewer
- updated_at

provenance_records
- artwork_id
- year_start
- year_end
- owner_or_institution
- event_type
- document_ref
- confidence
- verified_by

analysis_runs
- artwork_id
- tool_name
- risk
- confidence
- findings_json
- sources_json
- created_at
```

## 법적/제품 주의

이 시스템은 감정 보조 도구입니다. 최종 판단은 실물 조사, 과학 분석, provenance 원본 자료, 공인 감정 절차와 함께 내려야 합니다.
