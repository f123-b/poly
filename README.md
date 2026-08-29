# PolyQuant Intelligence V2

Polymarket / prediction-market **量化分析 + 概率预测 + 事件研究 + 回测 + Paper Trading + 风控 + 受控实盘适配**终端。

核心决策链：

`市场数据 → Feature → Evidence → Probability → Edge → Strategy → Hard Risk → Paper/Live Gate → Audit → Calibration`

## V2 已完成

- Polymarket 公共市场发现、订单簿与 Demo fallback
- Spread / Depth / OrderBook Imbalance / Liquidity / Opportunity Scanner
- 概率融合引擎与可选 OpenAI-compatible Research 输入
- **Event Intelligence**：事件/新闻 JSON Feed、市场证据匹配、可靠度/新鲜度/情绪聚合、证据审计
- **Market Graph**：阈值包含关系与逻辑概率异常检测
- **Resolved Calibration**：保存市场最终 YES/NO，使用每个市场最新预测计算 Brier / Log Loss / ECE
- Probability Edge、Cross-Market、Smart Money 基础能力
- Fractional Kelly、单市场/总敞口/Edge/Confidence/Spread/Liquidity 硬风控
- Paper Broker + Auto Paper Trader
- 回测：费用、滑点、ROI、Max Drawdown、Win Rate、Sharpe
- 可选真实执行：官方 Python SDK、geoblock fail-closed、双重确认、严格名义金额限制
- SQLite 预测/证据/交易/Resolution 审计
- FastAPI + 中文 Quant Dashboard V2
- Docker、Demo 模式、GitHub Actions CI、单元测试

> 自动循环始终只调用 Paper Broker。Live 真钱执行默认关闭，不能通过 AI 或策略绕过硬风控、确认短语或 geoblock preflight。

## 启动

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

打开 `http://localhost:8000`。

本地运行：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## 数据模式

- `POLYQUANT_MODE=demo`：完全离线，无钱包/Key 即可跑 UI、扫描、回测和 Paper。
- `POLYQUANT_MODE=auto`：优先 Polymarket 公共行情，失败自动 fallback。
- `POLYQUANT_EVENT_FEED_URL=`：可选外部 JSON 事件源；为空时使用确定性的 Demo 证据流。

事件源支持 `[{...}]` 或 `{ "items": [...] }`，字段可包含 `title/summary/source/url/published_at/entities/reliability/sentiment`。

## 关键 API

- `GET /api/health`
- `GET /api/markets`
- `GET /api/opportunities?limit=12`
- `GET /api/markets/{id}`
- `GET /api/markets/{id}/evidence`
- `GET /api/events`
- `GET /api/cross-market/anomalies`
- `GET /api/cross-market/graph-anomalies`
- `GET /api/calibration/history`
- `POST /api/calibration/resolve` body: `{ "market_id": "...", "outcome": "YES" }`
- `GET /api/paper/account`
- `POST /api/paper/orders`
- `GET|POST /api/auto/*`
- `POST /api/backtest`
- `POST /api/backtest/demo`
- `GET /api/live/preflight`
- `POST /api/live/orders`（默认禁用）

## 安全边界

V2 不声称策略已经证明长期盈利。真实资金执行必须独立安装 `.[live]`、显式开启配置、通过所在地/geoblock 检查，并在每笔请求提供固定确认字符串。不要使用代理或其他方式绕过平台地域限制。

## 开发验证

```bash
pip install -e '.[dev]'
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```

CI 会执行 compileall、pytest 和 Demo smoke test。

详见 `ARCHITECTURE.md` 与 `docs/IMPLEMENTATION_PLAN_V2.md`。
