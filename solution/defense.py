"""Data Siege detector using only the documented context and toolkit."""

from api import Verdict


def register(ctx):
    ctx.on("data_batch", check_data_batch)
    ctx.on("contract_checkpoint", check_contract_checkpoint)
    ctx.on("lineage_run", check_lineage_run)
    ctx.on("feature_materialization", check_feature_materialization)
    ctx.on("embedding_batch", check_embedding_batch)


def _limit(ctx, name):
    baseline = ctx.baseline
    if isinstance(baseline, dict):
        return baseline[name]
    return getattr(baseline, name)


def _outside(value, lower, upper, fraction=1.0):
    """Use a fraction of the published three-sigma interval."""
    center = (lower + upper) / 2.0
    half_width = (upper - lower) / 2.0 * fraction
    return value < center - half_width or value > center + half_width


def check_data_batch(payload, ctx):
    profile = ctx.tools.batch_profile(payload["batch_id"])
    if "error" in profile:
        return Verdict(alert=False, pillar="checks")

    count_bad = _outside(
        profile["row_count"],
        _limit(ctx, "row_count_min"),
        _limit(ctx, "row_count_max"),
        0.75,
    )
    amount_bad = _outside(
        profile["mean_amount"],
        _limit(ctx, "mean_amount_min"),
        _limit(ctx, "mean_amount_max"),
        0.75,
    )
    null_bad = profile["null_rate"]["customer_id"] > 0.82 * _limit(ctx, "null_rate_max")
    freshness_bad = profile["staleness_min"] > 0.90 * _limit(ctx, "staleness_min_max")
    return Verdict(alert=count_bad or amount_bad or null_bad or freshness_bad, pillar="checks")


def check_contract_checkpoint(payload, ctx):
    diff = ctx.tools.contract_diff(payload["contract_id"], payload["checkpoint_batch_id"])
    if "error" in diff:
        return Verdict(alert=False, pillar="contracts")
    alert = bool(diff["violations"]) or diff["freshness_delay_min"] > 0.90 * _limit(
        ctx, "freshness_delay_max_min"
    )
    return Verdict(alert=alert, pillar="contracts")


def check_lineage_run(payload, ctx):
    graph = ctx.tools.lineage_graph_slice(payload["run_id"])
    if "error" in graph:
        return Verdict(alert=False, pillar="lineage")

    alert = graph["duration_ms"] > 0.86 * _limit(ctx, "lineage_duration_ms_max")
    expected_upstream = payload.get("expected_upstream")
    if expected_upstream is None:
        expected_upstream = payload.get("declared_upstream")
    if expected_upstream is not None:
        alert = alert or set(graph["actual_upstream"]) != set(expected_upstream)
    else:
        alert = alert or len(graph["actual_upstream"]) < 2

    expected_outputs = payload.get("expected_downstream_count")
    if expected_outputs is None:
        expected_outputs = payload.get("declared_downstream_count")
    if expected_outputs is not None:
        alert = alert or graph["actual_downstream_count"] != expected_outputs
    else:
        alert = alert or graph["actual_downstream_count"] == 0
    return Verdict(alert=alert, pillar="lineage")


def check_feature_materialization(payload, ctx):
    drift = ctx.tools.feature_drift(payload["feature_view"], payload["batch_id"])
    if "error" in drift:
        return Verdict(alert=False, pillar="ai_infra")
    alert = drift["mean_shift_sigma"] > 0.75 * _limit(
        ctx, "feature_mean_shift_sigma_max"
    )
    return Verdict(alert=alert, pillar="ai_infra")


def check_embedding_batch(payload, ctx):
    drift = ctx.tools.embedding_drift(payload["corpus"], payload["chunk_batch_id"])
    if "error" in drift:
        return Verdict(alert=False, pillar="ai_infra")
    alert = (
        drift["centroid_shift"] > 0.90 * _limit(ctx, "embedding_centroid_shift_max")
        or drift["avg_doc_age_days"] > 0.92 * _limit(ctx, "corpus_avg_doc_age_days_max")
    )
    return Verdict(alert=alert, pillar="ai_infra")
