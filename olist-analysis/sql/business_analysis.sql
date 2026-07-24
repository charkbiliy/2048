-- PostgreSQL 示例：先将 Olist CSV 导入同名表，再执行以下分析。
-- 关键原则：先按订单聚合明细表，避免商品、支付、评论多对多连接导致 GMV 膨胀。

WITH item_totals AS (
    SELECT
        order_id,
        SUM(price) AS product_revenue,
        SUM(freight_value) AS freight_revenue,
        SUM(price + freight_value) AS gmv,
        COUNT(*) AS item_count
    FROM olist_order_items_dataset
    GROUP BY order_id
),
order_mart AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        o.order_status,
        CAST(o.order_purchase_timestamp AS timestamp) AS purchased_at,
        CAST(o.order_delivered_customer_date AS timestamp) AS delivered_at,
        CAST(o.order_estimated_delivery_date AS timestamp) AS estimated_at,
        i.gmv,
        i.item_count
    FROM olist_orders_dataset AS o
    JOIN olist_customers_dataset AS c USING (customer_id)
    LEFT JOIN item_totals AS i USING (order_id)
),
delivered_orders AS (
    SELECT
        *,
        DATE_TRUNC('month', purchased_at)::date AS purchase_month,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY purchased_at, order_id
        ) AS customer_order_number
    FROM order_mart
    WHERE order_status = 'delivered'
)
SELECT
    purchase_month,
    ROUND(SUM(gmv)::numeric, 2) AS gmv,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_unique_id) AS active_customers,
    ROUND(
        SUM(gmv)::numeric / NULLIF(COUNT(DISTINCT order_id), 0),
        2
    ) AS average_order_value,
    COUNT(DISTINCT customer_unique_id)
        FILTER (WHERE customer_order_number > 1) AS returning_customers,
    ROUND(
        COUNT(DISTINCT customer_unique_id)
            FILTER (WHERE customer_order_number > 1)::numeric
        / NULLIF(COUNT(DISTINCT customer_unique_id), 0),
        4
    ) AS repeat_customer_rate
FROM delivered_orders
GROUP BY purchase_month
ORDER BY purchase_month;


-- 物流延误与评分：评论先按订单聚合，避免重复评论导致重复订单。
WITH order_reviews AS (
    SELECT order_id, AVG(review_score) AS review_score
    FROM olist_order_reviews_dataset
    GROUP BY order_id
)
SELECT
    c.customer_state,
    COUNT(*) AS delivered_orders,
    ROUND(
        AVG(
            CASE WHEN CAST(o.order_delivered_customer_date AS timestamp)
                         > CAST(o.order_estimated_delivery_date AS timestamp)
                 THEN 1.0 ELSE 0.0 END
        )::numeric,
        4
    ) AS delay_rate,
    ROUND(AVG(r.review_score)::numeric, 2) AS average_review_score
FROM olist_orders_dataset AS o
JOIN olist_customers_dataset AS c USING (customer_id)
LEFT JOIN order_reviews AS r USING (order_id)
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
HAVING COUNT(*) >= 30
ORDER BY delay_rate DESC;
