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
- Auto Paper Trader：自动扫描 → 风控 → 自动模拟成交，可启动/停止/单次运行
- 可选 Live Executor：官方 Python SDK + geoblock fail-closed + 明确确认短语 + 单笔/单市场/日累计硬上限
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

自动交易循环默认关闭；可调用 `/api/auto/start` 启动 **Paper 自动交易**。如需启动时自动运行：`POLYQUANT_AUTO_TRADE_ENABLED=true`。

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
- `GET /api/live/preflight`
- `POST /api/live/orders`（默认禁用，需要显式配置）
- `GET /api/auto/status`
- `POST /api/auto/run-once`
- `POST /api/auto/start` / `POST /api/auto/stop`
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

## 可选真实执行（实验性，默认关闭）

V1 的自动循环仍固定为 **Paper**。真实资金执行器作为独立适配层提供，避免未经验证的自动实盘。启用前必须确认所在地可交易，并使用独立的小额钱包。

安装官方 SDK 依赖：

```bash
pip install -e '.[live]'
```

然后配置：

```env
POLYQUANT_LIVE_EXECUTION_ENABLED=true
POLYQUANT_LIVE_RISK_ACK=I_UNDERSTAND_REAL_MONEY_TRADING
POLYQUANT_LIVE_PRIVATE_KEY=...
POLYQUANT_LIVE_DEPOSIT_WALLET=...
```

先调用 `GET /api/live/preflight`，只有 `ready=true` 才允许继续。每个真实订单还要求请求字段 `confirmation` 精确等于 `EXECUTE_LIVE_ORDER`。V1 默认硬限制：单笔 $10、单市场每日 $20、全局每日 $25，可通过环境变量进一步调低。

真实执行层使用 Polymarket 官方 `AsyncSecureClient.place_market_order`。没有真实凭据的 CI/本地测试不会提交订单。
