# 변경 이력

## 2026-06-10 — 오답 전용 엑셀 파일 추가 저장

### 변경 파일
- `main.py`

### 변경 내용
`save_results` 메서드 끝부분에 오답만 필터링해서 별도 엑셀 파일로 저장하는 코드 추가.

```python
wrong_df = self.df[self.df["성공 여부"] == "X"]
wrong_path = self.excel_path.replace(".xlsx", "_wrong.xlsx")
wrong_df.to_excel(wrong_path, index=False)
print(f"오답 파일 저장 완료: {wrong_path} ({len(wrong_df)}개)")
```

### 실행 결과
실행 후 생성되는 파일:
- `xlsxfile_result.xlsx` — 전체 결과 (기존)
- `xlsxfile_wrong.xlsx` — 오답(`성공 여부 == "X"`)만 모은 파일 (신규)

### 오답 파일 컬럼 구성
전체 결과 파일과 동일한 컬럼 구조를 유지:
- No
- Question
- 도메인 Ground Truth
- LLM 도메인 분류 결과
- 성공 여부 (모두 `X`)
- 추론 과정
- 분류 의견
- 분류 의견 그룹 (모두 `오답`)
