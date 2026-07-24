# Olist 电商用户增长分析

一个可复现的数据分析作品集项目，使用巴西 Olist 电商公开数据回答四类业务问题：

1. GMV、订单量、客单价和老客占比如何变化？
2. 不同首购月份的客户留存是否改善？
3. 哪些客户值得重点维护或召回？
4. 物流延误是否伴随更低评分，问题集中在哪里？

项目同时提供兼容真实表结构的演示数据生成器，因此没有 Kaggle 账号也能完整运行。

## 快速运行

需要 Python 3.10 或更高版本。

```bash
cd olist-analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 生成演示数据
python src/generate_demo_data.py

# 执行完整分析
python src/analyze.py

# 运行测试
pytest -q
```

分析结果位于 `output/`，包括：

- `analysis_report.md`：自动生成的业务报告
- `summary.json`：核心指标，可供仪表盘读取
- `monthly_metrics.csv`：月度经营指标
- `cohort_retention.csv`：同期群留存矩阵
- `rfm_customers.csv`：客户分群及 RFM 得分
- `category_metrics.csv`：品类规模及客单价
- `order_mart.csv`：一行一订单的分析宽表
- `charts/`：GMV、留存和客户分群图表

## 使用真实 Olist 数据

从 [Kaggle: Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) 下载并解压 CSV，将以下文件放入 `data/raw/`：

```text
olist_orders_dataset.csv
olist_customers_dataset.csv
olist_order_items_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
```

然后运行：

```bash
python src/analyze.py --raw-dir data/raw --output-dir output
```

原始数据不会提交到 Git。演示数据仅用于验证代码，不能当作真实业务结论。

## 指标口径

| 指标 | 定义 |
|---|---|
| GMV | 已送达订单的商品金额与运费之和 |
| 客单价 | GMV / 已送达订单数 |
| 活跃客户 | 当月至少有一笔已送达订单的去重客户 |
| 老客 | 当月下单之前已有已送达订单的客户 |
| 老客占比 | 当月老客数 / 当月活跃客户数 |
| 同期群留存 | 某首购月客户在第 N 月再次购买的比例 |
| 配送延误 | 实际送达时间晚于预计送达时间 |

这里将订单明细先聚合至订单粒度，再连接客户和评论表，避免多对多连接造成 GMV 重复计算。`sql/business_analysis.sql` 给出了同样逻辑的 PostgreSQL 查询。

## 分析方法

### 月度经营分析

拆解 GMV 的变化来源：

```text
GMV = 订单数 × 客单价
订单数受活跃客户数及客户购买频率共同影响
```

不要仅根据最后一个月的下滑判断业务恶化。Olist 数据的首尾月份可能不完整，应先检查数据覆盖范围。

### 同期群留存

以客户首次成功购买月份为 cohort，第 0 月固定为 100%，之后观察每月再次购买比例。它比总复购率更适合比较不同获客批次。

### RFM 分群

- R（Recency）：距离最近一次购买的天数，越小越好
- F（Frequency）：成功订单数，越大越好
- M（Monetary）：累计 GMV，越大越好

项目按五分位打分，并输出高价值、潜力、新客、即将流失、沉睡及一般客户。分群阈值是运营规则，不是自然真理；用于真实业务时应结合毛利和触达成本校准。

### 物流体验

比较准时与延误订单的评分，并输出订单级配送时长。观察性数据只能证明关联，不能排除地区、品类和订单金额等混杂因素，因此不能直接声称“延误导致差评”。

## 项目结构

```text
olist-analysis/
├── data/raw/                   # 原始 CSV，不提交
├── output/                     # 自动生成结果，不提交
├── sql/business_analysis.sql   # SQL 指标示例
├── src/
│   ├── analyze.py              # 分析主程序
│   └── generate_demo_data.py   # 演示数据生成器
├── tests/test_analysis.py
├── requirements.txt
└── README.md
```

## 如何把它展示成作品集

面试时建议围绕“问题—证据—行动”讲述，而不是逐张解释图表：

> 我先建立一行一订单的数据集，确保多表连接不重复计算收入；随后用月度指标和同期群区分规模增长与客户质量，用 RFM 找到可运营人群，最后定位物流体验风险。建议通过承运商治理和延误用户补偿实验验证改进效果。

可以继续将 CSV 接入 Power BI、Tableau 或 Looker Studio，制作经营总览、客户留存和履约体验三个页面。
