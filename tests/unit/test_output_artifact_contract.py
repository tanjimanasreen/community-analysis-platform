import json

import pandas as pd
import pytest

from src.reporting import output_contract as contract
from src.reporting.output_contract import OutputContractError, verify_output_contract
from src.themes import theme_inputs
from src.topics import topic_inputs


def _config(tmp_path, *, month="03", theme_output=None):
    return {
        "output_base_path": str(tmp_path / "outputs"),
        "data_type": "twitter",
        "content_type": "reply",
        "month": month,
        "year": "2017",
        "theme": {
            "output_dir": str(theme_output or tmp_path / "theme"),
            "render_visuals": False,
        },
    }


def _telegram_config(tmp_path, *, month="01", theme_output=None):
    return {
        "output_base_path": str(tmp_path / "outputs"),
        "data_type": "telegram",
        "content_type": "forward",
        "month": month,
        "year": "2019",
        "date_column": "forwarded_date",
        "theme": {
            "output_dir": str(theme_output or tmp_path / "theme"),
            "render_visuals": False,
        },
    }


def _write_parquet(path, columns, rows=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        rows or [{column: _sample_value(column) for column in columns}], columns=columns
    ).to_parquet(
        path,
        index=False,
    )


def _sample_value(column):
    if column in {
        "absolute_unigram_keywords",
        "absolute_bigram_keywords",
        "weighted_unigram_keywords",
        "weighted_bigram_keywords",
        "members",
        "messages",
        "messages_ids",
        "absolute_members",
        "weighted_members",
        "common_members",
        "uncommon_members",
    }:
        return "[1, 2]" if column in {"members", "messages_ids"} else "['alpha']"
    if "community" in column or column in {
        "source",
        "target",
        "from_id",
        "forwarder_id",
    }:
        return 1
    if column in {"weight", "jaccard_score"}:
        return 1.0
    if column in {
        "total_messages",
        "total_matched",
        "total_absolute",
        "total_weighted",
    }:
        return 1
    return "value"


def _base(config):
    return (
        pd.io.common.stringify_path(config["output_base_path"]),
        config["data_type"],
        config["content_type"],
        config["year"],
    )


def _write_public_outputs(config, months):
    output_base_path, data_type, content_type, year = _base(config)
    base = __import__("pathlib").Path(output_base_path) / data_type
    theme_dir = __import__("pathlib").Path(config["theme"]["output_dir"])

    for month in months:
        _write_parquet(
            base / "network_data" / content_type / f"{month}{year}.parquet",
            contract.get_network_data_required_columns(config),
        )
        _write_parquet(
            base
            / "communities"
            / "graphs"
            / "absolute"
            / content_type
            / f"{month}.parquet",
            contract.COMMUNITY_GRAPH_COLUMNS,
        )
        _write_parquet(
            base
            / "communities"
            / "graphs"
            / "weighted"
            / content_type
            / f"{month}.parquet",
            contract.COMMUNITY_GRAPH_COLUMNS,
        )
        _write_parquet(
            base / "communities" / "matched" / content_type / f"{month}.parquet",
            contract.MATCHED_COMMUNITY_SUMMARY_COLUMNS,
        )
        _write_parquet(
            base / "user_centrality" / content_type / f"{month}.parquet",
            contract.USER_CENTRALITY_COLUMNS,
        )
        _write_parquet(
            base / "count_user_messages" / content_type / f"{month}.parquet",
            contract.COUNT_USER_MESSAGES_COLUMNS,
        )
        _write_parquet(
            base / "daily_messages_stat" / content_type / f"{month}.parquet",
            contract.DAILY_MESSAGES_STAT_COLUMNS,
        )
        _write_parquet(
            base / "LDA" / "scores" / content_type / f"{month}.parquet",
            contract.LDA_SCORES_COLUMNS,
        )

        matched_lda = (
            base / "LDA" / "matched" / content_type / f"{month}_{year}.parquet"
        )
        _write_parquet(matched_lda, contract.MATCHED_LDA_COLUMNS)
        theme_inputs.save_theme_inputs(
            matched_lda_csv=matched_lda,
            output_base_path=output_base_path,
            data_type=data_type,
            content_type=content_type,
            month=month,
            year=year,
        )
        _write_parquet(
            theme_dir / f"{month}_{year}_with_themes.parquet",
            contract.THEMED_OUTPUT_COLUMNS,
        )
        topic_inputs.save_topic_inputs(
            absolute_community_messages=pd.DataFrame(
                {
                    "community_number": [1],
                    "messages": [["alpha"]],
                    "messages_ids": [[1]],
                    "total_messages": [1],
                }
            ),
            weighted_community_messages=pd.DataFrame(
                {
                    "community_number": [1],
                    "messages": [["alpha"]],
                    "messages_ids": [[1]],
                    "total_messages": [1],
                }
            ),
            matched_communities=pd.DataFrame(
                {
                    "abs_community": [1],
                    "per_community": [1],
                    "jaccard_score": [1.0],
                    "members": [[1, 2]],
                }
            ),
            partial_matched_communities=pd.DataFrame(
                columns=topic_inputs.PARTIAL_MATCHED_COMMUNITY_COLUMNS
            ),
            output_base_path=output_base_path,
            data_type=data_type,
            content_type=content_type,
            month=month,
            year=year,
        )

    transition_rows = [
        {
            column: _sample_value(column)
            for column in contract.COMMUNITY_TRANSITION_COLUMNS
        }
    ]
    _write_parquet(
        theme_dir / "community_transition.parquet",
        contract.COMMUNITY_TRANSITION_COLUMNS,
        transition_rows,
    )
    _write_parquet(
        theme_dir / "community_paths.parquet",
        contract.COMMUNITY_PATH_COLUMNS,
    )
    _write_parquet(
        theme_dir / "community_path_membership.parquet",
        contract.COMMUNITY_PATH_MEMBERSHIP_COLUMNS,
    )


