"""生成与 Olist 表结构兼容的演示数据，仅用于验证分析流程。"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate_demo_data(output_dir: Path, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    states = np.array(["SP", "RJ", "MG", "PR", "BA"])
    categories = np.array(
        ["health_beauty", "computers_accessories", "home_decor", "sports_leisure"]
    )
    product_ids = [f"product_{i:03d}" for i in range(24)]
    products = pd.DataFrame(
        {
            "product_id": product_ids,
            "product_category_name": np.resize(categories, len(product_ids)),
        }
    )

    unique_customers = [f"user_{i:03d}" for i in range(140)]
    customer_weights = np.linspace(2.8, 0.6, len(unique_customers))
    customer_weights /= customer_weights.sum()

    order_rows: list[dict] = []
    customer_rows: list[dict] = []
    item_rows: list[dict] = []
    review_rows: list[dict] = []
    payment_rows: list[dict] = []

    start = pd.Timestamp("2017-01-01")
    order_count = 360
    for i in range(order_count):
        order_id = f"order_{i:04d}"
        customer_id = f"customer_order_{i:04d}"
        unique_id = rng.choice(unique_customers, p=customer_weights)
        purchase = start + pd.Timedelta(days=int(rng.integers(0, 540)))
        state = rng.choice(states, p=[0.42, 0.20, 0.17, 0.12, 0.09])

        base_days = {"SP": 5, "RJ": 7, "MG": 8, "PR": 9, "BA": 13}[state]
        delayed = bool(rng.random() < (0.10 if state != "BA" else 0.28))
        delivery_days = max(2, base_days + int(rng.normal(0, 2)) + (8 if delayed else 0))
        delivered = purchase + pd.Timedelta(days=delivery_days)
        estimated = purchase + pd.Timedelta(days=base_days + 5)
        status = "canceled" if rng.random() < 0.035 else "delivered"

        order_rows.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_status": status,
                "order_purchase_timestamp": purchase,
                "order_delivered_customer_date": delivered if status == "delivered" else pd.NaT,
                "order_estimated_delivery_date": estimated,
            }
        )
        customer_rows.append(
            {
                "customer_id": customer_id,
                "customer_unique_id": unique_id,
                "customer_city": f"city_{state.lower()}",
                "customer_state": state,
            }
        )

        order_total = 0.0
        for item_number in range(1, int(rng.integers(2, 4))):
            product_id = rng.choice(product_ids)
            price = round(float(rng.lognormal(4.3, 0.55)), 2)
            freight = round(float(price * rng.uniform(0.08, 0.28)), 2)
            order_total += price + freight
            item_rows.append(
                {
                    "order_id": order_id,
                    "order_item_id": item_number,
                    "product_id": product_id,
                    "seller_id": f"seller_{int(rng.integers(1, 10)):02d}",
                    "price": price,
                    "freight_value": freight,
                }
            )

        score_center = 4.45 - (1.45 if delayed else 0) - (0.5 if status == "canceled" else 0)
        review_rows.append(
            {
                "review_id": f"review_{i:04d}",
                "order_id": order_id,
                "review_score": int(np.clip(round(rng.normal(score_center, 0.75)), 1, 5)),
            }
        )
        payment_rows.append(
            {
                "order_id": order_id,
                "payment_sequential": 1,
                "payment_type": rng.choice(
                    ["credit_card", "boleto", "voucher"], p=[0.74, 0.20, 0.06]
                ),
                "payment_installments": int(rng.integers(1, 7)),
                "payment_value": round(order_total, 2),
            }
        )

    frames = {
        "olist_orders_dataset.csv": pd.DataFrame(order_rows),
        "olist_customers_dataset.csv": pd.DataFrame(customer_rows),
        "olist_order_items_dataset.csv": pd.DataFrame(item_rows),
        "olist_order_reviews_dataset.csv": pd.DataFrame(review_rows),
        "olist_order_payments_dataset.csv": pd.DataFrame(payment_rows),
        "olist_products_dataset.csv": products,
    }
    for filename, frame in frames.items():
        frame.to_csv(output_dir / filename, index=False)

    print(f"已生成 {order_count} 笔演示订单：{output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 Olist 兼容演示数据")
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate_demo_data(args.output_dir, args.seed)


if __name__ == "__main__":
    main()
