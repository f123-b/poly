# PolyQuant Intelligence V3

Polymarket / prediction-market **量化分析 + 概率预测 + 事件研究 + 历史研究仓库 + Smart Money + 实验平台 + 回测 + Paper Trading + 风控 + 受控实盘适配**终端。

核心闭环：

`Market → Feature → Evidence → Probability Components → Edge → Strategy → Hard Risk → Paper/Live Gate → Audit → Resolution → Calibration → Experiment`

## V3 已完成

- Polymarket 公共市场发现、订单簿、历史价格与 Demo fallback
- Spread / Depth / OrderBook Imbalance / Liquidity / Opportunity Scanner
- **可解释概率组件**：Market、OrderBook、Evidence、LLM、Shrink 等组件单独审计
- **Evidence-aware Probability**：事件证据真正进入概率模型，但受 `EVIDENCE_MAX_ADJUSTMENT` 硬上限约束
- Event Intelligence：JSON Feed、市场证据匹配、可靠度/新鲜度/情绪聚合
- Market Graph：阈值包含关系与逻辑概率异常检测
- **Research Warehouse**：Market / Feature / Prediction / Evidence 历史快照、研究历史查询
- **Resolved Calibration**：Brier / Log Loss / ECE
- **Smart Money V3**：排行榜、Trader 画像、持仓/已平仓统计、市场 Smart-Money Flow
- **Experiment Registry**：实验参数、指标、备注持久化；提供离线 demo grid
- Fractional Kelly、单市场/总敞口/Edge/Confidence/Spread/Liquidity 硬风控
- Paper Broker + Auto Paper Trader
- 回测：费用、滑点、ROI、Max Drawdown、Win Rate、Sharpe
- 系统/风控状态 API 与仓库统计
- 可选真实执行：官方 Python SDK、geoblock fail-closed、双重确认、严格名义金额限制
- FastAPI + 中文 Quant Dashboard V3
- Docker、完全离线 Demo、GitHub Actions CI、单元测试

> 自动循环始终只调用 Paper Broker。Live 真钱执行默认关闭，不能通过 AI、事件源或策略绕过硬风控、确认短语或 geoblock preflight。

## 启动

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

打开 `http://localhost:8000`。

本地离线运行：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## 关键设计

### 1. 证据不是交易指令

外部事件源只生成结构化 Evidence。Evidence 对最终概率的影响默认最多 ±3.5 个百分点，随后概率仍会向市场价格收缩。AI Research 同样只是低权重研究输入，无法调用执行器。

### 2. 历史仓库

SQLite 零配置模式现在保存：

- `market_snapshots`
- `feature_snapshots`
- `predictions`
- `evidence_snapshots`
- `resolutions`
- `trader_profiles`
- `experiments`
- Paper/Live 审计记录

接口层保持可迁移设计，后续可替换 PostgreSQL/TimescaleDB。

### 3. Smart Money

V3 使用 Polymarket Data API 的 leaderboard / positions / closed-positions / activity / trades 数据构建 Trader 画像和市场净流评分。Demo 模式提供确定性离线数据。

### 4. Experiment

策略参数和结果不再散落在日志中。每次实验可以持久化：名称、策略、参数、指标、备注，并可比较历史实验。

## 关键 API

### 市场与研究

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/markets`
- `GET /api/opportunities?limit=12`
- `GET /api/markets/{id}`
- `GET /api/markets/{id}/history`
- `GET /api/markets/{id}/research-history`
- `GET /api/markets/{id}/evidence`
- `GET /api/markets/{id}/smart-money`
- `GET /api/events`
- `GET /api/cross-market/graph-anomalies`

### Smart Money

- `GET /api/smart-money/leaderboard`
- `GET /api/smart-money/traders/{wallet}`

### Calibration / Experiments

- `GET /api/calibration/history`
- `POST /api/calibration/resolve`
- `GET /api/experiments`
- `POST /api/experiments`
- `POST /api/experiments/demo-grid`

### Trading / Backtest

- `GET /api/paper/account`
- `POST /api/paper/orders`
- `GET|POST /api/auto/*`
- `POST /api/backtest`
- `POST /api/backtest/demo`
- `GET /api/live/preflight`
- `POST /api/live/orders`（默认禁用）

## 安全边界

V3 不声称已经拥有经过长期真实样本证明的盈利 Alpha。真实资金执行必须独立安装 `.[live]`、显式开启配置、通过所在地/geoblock 检查，并在每笔请求提供固定确认字符串。系统不包含任何绕过地域限制、代理规避或关闭硬风控的路径。

## 开发验证

```bash
pip install -e '.[dev]'
python -m compileall -q polyquant tests
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```

CI 会执行以上核心验证。

更多设计见 `ARCHITECTURE.md`、`docs/V3_PLAN.md`、`docs/V3_SCHEMA.md`、`docs/V3_ACCEPTANCE.md`。
