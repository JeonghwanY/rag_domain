import boto3
import os
import json
import math
import pandas as pd
from dotenv import load_dotenv
from domain import BATCH_SIZE, build_prompt
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_WORKERS =14

load_dotenv()

#MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
#MODEL = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
MODEL = "global.anthropic.claude-opus-4-6-v1"
#MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


class DomainClassifier:
    # Bedrock 클라이언트 및 Excel 상태 초기화
    def __init__(self):
        self.model_id = MODEL
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("BEDROCK_REGION"),
        )
        self.df = None
        self.excel_path = None

    # Excel 파일을 읽어 No, Question, Ground Truth 컬럼을 딕셔너리 리스트로 반환
    def load_excel(self, file_path: str) -> list[dict]:
        self.excel_path = file_path
        self.df = pd.read_excel(file_path, dtype={"No": int, "Question": str, "도메인 Ground Truth": str})
        return self.df[["No", "Question", "도메인 Ground Truth"]].to_dict(orient="records")

    # 프롬프트를 Bedrock에 전송하고 모델 응답 텍스트를 반환
    def _call_bedrock(self, prompt: str) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body
        )
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    # 단일 배치를 Bedrock에 요청하고 파싱된 결과 반환
    def _process_batch(self, batch_index: int, batch: list[dict], num_batches: int) -> list[dict]:
        print(f"배치 {batch_index+1}/{num_batches} 처리 중... ({len(batch)}개)")
        prompt = build_prompt(batch)
        raw = self._call_bedrock(prompt)
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print(f"  배치 {batch_index+1} 파싱 실패, raw 응답:\n{raw[:200]}")
            return []

    # 데이터셋을 BATCH_SIZE 단위로 나눠 병렬로 Bedrock에 분류 요청하고 전체 결과 반환
    def classify_batch(self, dataset: list[dict]) -> list[dict]:
        total = len(dataset)
        num_batches = math.ceil(total / BATCH_SIZE)
        batches = [dataset[i * BATCH_SIZE : (i + 1) * BATCH_SIZE] for i in range(num_batches)]
        results = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._process_batch, i, batch, num_batches): i
                for i, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                results.extend(future.result())

        return results

    # 분류 결과를 DataFrame에 병합하고 정확도를 계산해 Excel로 저장
    def save_results(self, results: list[dict]) -> None:
        results_map = {r["no"]: r for r in results}

        self.df["LLM 도메인 분류 결과"] = ""
        self.df["성공 여부"] = ""
        self.df["추론 과정"] = ""
        self.df["분류 의견"] = ""

        for idx, row in self.df.iterrows():
            no = row["No"]
            if no in results_map:
                r = results_map[no]
                self.df.at[idx, "LLM 도메인 분류 결과"] = r["domain"]
                self.df.at[idx, "성공 여부"] = "O" if r["domain"] == row["도메인 Ground Truth"] else "X"
                self.df.at[idx, "추론 과정"] = r.get("reasoning", "")
                self.df.at[idx, "분류 의견"] = r["opinion"]

        self.df["분류 의견 그룹"] = self.df["성공 여부"].apply(
            lambda x: "정답" if x == "O" else "오답"
        )

        output_path = self.excel_path.replace(".xlsx", "_result.xlsx")
        self.df.to_excel(output_path, index=False)

        total = len(self.df)
        correct = (self.df["성공 여부"] == "O").sum()
        print(f"저장 완료: {output_path}")
        print(f"정확도: {correct}/{total} ({correct/total*100:.1f}%)")






if __name__ == "__main__":
    start_time = time.perf_counter()
    
    classifier = DomainClassifier()
    dataset = classifier.load_excel("xlsxfile.xlsx")
    results = classifier.classify_batch(dataset)
    classifier.save_results(results)
    
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"총 실행 시간: {elapsed_time:.2f} 초 (약 {elapsed_time / 60:.1f} 분)")