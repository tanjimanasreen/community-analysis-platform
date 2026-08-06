from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.themes.benchmark.providers import get_provider

logger = logging.getLogger(__name__)

_REQUIRED_REVIEW_COLUMNS = {"request_keywords", "theme_json"}
_SCORE_COLUMNS = (
    "fidelity",
    "coherence",
    "specificity",
    "non_redundancy",
    "usefulness",
    "overall_preference",
)


def _create_deepeval_adapter(provider, model_name: str):
    """Create the optional DeepEval model adapter only when eval deps are used."""
    try:
        from deepeval.models import DeepEvalBaseLLM
    except ModuleNotFoundError as exc:
        raise ImportError(
            "DeepEval evaluation requires the optional 'eval' dependency extra."
        ) from exc

    class DeepEvalProviderAdapter(DeepEvalBaseLLM):
        def load_model(self):
            return provider

        def generate(self, prompt: str) -> str:
            return provider.generate_text(prompt)

        async def a_generate(self, prompt: str) -> str:
            # Do not block DeepEval's event loop when a synchronous provider is used.
            return await asyncio.to_thread(self.generate, prompt)

        def get_model_name(self):
            return model_name

    return DeepEvalProviderAdapter()


def _prepare_eval_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(_REQUIRED_REVIEW_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(
            "DeepEval review artifact is missing required columns: "
            + ", ".join(missing)
        )
    return pd.DataFrame(
        {
            "inputs": [
                {"query": f"Keywords: {value}"}
                for value in frame["request_keywords"].tolist()
            ],
            "outputs": frame["theme_json"].astype(str).tolist(),
        }
    )


def evaluate_with_deepeval(
    config: Mapping[str, Any],
    dataset_id: str | None,
    run_id: str,
    output_base_path: str | Path,
    tracking_uri: str,
) -> Path:
    """Evaluate a frozen benchmark review artifact with DeepEval + MLflow.

    This workflow is intentionally separate from production theme generation.
    Optional dependencies are imported lazily so normal analytical runs do not
    require DeepEval or full MLflow.
    """
    benchmark_config = config.get("benchmark", {})
    judge_provider_id = benchmark_config.get("evaluator_judge")
    if not judge_provider_id:
        raise ValueError("benchmark.evaluator_judge must be configured")

    try:
        import mlflow
        from deepeval.metrics import GEval
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams
        from mlflow.genai.scorers import scorer
    except ModuleNotFoundError as exc:
        raise ImportError(
            "DeepEval evaluation requires the optional 'eval' dependency extra."
        ) from exc

    from src.themes.benchmark.dataset import benchmark_root

    root = benchmark_root(output_base_path, run_id)
    input_file = root / "review" / "blinded_export.parquet"
    output_file = root / "scores" / "deepeval_scores.parquet"
    if not input_file.is_file():
        raise FileNotFoundError(
            f"DeepEval review artifact does not exist: {input_file}"
        )

    provider = get_provider(judge_provider_id, config=config, allow_live=True)
    custom_model = _create_deepeval_adapter(
        provider=provider, model_name=judge_provider_id
    )

    metric_specs = (
        (
            "Fidelity",
            "Evaluate if the generated themes faithfully represent the provided request keywords without introducing hallucinated concepts.",
            [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
        (
            "Coherence",
            "Evaluate if the generated themes and their grouped keywords make logical sense together and are cohesive.",
            [LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
        (
            "Specificity",
            "Evaluate if the themes are specific and descriptive, rather than overly broad or generic.",
            [LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
        (
            "Non-redundancy",
            "Evaluate if the generated themes are distinct from each other without overlapping or redundant concepts.",
            [LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
        (
            "Usefulness",
            "Evaluate if the themes are useful for interpreting the social dynamics and discussions of the community.",
            [LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
        (
            "Overall Preference",
            "Evaluate the overall quality, formatting, and presentation of the themes.",
            [LLMTestCaseParams.ACTUAL_OUTPUT],
        ),
    )
    metrics = {
        name: GEval(
            name=name,
            criteria=criteria,
            evaluation_params=params,
            model=custom_model,
            strict_mode=True,
        )
        for name, criteria, params in metric_specs
    }

    def create_scorer(name: str):
        metric = metrics[name]

        @scorer(name=name)
        def score(inputs, outputs) -> float:
            input_data = inputs.get("query", str(inputs))
            test_case = LLMTestCase(input=input_data, actual_output=outputs)
            metric.measure(test_case)
            return float(_scale_score(metric.score))

        return score

    scorers = [create_scorer(name) for name, _criteria, _params in metric_specs]

    frame = pd.read_parquet(input_file)
    if dataset_id is not None and "dataset_id" in frame.columns:
        frame = frame.loc[frame["dataset_id"].astype(str) == str(dataset_id)].copy()
    if frame.empty:
        raise ValueError("DeepEval review artifact contains no rows to evaluate")
    eval_frame = _prepare_eval_dataframe(frame)

    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri(tracking_uri)
    logger.info(
        "deepeval_started run_id=%s judge=%s rows=%d",
        run_id,
        judge_provider_id,
        len(frame),
    )
    with mlflow.start_run(run_name=f"DeepEval Benchmark {judge_provider_id}"):
        mlflow_results = mlflow.genai.evaluate(data=eval_frame, scorers=scorers)

    eval_table = mlflow_results.tables.get("eval_results")
    if eval_table is None:
        raise RuntimeError("MLflow DeepEval evaluation did not return eval_results")

    table_mapping = {
        "fidelity": "Fidelity/value",
        "coherence": "Coherence/value",
        "specificity": "Specificity/value",
        "non_redundancy": "Non-redundancy/value",
        "usefulness": "Usefulness/value",
        "overall_preference": "Overall Preference/value",
    }
    for output_column, mlflow_column in table_mapping.items():
        if mlflow_column not in eval_table.columns:
            raise RuntimeError(
                f"MLflow DeepEval results are missing column: {mlflow_column}"
            )
        frame[output_column] = (
            pd.to_numeric(eval_table[mlflow_column], errors="coerce")
            .fillna(3)
            .round()
            .clip(1, 5)
            .astype(int)
            .to_numpy()
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_file, index=False)
    logger.info(
        "deepeval_completed run_id=%s judge=%s rows=%d output=%s",
        run_id,
        judge_provider_id,
        len(frame),
        output_file,
    )
    return output_file


def _scale_score(score: float | None) -> int:
    if score is None:
        return 3
    # GEval returns 0..1. Clamp defensive provider/model outliers to 1..5.
    return max(1, min(5, int(round(float(score) * 4)) + 1))
