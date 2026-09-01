"""Real local TEI container compatibility smoke script.

Verifies:
1. Docker daemon connectivity.
2. Starting both similarity (port 8080) and clustering (port 8081) TEI containers from the built image.
3. Health check readiness with bounded retry using wait_for_tei_services.
4. TEIClient embedding generation for both models.
5. Contract compliance:
   - 384 dimensions
   - All values finite
   - Similarity normalized (L2 norm == 1.0)
   - Clustering unnormalized raw output compatible with Stage A float64 L2 normalization and HDBSCAN
6. Clean termination and container cleanup in all execution paths.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
import uuid

import numpy as np

from src.themes.tei_client import TEIClient
from src.themes.tei_health import wait_for_tei_services

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("check_tei_compat")


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)


def cleanup_container(container_name: str) -> None:
    logger.info("Cleaning up container %s...", container_name)
    subprocess.run(
        ["docker", "rm", "-f", container_name], capture_output=True, text=True
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real local TEI container compatibility smoke"
    )
    parser.add_argument(
        "--image",
        default="community-analysis-tei:dev",
        help="Docker image tag to test (default: community-analysis-tei:dev)",
    )
    args = parser.parse_args()

    # 1. Verify Docker connectivity
    docker_check = run_cmd(["docker", "info"])
    if docker_check.returncode != 0:
        logger.error("Docker daemon is not reachable: %s", docker_check.stderr)
        return 1

    run_id = uuid.uuid4().hex[:8]
    sim_name = f"tei-sim-smoke-{run_id}"
    clust_name = f"tei-clust-smoke-{run_id}"

    containers_to_clean = [sim_name, clust_name]

    try:
        # 2. Start similarity container (port 8080)
        logger.info("Starting similarity TEI container %s on port 8080...", sim_name)
        sim_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            sim_name,
            "-p",
            "8080:8080",
            args.image,
            "--model-id",
            "/models/similarity",
            "--port",
            "8080",
        ]
        res = run_cmd(sim_cmd)
        if res.returncode != 0:
            logger.error("Failed to start similarity container: %s", res.stderr)
            return 1

        # 3. Start clustering container (port 8081)
        logger.info("Starting clustering TEI container %s on port 8081...", clust_name)
        clust_cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            clust_name,
            "-p",
            "8081:8081",
            args.image,
            "--model-id",
            "/models/clustering",
            "--port",
            "8081",
        ]
        res = run_cmd(clust_cmd)
        if res.returncode != 0:
            logger.error("Failed to start clustering container: %s", res.stderr)
            return 1

        # 4. Wait for readiness using wait_for_tei_services
        logger.info("Waiting for both TEI services to become ready...")
        cfg = {
            "theme": {
                "similarity_provider": "tei",
                "clustering_provider": "tei",
            },
            "theme_similarity": {
                "tei": {
                    "base_url": "http://127.0.0.1:8080",
                }
            },
            "theme_clustering": {
                "tei": {
                    "base_url": "http://127.0.0.1:8081",
                }
            },
        }
        health_status = wait_for_tei_services(
            cfg, attempts=30, interval=1.0, timeout=5.0
        )
        logger.info("TEI services ready: %s", health_status)

        # 5. Test Similarity TEIClient & contract assertions
        logger.info("Testing similarity TEIClient (normalize=True)...")
        sim_client = TEIClient(
            base_url="http://127.0.0.1:8080",
            normalize=True,
            timeout_seconds=10.0,
        )
        sim_texts = [
            "Online disinformation spreading across community networks",
            "Graph analysis reveals high centrality clusters",
        ]
        sim_embeddings = sim_client.encode(sim_texts)
        assert sim_embeddings.shape == (
            2,
            384,
        ), f"Unexpected similarity shape: {sim_embeddings.shape}"
        assert np.all(
            np.isfinite(sim_embeddings)
        ), "Similarity embeddings contain NaN or Inf"

        # Similarity contract: normalized embeddings have L2 norm == 1.0
        norms = np.linalg.norm(sim_embeddings, axis=1)
        for i, norm_val in enumerate(norms):
            assert (
                abs(norm_val - 1.0) < 1e-4
            ), f"Text {i} similarity embedding not normalized: norm={norm_val}"
        logger.info(
            "Similarity TEIClient passed (shape=(2, 384), normalized=True, finite=True)"
        )

        # 6. Test Clustering TEIClient & contract assertions
        logger.info("Testing clustering TEIClient (normalize=False)...")
        clust_client = TEIClient(
            base_url="http://127.0.0.1:8081",
            normalize=False,
            timeout_seconds=10.0,
        )
        clust_texts = [
            "Elections and electoral integrity discussion in channels",
            "Financial market sentiment and cryptocurrency trading groups",
        ]
        clust_embeddings = clust_client.encode(clust_texts)
        assert clust_embeddings.shape == (
            2,
            384,
        ), f"Unexpected clustering shape: {clust_embeddings.shape}"
        assert np.all(
            np.isfinite(clust_embeddings)
        ), "Clustering embeddings contain NaN or Inf"
        logger.info("Clustering TEIClient passed (shape=(2, 384), unnormalized=True)")

        # 7. Exercise real Stage A production consumer (_l2_normalize_embeddings + _fit_hdbscan)
        logger.info("Testing Stage A production consumer with real TEI embeddings...")
        from src.themes.theme_clustering import (
            _l2_normalize_embeddings,
            _fit_hdbscan,
            CANONICALIZATION_DISTANCE_THRESHOLD,
            CANONICALIZATION_LINKAGE,
            CANONICALIZATION_METRIC,
        )

        stage_a_normalized = _l2_normalize_embeddings(
            clust_embeddings, context="Stage-A monthly theme embeddings"
        )
        assert stage_a_normalized.dtype == np.float64
        assert np.allclose(np.linalg.norm(stage_a_normalized, axis=1), 1.0, atol=1e-6)

        stage_a_labels, stage_a_probs = _fit_hdbscan(
            stage_a_normalized,
            min_cluster_size=2,
            metric="euclidean",
            clusterer_factory=None,
            cluster_selection_method="leaf",
            allow_single_cluster=False,
        )
        assert stage_a_labels.shape == (2,)
        assert stage_a_probs.shape == (2,)
        logger.info(
            "Stage A production consumer passed: real TEI embeddings accepted by _fit_hdbscan"
        )

        # 8. Exercise real Stage B production consumer (AgglomerativeClustering with contract constants)
        logger.info("Testing Stage B production consumer with real TEI embeddings...")
        from sklearn.cluster import AgglomerativeClustering

        stage_b_clusterer = AgglomerativeClustering(
            n_clusters=None,
            metric=CANONICALIZATION_METRIC,
            linkage=CANONICALIZATION_LINKAGE,
            distance_threshold=CANONICALIZATION_DISTANCE_THRESHOLD,
            compute_full_tree=True,
        )
        stage_b_labels = stage_b_clusterer.fit_predict(stage_a_normalized)
        assert stage_b_labels.shape == (2,)
        logger.info(
            "Stage B production consumer passed: real TEI embeddings accepted by AgglomerativeClustering"
        )

        # 9. Exercise Theme Similarity consumer (cosine_similarity)
        logger.info("Testing Theme Similarity consumer with real TEI embeddings...")
        from sklearn.metrics.pairwise import cosine_similarity

        sim_matrix = cosine_similarity(sim_embeddings)
        assert sim_matrix.shape == (2, 2)
        assert np.all(np.isfinite(sim_matrix))
        logger.info("Theme Similarity consumer passed: cosine matrix valid")

        logger.info("TEI compatibility smoke tests PASSED successfully!")
        return 0

    finally:
        for c_name in containers_to_clean:
            cleanup_container(c_name)


if __name__ == "__main__":
    sys.exit(main())
