"""Olist 电商经营、留存、RFM 与物流体验分析。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
}


def load_data(raw_dir: Path) -> dict[str, pd.DataFrame]:
    missing = [name for name in FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"缺少数据文件：{', '.join(missing)}。"
            "请下载 Olist 数据集或先运行 generate_demo_data.py。"
        )

    data = {key: pd.read_csv(raw_dir / filename) for key, filename in FILES.items()}
    date_columns = [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for column in date_columns:
        data["orders"][column] = pd.to_datetime(data["orders"][column], errors="coerce")
    return data


def build_order_mart(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    items = data["items"].copy()
    items["price"] = pd.to_numeric(items["price"], errors="coerce").fillna(0)
    items["freight_value"] = pd.to_numeric(
        items["freight_value"], errors="coerce"
    ).fillna(0)
    item_totals = (
        items.assign(gmv=lambda x: x["price"] + x["freight_value"])
        .groupby("order_id", as_index=False)
        .agg(
            product_revenue=("price", "sum"),
            freight_revenue=("freight_value", "sum"),
            gmv=("gmv", "sum"),
            item_count=("order_item_id", "count"),
        )
    )
    reviews = data["reviews"].groupby("order_id", as_index=False)["review_score"].mean()
    mart = (
        data["orders"]
        .merge(data["customers"], on="customer_id", how="left", validate="many_to_one")
        .merge(item_totals, on="order_id", how="left", validate="one_to_one")
        .merge(reviews, on="order_id", how="left", validate="one_to_one")
    )
    mart[["product_revenue", "freight_revenue", "gmv", "item_count"]] = mart[
        ["product_revenue", "freight_revenue", "gmv", "item_count"]
    ].fillna(0)
    mart["purchase_month"] = (
        mart["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    )
    mart["delivery_days"] = (
        mart["order_delivered_customer_date"] - mart["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    mart["is_delayed"] = (
        mart["order_delivered_customer_date"] > mart["order_estimated_delivery_date"]
    )
    return mart


def monthly_metrics(delivered: pd.DataFrame) -> pd.DataFrame:
    ordered = delivered.sort_values(
        ["customer_unique_id", "order_purchase_timestamp", "order_id"]
    ).copy()
    ordered["customer_order_number"] = ordered.groupby("customer_unique_id").cumcount()
    ordered["is_returning"] = ordered["customer_order_number"] > 0

    metrics = (
        ordered.groupby("purchase_month", as_index=False)
        .agg(
            gmv=("gmv", "sum"),
            orders=("order_id", "nunique"),
            active_customers=("customer_unique_id", "nunique"),
            returning_customers=(
                "customer_unique_id",
                lambda s: s[ordered.loc[s.index, "is_returning"]].nunique(),
            ),
        )
        .sort_values("purchase_month")
    )
    metrics["average_order_value"] = metrics["gmv"] / metrics["orders"]
    metrics["new_customers"] = (
        metrics["active_customers"] - metrics["returning_customers"]
    )
    metrics["repeat_customer_rate"] = (
        metrics["returning_customers"] / metrics["active_customers"]
    )
    metrics["gmv_mom_growth"] = metrics["gmv"].pct_change()
    return metrics


def cohort_retention(delivered: pd.DataFrame) -> pd.DataFrame:
    customer_month = delivered[
        ["customer_unique_id", "purchase_month"]
    ].drop_duplicates()
    first_month = customer_month.groupby("customer_unique_id")["purchase_month"].min()
    cohort = customer_month.join(
        first_month.rename("cohort_month"), on="customer_unique_id"
    )
    cohort["month_number"] = (
        (cohort["purchase_month"].dt.year - cohort["cohort_month"].dt.year) * 12
        + cohort["purchase_month"].dt.month
        - cohort["cohort_month"].dt.month
    )
    counts = cohort.pivot_table(
        index="cohort_month",
        columns="month_number",
        values="customer_unique_id",
        aggfunc="nunique",
    )
    return counts.div(counts[0], axis=0).sort_index()


def rfm_segmentation(delivered: pd.DataFrame) -> pd.DataFrame:
    snapshot = delivered["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    rfm = delivered.groupby("customer_unique_id", as_index=False).agg(
        recency_days=(
            "order_purchase_timestamp",
            lambda s: (snapshot - s.max()).days,
        ),
        frequency=("order_id", "nunique"),
        monetary=("gmv", "sum"),
    )
    rfm["r_score"] = 6 - np.ceil(
        rfm["recency_days"].rank(method="first", pct=True) * 5
    ).astype(int)
    rfm["f_score"] = np.ceil(
        rfm["frequency"].rank(method="first", pct=True) * 5
    ).astype(int)
    rfm["m_score"] = np.ceil(rfm["monetary"].rank(method="first", pct=True) * 5).astype(
        int
    )

    conditions = [
        (rfm["r_score"] >= 4) & (rfm["f_score"] >= 4),
        (rfm["r_score"] >= 3) & (rfm["f_score"] >= 3),
        (rfm["r_score"] >= 4) & (rfm["f_score"] <= 2),
        (rfm["r_score"] <= 2) & (rfm["f_score"] >= 3),
        (rfm["r_score"] <= 2) & (rfm["f_score"] <= 2),
    ]
    labels = ["高价值客户", "潜力客户", "新客户", "即将流失客户", "沉睡客户"]
    rfm["segment"] = np.select(conditions, labels, default="一般客户")
    return rfm.sort_values(["r_score", "f_score", "m_score"], ascending=False)


def category_metrics(
    data: dict[str, pd.DataFrame], delivered_ids: pd.Series
) -> pd.DataFrame:
    category = (
        data["items"]
        .merge(data["products"], on="product_id", how="left", validate="many_to_one")
        .loc[lambda x: x["order_id"].isin(delivered_ids)]
        .assign(
            gmv=lambda x: pd.to_numeric(x["price"], errors="coerce").fillna(0)
            + pd.to_numeric(x["freight_value"], errors="coerce").fillna(0)
        )
        .groupby("product_category_name", as_index=False)
        .agg(gmv=("gmv", "sum"), orders=("order_id", "nunique"))
    )
    category["average_order_value"] = category["gmv"] / category["orders"]
    return category.sort_values("gmv", ascending=False)


def save_charts(
    monthly: pd.DataFrame,
    cohort: pd.DataFrame,
    rfm: pd.DataFrame,
    charts_dir: Path,
) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly["purchase_month"], monthly["gmv"], marker="o", color="#2563eb")
    ax.set(title="Monthly GMV", xlabel="", ylabel="GMV")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(charts_dir / "monthly_gmv.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6))
    image = ax.imshow(cohort.fillna(0).to_numpy(), cmap="Blues", vmin=0, vmax=1)
    ax.set(
        title="Customer Cohort Retention",
        xlabel="Months Since First Purchase",
        ylabel="First Purchase Cohort",
    )
    ax.set_xticks(range(len(cohort.columns)), labels=cohort.columns)
    ax.set_yticks(
        range(len(cohort.index)),
        labels=[date.strftime("%Y-%m") for date in cohort.index],
    )
    fig.colorbar(image, ax=ax, format="{x:.0%}")
    fig.tight_layout()
    fig.savefig(charts_dir / "cohort_retention.png", dpi=150)
    plt.close(fig)

    chart_labels = {
        "高价值客户": "Champions",
        "潜力客户": "Potential Loyalists",
        "新客户": "New Customers",
        "即将流失客户": "At Risk",
        "沉睡客户": "Hibernating",
        "一般客户": "Regular Customers",
    }
    segment = (
        rfm.assign(chart_segment=rfm["segment"].map(chart_labels))
        .groupby("chart_segment")["customer_unique_id"]
        .count()
        .sort_values()
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    segment.plot.barh(ax=ax, color="#0f766e")
    ax.set(title="RFM Customer Segments", xlabel="Customers", ylabel="")
    fig.tight_layout()
    fig.savefig(charts_dir / "rfm_segments.png", dpi=150)
    plt.close(fig)


def write_report(
    mart: pd.DataFrame,
    delivered: pd.DataFrame,
    monthly: pd.DataFrame,
    rfm: pd.DataFrame,
    categories: pd.DataFrame,
    output_dir: Path,
) -> None:
    delayed = delivered[delivered["is_delayed"]]
    on_time = delivered[~delivered["is_delayed"]]
    delayed_rate = delivered["is_delayed"].mean()
    score_gap = on_time["review_score"].mean() - delayed["review_score"].mean()
    latest_row = monthly.iloc[-1]
    max_purchase = delivered["order_purchase_timestamp"].max()
    if (
        max_purchase.day < (max_purchase + pd.offsets.MonthEnd(0)).day
        and len(monthly) > 1
    ):
        latest_row = monthly.iloc[-2]
    latest_repeat = latest_row["repeat_customer_rate"]
    cancel_rate = (mart["order_status"] == "canceled").mean()
    top_category = categories.iloc[0]["product_category_name"]
    top_segment = rfm["segment"].value_counts().idxmax()

    summary = {
        "orders_total": int(mart["order_id"].nunique()),
        "delivered_orders": int(delivered["order_id"].nunique()),
        "gmv": round(float(delivered["gmv"].sum()), 2),
        "customers": int(delivered["customer_unique_id"].nunique()),
        "cancel_rate": round(float(cancel_rate), 4),
        "delay_rate": round(float(delayed_rate), 4),
        "on_time_minus_delayed_review_score": (
            None if pd.isna(score_gap) else round(float(score_gap), 2)
        ),
        "latest_complete_month": latest_row["purchase_month"].strftime("%Y-%m"),
        "latest_complete_month_repeat_customer_rate": round(float(latest_repeat), 4),
        "top_category_by_gmv": top_category,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    score_text = "样本不足"
    if not pd.isna(score_gap):
        score_text = f"{score_gap:.2f} 分"
    report = f"""# Olist 电商数据分析报告

