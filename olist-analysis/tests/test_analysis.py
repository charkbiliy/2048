import json

import pandas as pd

from src.analyze import build_order_mart, load_data, run_analysis
from src.generate_demo_data import generate_demo_data


def test_order_mart_does_not_inflate_item_revenue(tmp_path):
    raw_dir = tmp_path / "raw"
    generate_demo_data(raw_dir, seed=7)
    data = load_data(raw_dir)

    mart = build_order_mart(data)
    expected = (data["items"]["price"] + data["items"]["freight_value"]).sum()

    assert mart["order_id"].is_unique
    assert mart["gmv"].sum() == pytest_approx(expected)


def test_end_to_end_analysis_writes_expected_outputs(tmp_path):
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    generate_demo_data(raw_dir)

    run_analysis(raw_dir, output_dir)

    expected_files = [
        "monthly_metrics.csv",
        "cohort_retention.csv",
        "rfm_customers.csv",
        "category_metrics.csv",
        "summary.json",
        "analysis_report.md",
        "charts/monthly_gmv.png",
        "charts/cohort_retention.png",
        "charts/rfm_segments.png",
    ]
    assert all((output_dir / filename).exists() for filename in expected_files)

    monthly = pd.read_csv(output_dir / "monthly_metrics.csv")
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert not monthly.empty
    assert 0 <= monthly["repeat_customer_rate"].max() <= 1
    assert summary["delivered_orders"] > 0
    assert summary["gmv"] > 0


def pytest_approx(value):
    """避免生产代码依赖 pytest；测试运行时再导入。"""
    import pytest

    return pytest.approx(value)
