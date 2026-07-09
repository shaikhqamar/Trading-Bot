"""
Order placement logic: translates a validated OrderRequest into the
parameters Binance's Futures API expects, submits it via the client
layer, and normalizes the response for display.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceClientError, BinanceNetworkError, FuturesTestnetClient
from bot.logging_config import get_logger
from bot.validators import OrderRequest

logger = get_logger()


@dataclass
class OrderResult:
    success: bool
    raw_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    @property
    def order_id(self):
        return self.raw_response.get("orderId") if self.raw_response else None

    @property
    def status(self):
        return self.raw_response.get("status") if self.raw_response else None

    @property
    def executed_qty(self):
        return self.raw_response.get("executedQty") if self.raw_response else None

    @property
    def avg_price(self):
        if not self.raw_response:
            return None
        # futures_create_order returns avgPrice for filled/partially-filled orders
        return self.raw_response.get("avgPrice")


def build_binance_params(order: OrderRequest) -> Dict[str, Any]:
    """Map our internal OrderRequest to the kwargs expected by futures_create_order."""
    params: Dict[str, Any] = {
        "symbol": order.symbol,
        "side": order.side,
        "type": "STOP" if order.order_type == "STOP_LIMIT" else order.order_type,
        "quantity": str(order.quantity),
    }

    if order.order_type in ("LIMIT", "STOP_LIMIT"):
        params["price"] = str(order.price)
        params["timeInForce"] = order.time_in_force

    if order.order_type == "STOP_LIMIT":
        params["stopPrice"] = str(order.stop_price)

    return params


def place_order(client: FuturesTestnetClient, order: OrderRequest) -> OrderResult:
    """
    Submit the order through the client and return a normalized OrderResult.
    Never raises for expected failure modes (API rejection / network issue) —
    callers should check `.success` and `.error_message`.
    """
    params = build_binance_params(order)
    logger.info(
        "Submitting %s %s order: symbol=%s qty=%s price=%s",
        order.side, order.order_type, order.symbol, order.quantity, order.price,
    )
    try:
        response = client.place_order(**params)
        return OrderResult(success=True, raw_response=response)
    except BinanceClientError as e:
        logger.error("Order rejected by Binance: %s", e)
        return OrderResult(success=False, error_message=f"Order rejected: {e}")
    except BinanceNetworkError as e:
        logger.error("Network failure while placing order: %s", e)
        return OrderResult(success=False, error_message=f"Network error: {e}")