## 核心经营结果

- 有效订单：{summary["delivered_orders"]:,} 笔
- GMV：{summary["gmv"]:,.2f}
- 有效客户：{summary["customers"]:,} 人
- 取消率：{summary["cancel_rate"]:.1%}
- 最近完整月份（{summary["latest_complete_month"]}）老客占比：{summary["latest_complete_month_repeat_customer_rate"]:.1%}

## 关键发现

1. **物流体验**：{summary["delay_rate"]:.1%} 的已送达订单晚于承诺日期；准时订单评分比延误订单平均高 {score_text}。
2. **品类贡献**：GMV 最高的品类是 `{top_category}`，应结合利润率和供给稳定性判断是否追加资源。
3. **客户结构**：人数最多的 RFM 分群是“{top_segment}”，具体客户名单见 `rfm_customers.csv`。

## 建议

- 优先检查高延误地区和品类的承运商表现，对首单延误用户设计补偿实验。
- 对高价值客户提供会员权益；对即将流失客户采用有成本上限的召回券。
- 每月持续追踪 GMV、客单价、老客占比及同期群留存，避免只看订单规模。

## 口径与限制

- GMV = 商品金额 + 运费，仅统计状态为 `delivered` 的订单。
- 老客指当月下单前已有成功订单的客户，不等同于当月购买两次的客户。
- Olist 没有曝光、访问和营销成本数据，因此本项目不能计算访问到购买的完整漏斗或广告 ROI。
- 物流与评分结果是观察性相关关系，不能直接解释为因果效应。
"""
    (output_dir / "analysis_report.md").write_text(report, encoding="utf-8")


def run_analysis(raw_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_data(raw_dir)
    mart = build_order_mart(data)
    delivered = mart[
        (mart["order_status"] == "delivered") & mart["order_purchase_timestamp"].notna()
    ].copy()
    if delivered.empty:
        raise ValueError("没有可分析的已送达订单。")

    monthly = monthly_metrics(delivered)
    cohort = cohort_retention(delivered)
    rfm = rfm_segmentation(delivered)
    categories = category_metrics(data, delivered["order_id"])

    mart.to_csv(output_dir / "order_mart.csv", index=False)
    monthly.to_csv(output_dir / "monthly_metrics.csv", index=False)
    cohort.to_csv(output_dir / "cohort_retention.csv")
    rfm.to_csv(output_dir / "rfm_customers.csv", index=False)
    categories.to_csv(output_dir / "category_metrics.csv", index=False)
    save_charts(monthly, cohort, rfm, output_dir / "charts")
    write_report(mart, delivered, monthly, rfm, categories, output_dir)
    print(f"分析完成，结果已写入：{output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Olist 电商数据分析")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    run_analysis(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
