# main.py 구조 설명

## 개요

AWS Bedrock의 Claude 모델을 사용해 AIA생명 고객센터 질문을 21개 도메인으로 분류하는 파이프라인입니다.
Excel 파일을 입력받아 LLM 분류 결과와 정확도를 Excel로 저장합니다.

---

## 전체 흐름

```
Excel 입력 → 배치 분할 → 병렬 Bedrock 호출 → 결과 병합 → Excel 저장
```

---

## 설정값

| 변수 | 값 | 설명 |
|---|---|---|
| `MAX_WORKERS` | 20 | 병렬 처리 스레드 수 |
| `MODEL` | claude-haiku-4-5 | 사용할 Bedrock 모델 (주석으로 다른 모델 전환 가능) |
| `BATCH_SIZE` | domain.py에서 import | 배치당 질문 수 (현재 20) |
| `read_timeout` | 300초 | Bedrock 응답 대기 시간 |
| `connect_timeout` | 300초 | Bedrock 연결 시간 |

### 모델 옵션 (주석 전환)
```python
# us.anthropic.claude-haiku-4-5-20251001-v1:0   # US 리전 Haiku
  global.anthropic.claude-haiku-4-5-20251001-v1:0  # Global Haiku (현재 사용)
# global.anthropic.claude-opus-4-6-v1            # Global Opus 4.6
# global.anthropic.claude-sonnet-4-6             # Global Sonnet 4.6
# global.anthropic.claude-opus-4-8               # Global Opus 4.8
```

---

## 클래스: DomainClassifier

### `__init__()`
- AWS Bedrock 클라이언트 초기화
- 환경변수 `BEDROCK_REGION`에서 리전 로드 (`.env` 파일)
- read/connect timeout 300초 설정

### `load_excel(file_path)`
- Excel 파일 읽기
- 필요 컬럼: `No`, `Question`, `도메인 Ground Truth`
- pandas DataFrame으로 저장, dict 리스트로 반환

### `_call_bedrock(prompt)`
- 단일 프롬프트를 Bedrock에 전송
- `max_tokens`: 8192
- 응답 텍스트 반환

### `_process_batch(batch_index, batch, num_batches)`
- 단일 배치 처리
- `domain.py`의 `build_prompt()`로 프롬프트 생성
- Bedrock 호출 후 JSON 파싱
- ` ```json ` 마크다운 fence 자동 제거
- 파싱 실패 시 빈 리스트 반환 (배치 스킵)

### `classify_batch(dataset)`
- 전체 데이터셋을 `BATCH_SIZE` 단위로 분할
- `ThreadPoolExecutor`로 최대 `MAX_WORKERS`개 배치 병렬 처리
- 전체 결과 리스트로 병합 반환

### `save_results(results)`
- 분류 결과를 DataFrame에 병합
- 출력 컬럼:
  - `LLM 도메인 분류 결과`: 모델이 선택한 도메인
  - `성공 여부`: GT와 일치하면 `O`, 불일치하면 `X`
  - `추론 과정`: 모델의 reasoning (CoT)
  - `분류 의견`: 모델의 분류 근거 요약
  - `분류 의견 그룹`: 정답 / 오답
- 결과 파일: 입력파일명 `_result.xlsx`로 저장
- 정확도 콘솔 출력

---

## 실행

```bash
python main.py
```

입력 파일 경로는 `main.py` 하단에서 변경:
```python
dataset = classifier.load_excel("xlsxfile.xlsx")
```

---

## 의존 파일

| 파일 | 역할 |
|---|---|
| `domain.py` | 도메인 목록, 프롬프트 빌더, BATCH_SIZE |
| `.env` | `BEDROCK_REGION` 환경변수 |
| `requirements.txt` | boto3, python-dotenv, pandas, openpyxl |
