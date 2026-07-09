"""
Input validation for order requests.

Kept independent of the Binance client so it can be unit tested without
any network access, and reused by both the CLI layer and (if added later)
any other front end (web UI, scheduled jobs, etc).
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
TIME_IN_FORCE = {"GTC", "IOC", "FOK"}


class ValidationError(Exception):
    """Raised when user-supplied order parameters are invalid."""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "GTC"


def _to_decimal(value, field_name: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"'{field_name}' must be a valid number, got: {value!r}")
    return d


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    stop_price=None,
    time_in_force: str = "GTC",
) -> OrderRequest:
    """
    Validate raw CLI input and return a clean OrderRequest.
    Raises ValidationError with a human-readable message on any problem.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol is required, e.g. BTCUSDT")
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValidationError(f"Symbol '{symbol}' looks invalid (alphanumeric only)")

    if not side or side.upper() not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got: {side!r}")
    side = side.upper()

    if not order_type or order_type.upper() not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got: {order_type!r}"
        )
    order_type = order_type.upper()

    qty = _to_decimal(quantity, "quantity")
    if qty <= 0:
        raise ValidationError(f"Quantity must be > 0, got: {qty}")

    price_dec = None
    stop_price_dec = None

    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders")
        price_dec = _to_decimal(price, "price")
        if price_dec <= 0:
            raise ValidationError(f"Price must be > 0, got: {price_dec}")

    if order_type == "STOP_LIMIT":
        if price is None:
            raise ValidationError("Price is required for STOP_LIMIT orders")
        if stop_price is None:
            raise ValidationError("Stop price is required for STOP_LIMIT orders")
        price_dec = _to_decimal(price, "price")
        stop_price_dec = _to_decimal(stop_price, "stop_price")
        if price_dec <= 0 or stop_price_dec <= 0:
            raise ValidationError("Price and stop_price must both be > 0")

    tif = (time_in_force or "GTC").upper()
    if tif not in TIME_IN_FORCE:
        raise ValidationError(f"time_in_force must be one of {sorted(TIME_IN_FORCE)}, got: {tif!r}")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=qty,
        price=price_dec,
        stop_price=stop_price_dec,
        time_in_force=tif,
    )
