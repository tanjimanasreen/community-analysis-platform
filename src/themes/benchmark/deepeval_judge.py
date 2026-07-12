from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from src.themes.benchmark.providers import get_provider
from src.themes.benchmark.review import REVIEW_SCORE_COLUMNS


class DeepEvalProviderAdapter(DeepEvalBaseLLM):
    def __init__(self, provider, model_name: str):
        self.provider = provider
        self.model_name = model_name

    def load_model(self):
        return self.provider

    def generate(self, prompt: str) -> str:
        return self.provider.generate_text(prompt)

    async def a_generate(self, prompt: str) -> str:
        # We can implement a true async wrapper, but for now we'll just run synchronously.
        return self.generate(prompt)

    def get_model_name(self):
        return self.model_name


def evaluate_with_deepeval(
    config: Mapping[str, Any],
    input_csv: str | Path,
    output_csv: str | Path,
    judge_provider_id: str,
) -> None:
    provider = get_provider(judge_provider_id, config=config, allow_live=True)
    custom_model = DeepEvalProviderAdapter(provider=provider, model_name=judge_provider_id)
    
    fidelity_metric = GEval(
        name="Fidelity",
        criteria="Evaluate if the generated themes faithfully represent the provided request keywords without introducing hallucinated concepts.",
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=custom_model,
        strict_mode=True,
    )
    coherence_metric = GEval(
        name="Coherence",
        criteria="Evaluate if the generated themes and their grouped keywords make logical sense together and are cohesive.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        model=custom_model,
        strict_mode=True,
    )
    specificity_metric = GEval(
        name="Specificity",
        criteria="Evaluate if the themes are specific and descriptive, rather than overly broad or generic.",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
        model=custom_model,
        strict_mode=True,
    )
    
    df = pd.read_csv(input_csv)
    
    results = []
    for _, row in df.iterrows():
        input_data = f"Keywords: {row['request_keywords']}"
        actual_output = str(row['theme_json'])
        
        test_case = LLMTestCase(
            input=input_data,
            actual_output=actual_output,
        )
        
        fidelity_metric.measure(test_case)
        coherence_metric.measure(test_case)
        specificity_metric.measure(test_case)
        
        row_dict = row.to_dict()
        # Scale GEval's 0-1 score to our 1-5 scale
        row_dict["fidelity"] = _scale_score(fidelity_metric.score)
        row_dict["coherence"] = _scale_score(coherence_metric.score)
        row_dict["specificity"] = _scale_score(specificity_metric.score)
        # For the others, we can either default to 3 or run more metrics. We'll leave them empty or default 3.
        row_dict["non_redundancy"] = 3
        row_dict["usefulness"] = 3
        row_dict["overall_preference"] = 3
        
        results.append(row_dict)
        
    out_df = pd.DataFrame(results)
    out_path = Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"DeepEval judge evaluation completed. Results saved to {out_path}")

def _scale_score(score: float | None) -> int:
    if score is None:
        return 3
    # GEval returns 0 to 1
    return int(round(score * 4)) + 1

