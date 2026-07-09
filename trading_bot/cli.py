#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet trading bot.

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000

Stop-limit order (bonus order type):
    python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
        --quantity 0.01 --price 65000 --stop-price 65500
"""

import argparse
import sys

from bot.client import BinanceClientError, FuturesTestnetClient
from bot.logging_config import get_logger
from bot.orders import place_order
from bot.validators import ValidationError, validate_order

logger = get_logger()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument("--price", required=False, help="Required for LIMIT / STOP_LIMIT orders")
    parser.add_argument("--stop-price", dest="stop_price", required=False,
                         help="Required for STOP_LIMIT orders")
    parser.add_argument("--time-in-force", dest="time_in_force", default="GTC",
                         choices=["GTC", "IOC", "FOK"])
    return parser


def print_order_summary(order) -> None:
    print("\n--- Order Request Summary ---")
    print(f"  Symbol:         {order.symbol}")
    print(f"  Side:           {order.side}")
    print(f"  Type:           {order.order_type}")
    print(f"  Quantity:       {order.quantity}")
    if order.price is not None:
        print(f"  Price:          {order.price}")
    if order.stop_price is not None:
        print(f"  Stop Price:     {order.stop_price}")
    if order.order_type in ("LIMIT", "STOP_LIMIT"):
        print(f"  Time in Force:  {order.time_in_force}")
    print("------------------------------\n")


def print_order_response(result) -> None:
    print("--- Order Response ---")
    if result.success:
        print(f"  Order ID:       {result.order_id}")
        print(f"  Status:         {result.status}")
        print(f"  Executed Qty:   {result.executed_qty}")
        print(f"  Avg Price:      {result.avg_price}")
        print("-----------------------")
        print("SUCCESS: order placed on Binance Futures Testnet.\n")
    else:
        print(f"  Error: {result.error_message}")
        print("-----------------------")
        print("FAILED: order was not placed.\n")


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Validate input (no network calls yet)
    try:
        order = validate_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as e:
        logger.warning("Input validation failed: %s", e)
        print(f"Invalid input: {e}")
        return 1

    print_order_summary(order)

    # 2. Build client (reads API credentials from environment)
    try:
        client = FuturesTestnetClient()
    except BinanceClientError as e:
        logger.error("Failed to initialize client: %s", e)
        print(f"Configuration error: {e}")
        return 1

    # 3. Place order
    result = place_order(client, order)
    print_order_response(result)

    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