def test_evolution_output_checks_include_path_contract(tmp_path):
    config = _config(tmp_path)
    checks = {
        check.name: check for check in contract.get_public_artifact_checks(config)
    }

    assert checks["community_path"].required is True
    assert checks["community_path_membership"].required is True
    assert checks["community_path_theme_similarity"].required is False

    config["theme"]["evolution_similarity_enabled"] = True
    enabled = {
        check.name: check for check in contract.get_public_artifact_checks(config)
    }
    assert enabled["community_path_theme_similarity"].required is True


def test_generated_artifact_checks_are_parquet_only(tmp_path):
    config = _config(tmp_path)
    checks = contract.get_public_artifact_checks(config)

    assert checks
    assert all(check.path.suffix == ".parquet" for check in checks)


def test_network_data_contract_uses_canonical_platform_date_column(tmp_path):
    twitter_columns = contract.get_network_data_required_columns(_config(tmp_path))
    telegram_columns = contract.get_network_data_required_columns(
        _telegram_config(tmp_path)
    )

    assert twitter_columns == [*contract.NETWORK_DATA_BASE_COLUMNS, "created_at"]
    assert telegram_columns == [*contract.NETWORK_DATA_BASE_COLUMNS, "forwarded_date"]


def test_public_telegram_network_check_requires_forwarded_date(tmp_path):
    config = _telegram_config(tmp_path)
    network_check = next(
        check
        for check in contract.get_public_artifact_checks(config)
        if check.name == "network_data"
    )

    assert network_check.required_columns == [
        *contract.NETWORK_DATA_BASE_COLUMNS,
        "forwarded_date",
    ]


def test_public_twitter_network_check_still_requires_created_at(tmp_path):
    config = _config(tmp_path)
    network_check = next(
        check
        for check in contract.get_public_artifact_checks(config)
        if check.name == "network_data"
    )

    assert network_check.required_columns == contract.NETWORK_DATA_COLUMNS


def test_output_contract_does_not_accept_csv_as_generated_artifact_fallback(tmp_path):
    config = _config(tmp_path)
    network_csv = (
        tmp_path / "outputs" / "twitter" / "network_data" / "reply" / "032017.csv"
    )
    network_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=contract.NETWORK_DATA_COLUMNS).to_csv(network_csv, index=False)

    with pytest.raises(
        OutputContractError,
        match=r"Missing required artifact network_data: .*032017\.parquet",
    ):
        verify_output_contract(config)


def test_output_contract_column_constants_match_internal_contract_modules():
    assert contract.MATCHED_LDA_COLUMNS == [
        "absolute_community",
        "absolute_unigram_topic",
        "absolute_unigram_keywords",
        "weighted_community",
        "weighted_unigram_topic",
        "weighted_unigram_keywords",
        "absolute_bigram_topic",
        "absolute_bigram_keywords",
        "weighted_bigram_topic",
        "weighted_bigram_keywords",
        "members",
    ]
    assert topic_inputs.MATCHED_COMMUNITY_COLUMNS == [
        "abs_community",
        "per_community",
        "jaccard_score",
        "members",
    ]
    assert set(theme_inputs.REQUIRED_COLUMNS).issubset(contract.MATCHED_LDA_COLUMNS)


def test_verify_output_contract_passes_for_one_month_outputs(tmp_path):
    config = _config(tmp_path)
    _write_public_outputs(config, ["03"])

    result = verify_output_contract(config)

    assert result.checked_count > 10
    assert any("partially_matched" in str(path) for path in result.skipped_optional)


