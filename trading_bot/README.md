Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI app for placing MARKET, LIMIT, and STOP_LIMIT
orders on Binance Futures Testnet, with input validation, structured
logging, and clean error handling.

Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py            Binance API wrapper (all network calls live here)
    orders.py             Maps validated input -> API params, submits order
    validators.py          CLI input validation (no network dependency)
    logging_config.py      Rotating file + console logging setup
  cli.py                   argparse CLI entry point
  logs/                    trading_bot.log written here at runtime
  requirements.txt
  .env.example
  README.md
```

Layering: `cli.py` only handles argument parsing and printing. `validators.py`
turns raw strings into a typed `OrderRequest` (or raises `ValidationError`).
`orders.py` turns that into Binance API parameters and calls `client.py`,
which is the only module that imports `python-binance` / talks to the network.
This means the validation and order-mapping logic can be unit tested with
zero network access (see "Testing without real API calls" below).

1. Setup

  1.1 Create a Binance Futures Testnet account

1. Go to https://testnet.binancefuture.com
2. Register/log in (this is a separate account system from binance.com — it
   does **not** use your real Binance login).
3. Once logged in, generate an **API Key** and **API Secret** from the
   testnet dashboard (there is an "API Key" panel on the testnet site).
4. The testnet account is pre-funded with test USDT — no real funds are
   involved anywhere in this project.

  1.2 Install dependencies

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate          Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

  1.3 Configure credentials

    Copy `.env.example` to `.env` and fill in your testnet key/   secret, or
    export them directly in your shell:

    ```bash
    export BINANCE_TESTNET_API_KEY="your_testnet_api_key"
    export BINANCE_TESTNET_API_SECRET="your_testnet_api_secret"
    ```

    If you use a `.env` file, load it before running the CLI (e.g.    `source .env`
    if it's shell-exportable, or use `python-dotenv` / `export $(cat .    env | xargs)`).
    The app itself reads credentials from `os.environ`, so any method that gets them into the environment works.

2. How to Run

Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

    Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000
```

    Stop-Limit order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \
  --quantity 0.01 --price 65000 --stop-price 65500
```

    CLI arguments

| Flag              | Required          | Notes                                  |
|-------------------|-------------------|-----------------------------------------|
| `--symbol`        | yes               | e.g. `BTCUSDT`                          |
| `--side`          | yes               | `BUY` or `SELL`                         |
| `--type`          | yes               | `MARKET`, `LIMIT`, or `STOP_LIMIT`      |
| `--quantity`      | yes               | Order quantity                          |
| `--price`         | LIMIT/STOP_LIMIT  | Limit price                             |
| `--stop-price`    | STOP_LIMIT only   | Trigger price                           |
| `--time-in-force` | no (default GTC)  | `GTC`, `IOC`, or `FOK`                  |

    Example output

```
--- Order Request Summary ---
  Symbol:         BTCUSDT
  Side:           BUY
  Type:           MARKET
  Quantity:       0.01
------------------------------

--- Order Response ---
  Order ID:       123456789
  Status:         FILLED
  Executed Qty:   0.01
  Avg Price:      68000.50
-----------------------
SUCCESS: order placed on Binance Futures Testnet.
```

On failure (bad symbol, insufficient testnet margin, closed market, etc.)
the app prints a `FAILED:` message with the reason and exits with a non-zero
status code instead of crashing.

   3. Logging

Every request, response, and error is logged to `logs/trading_bot.log`
(rotates at 5MB, keeps 3 backups) as well as printed to the console at
INFO level and above. Log format:

```
<timestamp> | <level> | trading_bot | <message>
```

    Generating the required submission log files

The `logs/` folder ships with two **example** files
(`example_market_order.log`, `example_limit_order.log`) that show the
expected format — these were generated with a mocked client, not a live
API call, since this environment has no network access to
`testnet.binancefuture.com`.

To produce the real log files for submission, run the two commands above
(Market and Limit) yourself with your own testnet credentials, then copy
the relevant entries out of `logs/trading_bot.log`.

   4. Testing without real API calls

`validators.py` and `orders.py` have no direct network dependency, so you
can exercise them without hitting Binance at all:

```python
from bot.validators import validate_order
from bot.orders import place_order
from unittest.mock import MagicMock

order = validate_order("BTCUSDT", "BUY", "MARKET", "0.01")

fake_client = MagicMock()
fake_client.place_order.return_value = {
    "orderId": 1, "status": "FILLED", "executedQty": "0.01", "avgPrice": "68000.5"
}
result = place_order(fake_client, order)
print(result.success, result.order_id, result.status)
```

   5. Error Handling

| Failure mode                          | Where it's caught       | Behavior                                   |
|----------------------------------------|--------------------------|---------------------------------------------|
| Invalid CLI input (bad side, missing price for LIMIT, non-numeric qty, etc.) | `validators.py` (`ValidationError`) | Printed to console, logged as WARNING, exit code 1 |
| Missing API credentials                | `client.py` (`BinanceClientError`) | Printed to console, logged as ERROR, exit code 1 |
| Order rejected by Binance (bad symbol, insufficient margin, min notional, etc.) | `client.py` → `orders.py` (`BinanceClientError`) | Printed as `FAILED:` with the API's reason, logged as ERROR, exit code 2 |
| Network failure (timeout, DNS, connection refused) | `client.py` (`BinanceNetworkError`) | Printed as `FAILED:` with the network error, logged as ERROR, exit code 2 |

   6. Assumptions

- This targets **USDT-M Futures** only (not Coin-M or Spot).
- Quantity and price precision/step-size rules (`LOT_SIZE`, `PRICE_FILTER`)
  are enforced by Binance itself; the app surfaces the resulting API error
  rather than re-implementing exchange filter rules client-side. For
  production use you'd typically fetch `/fapi/v1/exchangeInfo` once and
  validate/round locally before sending.
- `STOP_LIMIT` is implemented as Binance Futures' `STOP` order type (price +
  stopPrice), which is the closest equivalent on this API.
- Credentials are read from environment variables rather than a config file,
  so nothing sensitive is ever written to disk or logged (only order
  parameters and responses are logged — API keys never appear in `client.py`
  log statements).
- The bot places one order per CLI invocation; it does not manage
  positions, cancel/replace, or track open orders beyond the single
  `get_order_status` helper in `client.py`.

   7. Bonus Implemented

- **Third order type:** `STOP_LIMIT` (mapped to Binance's `STOP` futures
  order type), validated the same way as `LIMIT` plus a required
  `--stop-price`.
