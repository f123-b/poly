# PolyQuant Intelligence V1

一个可直接运行的 **Polymarket 量化分析 + 概率预测 + 回测 + Paper Trading + 风控终端**。

V1 的目标不是“让大模型直接下注”，而是建立完整决策链：

`行情 -> 量化特征 -> 概率估计 -> Edge -> 硬风控 -> Paper 执行 -> 审计记录`

## 已完成

- Polymarket Gamma 市场发现（公开数据）
- CLOB Order Book 公共行情读取
- API 异常时自动 Demo Fallback
- OrderBook / Spread / Depth / Imbalance / 流动性 / 成交量特征
- Opportunity Scanner 排行
- 保守概率融合引擎 + 可选 OpenAI-compatible Research 输入
- Probability Edge 信号
- Cross-Market 阈值逻辑异常检测
- Calibration：Brier / Log Loss / ECE
- Smart Money：Polymarket Trader Leaderboard 接口
- Fractional Kelly 建议仓位
- 单市场 / 总敞口 / Edge / Confidence / Spread 硬风控
- Paper Broker：现金、持仓、成交、PnL
- 回测：滑点、费用、ROI、Max Drawdown、Win Rate、Sharpe
- SQLite 预测与交易审计记录
- FastAPI API
- 中文 Quant Dashboard
- Docker / Demo / 单元测试

> **Live 真钱执行默认关闭。** V1 是研究和模拟交易版本，不提供绕过地域限制、平台限制或硬风控的能力。

## 最快启动

### Docker

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

打开：`http://localhost:8000`

### 本地 Python

需要 Python 3.11+：

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
python -m polyquant
```

## 离线 / Demo 模式

`.env`：

```env
POLYQUANT_MODE=demo
```

无需钱包、API Key 或 Polymarket 网络连接即可完整运行 Dashboard、机会扫描、回测和 Paper Trading。

默认 `auto`：优先读取真实 Polymarket 公共行情，失败自动切 Demo。

## 可选 AI Research

支持任意 OpenAI-compatible Chat Completions 服务：

```env
POLYQUANT_LLM_BASE_URL=https://your-provider.example/v1
POLYQUANT_LLM_API_KEY=...
POLYQUANT_LLM_MODEL=...
```

AI 只提供低权重概率研究输入，**不能调用交易执行器**。

## 核心 API

- `GET /api/health`
- `GET /api/markets`
- `GET /api/opportunities?limit=12`
- `GET /api/markets/{market_id}`
- `GET /api/cross-market/anomalies`
- `GET /api/calibration/demo`
- `GET /api/smart-money/leaderboard`
- `GET /api/paper/account`
- `POST /api/paper/orders`
- `POST /api/backtest`
- `POST /api/backtest/demo`

### Paper 下单示例

```json
{
  "market_id": "demo-btc",
  "outcome": "YES",
  "side": "BUY",
  "notional": 100
}
```

请求仍会经过 RiskEngine；Edge、Confidence、Spread 或仓位不符合要求时返回 422 并给出拒绝原因。

## 目录

```text
poly/
├── polyquant/
│   ├── api.py
│   ├── polymarket.py
│   ├── features.py
│   ├── probability.py
│   ├── risk.py
│   ├── portfolio.py
│   ├── backtest.py
│   ├── storage.py
│   └── service.py
├── web/
├── tests/
├── scripts/
├── Dockerfile
├── docker-compose.yml
└── ARCHITECTURE.md
```

## 当前边界与下一版本

V1 已经形成完整、可运行的研究/Paper 闭环，但没有声称已经拥有经过长期样本验证的盈利 Alpha。后续重点应该是：历史盘口数据仓库、Resolved Market Calibration、事件/新闻 Agent、Cross-Market 关系图、Smart Money、PostgreSQL/Timescale、真实安全执行适配器。