def test_verify_output_contract_accepts_telegram_forwarded_date(tmp_path):
    config = _telegram_config(tmp_path)
    _write_public_outputs(config, ["01"])

    result = verify_output_contract(config)

    assert result.checked_count > 10


def test_verify_output_contract_rejects_telegram_created_at_without_forwarded_date(
    tmp_path,
):
    config = _telegram_config(tmp_path)
    _write_public_outputs(config, ["01"])
    network_path = (
        tmp_path
        / "outputs"
        / "telegram"
        / "network_data"
        / "forward"
        / "012019.parquet"
    )
    _write_parquet(network_path, contract.NETWORK_DATA_COLUMNS)

    with pytest.raises(
        OutputContractError, match=r"missing columns: \['forwarded_date'\]"
    ):
        verify_output_contract(config)


def test_missing_required_artifact_fails_clearly(tmp_path):
    config = _config(tmp_path)

    with pytest.raises(
        OutputContractError, match="Missing required artifact network_data"
    ):
        verify_output_contract(config)


def test_missing_required_column_fails_clearly(tmp_path):
    config = _config(tmp_path)
    _write_public_outputs(config, ["03"])
    bad_path = (
        tmp_path
        / "outputs"
        / "twitter"
        / "communities"
        / "matched"
        / "reply"
        / "03.parquet"
    )
    pd.DataFrame({"month": ["03"]}).to_parquet(bad_path, index=False)

    with pytest.raises(OutputContractError, match="missing columns"):
        verify_output_contract(config)


def test_theme_manifest_hash_mismatch_is_enforced(tmp_path):
    config = _config(tmp_path)
    _write_public_outputs(config, ["03"])
    copied = (
        tmp_path
        / "outputs"
        / "twitter"
        / "_intermediate"
        / "theme_inputs"
        / "reply"
        / "2017"
        / "03_2017.parquet"
    )
    copied.write_text("corrupted\n", encoding="utf-8")

    with pytest.raises(OutputContractError, match="hash mismatch"):
        verify_output_contract(config)


def test_public_matched_lda_schema_matches_internal_theme_copy(tmp_path):
    config = _config(tmp_path)
    _write_public_outputs(config, ["03"])

    public_parquet = (
        tmp_path
        / "outputs"
        / "twitter"
        / "LDA"
        / "matched"
        / "reply"
        / "03_2017.parquet"
    )
    internal_parquet = (
        tmp_path
        / "outputs"
        / "twitter"
        / "_intermediate"
        / "theme_inputs"
        / "reply"
        / "2017"
        / "03_2017.parquet"
    )

    assert list(pd.read_parquet(public_parquet).columns) == list(
        pd.read_parquet(internal_parquet).columns
    )


def test_optional_partial_outputs_are_checked_when_present(tmp_path):
    config = _config(tmp_path)
    _write_public_outputs(config, ["03"])
    partial = (
        tmp_path
        / "outputs"
        / "twitter"
        / "communities"
        / "partially_matched"
        / "reply"
        / "03.parquet"
    )
    _write_parquet(partial, ["month"])

    with pytest.raises(OutputContractError, match="partial_matched_communities"):
        verify_output_contract(config)


def test_longitudinal_contract_requires_two_month_manifest_and_non_empty_transition(
    tmp_path,
):
    config = _config(tmp_path, month="04")
    _write_public_outputs(config, ["03", "04"])

    result = verify_output_contract(config, longitudinal=True)

    manifest = json.loads(
        (
            tmp_path
            / "outputs"
            / "twitter"
            / "_intermediate"
            / "theme_inputs"
            / "reply"
            / "2017"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["months"] == ["03", "04"]
    assert result.checked_count > 20


def test_longitudinal_contract_rejects_empty_transition(tmp_path):
    config = _config(tmp_path, month="04")
    _write_public_outputs(config, ["03", "04"])
    pd.DataFrame(columns=contract.COMMUNITY_TRANSITION_COLUMNS).to_parquet(
        tmp_path / "theme" / "community_transition.parquet",
        index=False,
    )

    with pytest.raises(OutputContractError, match="must contain at least one row"):
        verify_output_contract(config, longitudinal=True)


def test_theme_cluster_summary_contract_includes_ambiguous_serialization_diagnostic():
    columns = contract.get_required_columns_by_artifact()["theme_cluster_summary"]
    assert "excluded_records_ambiguous_general_theme_serialization" in columns
    assert "canonicalization_representation" in columns
    assert "canonicalization_grouping_method" in columns
    assert "canonicalization_similarity_threshold" in columns

    family_columns = contract.get_required_columns_by_artifact()[
        "theme_canonical_family"
    ]
    assert "stage_b_cluster_label" in family_columns
    assert "stage_b_hdbscan_label" in family_columns
