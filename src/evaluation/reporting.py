"""Presentation is a projection of the single metric registry."""
from .compat import canonical_result, canonical_record
from .registry import METRICS, SEMANTIC, REPORT_VERSION as VERSION, STATE_LABELS, spec
PRIMARY_DIRECTORY = "primary_report_" + VERSION.rsplit("-", 1)[-1]
REPORT_DIRECTORY = "report_" + VERSION.rsplit("-", 1)[-1]

normalized_result = canonical_result


def normalized_records(records):
    return [canonical_record(row) for row in records]


def metric_spec(name, *, aggregate=True):
    return spec(name, aggregate=aggregate)


def scale_label(name):
    return "–".join(f"{value:g}" for value in metric_spec(name)["scale"])


def display(value, name, *, aggregate=True, status=None):
    if value is None:
        return STATE_LABELS.get(status, "无可用分数")
    return f"{value:.{metric_spec(name, aggregate=aggregate)['display_decimals']}f}"


def difference_spec(name):
    row = metric_spec(name)
    span = row["scale"][1] - row["scale"][0]
    return {**row, "label": "差值：" + row["label"], "source_scale": row["scale"], "scale": [-span, span],
            "aggregation": "paired_same_task_seed_then_task_source_macro"}
