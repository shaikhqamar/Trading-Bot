"""
Thin wrapper around python-binance's Futures API, pinned to the
Binance Futures Testnet (USDT-M).

This is the only module that talks to the network. Keeping it isolated
means orders.py / cli.py never import python-binance directly, and this
class is the single place that needs to change if the underlying SDK
or endpoint ever changes.
"""

import os
from typing import Any, Dict, Optional

from binance import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from bot.logging_config import get_logger

logger = get_logger()

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceClientError(Exception):
    """Raised for any Binance API-level error (bad request, rejected order, etc)."""


class BinanceNetworkError(Exception):
    """Raised for connectivity issues (timeout, DNS failure, connection refused)."""


class FuturesTestnetClient:
    """
    Wraps python-binance's Client, forcing all requests to the
    Futures Testnet base URL and centralizing error handling + logging.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")

        if not api_key or not api_secret:
            raise BinanceClientError(
                "Missing API credentials. Set BINANCE_TESTNET_API_KEY and "
                "BINANCE_TESTNET_API_SECRET environment variables, or pass them explicitly."
            )

        # testnet=True switches python-binance's default endpoints to the
        # spot testnet, so we then explicitly override FUTURES_URL to make
        # sure USDT-M futures calls go to the futures testnet host.
        self._client = Client(api_key, api_secret, testnet=True)
        self._client.FUTURES_URL = FUTURES_TESTNET_BASE_URL + "/fapi"

        logger.debug("Initialized FuturesTestnetClient against %s", FUTURES_TESTNET_BASE_URL)

    def get_symbol_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch the latest mark price for a symbol (used for pre-trade sanity checks)."""
        logger.debug("REQUEST get_symbol_price symbol=%s", symbol)
        try:
            result = self._client.futures_symbol_ticker(symbol=symbol)
            logger.debug("RESPONSE get_symbol_price -> %s", result)
            return result
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error("API error fetching price for %s: %s", symbol, e)
            raise BinanceClientError(str(e)) from e
        except (RequestsConnectionError, Timeout, RequestException) as e:
            logger.error("Network error fetching price for %s: %s", symbol, e)
            raise BinanceNetworkError(str(e)) from e

    def place_order(self, **params) -> Dict[str, Any]:
        """
        Place a futures order. `params` is passed straight through to
        python-binance's futures_create_order (symbol, side, type, quantity,
        price, timeInForce, stopPrice, etc). Every request and response
        (or error) is logged.
        """
        logger.info("REQUEST place_order params=%s", params)
        try:
            result = self._client.futures_create_order(**params)
            logger.info("RESPONSE place_order -> %s", result)
            return result
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error("Binance API rejected order %s: %s", params, e)
            raise BinanceClientError(str(e)) from e
        except (RequestsConnectionError, Timeout) as e:
            logger.error("Network error placing order %s: %s", params, e)
            raise BinanceNetworkError(str(e)) from e
        except RequestException as e:
            logger.error("Unexpected request error placing order %s: %s", params, e)
            raise BinanceNetworkError(str(e)) from e

    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Query an order's current status by id (useful after MARKET fills)."""
        logger.debug("REQUEST get_order_status symbol=%s order_id=%s", symbol, order_id)
        try:
            result = self._client.futures_get_order(symbol=symbol, orderId=order_id)
            logger.debug("RESPONSE get_order_status -> %s", result)
            return result
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error("API error fetching order status %s/%s: %s", symbol, order_id, e)
            raise BinanceClientError(str(e)) from e
        except (RequestsConnectionError, Timeout, RequestException) as e:
            logger.error("Network error fetching order status %s/%s: %s", symbol, order_id, e)
            raise BinanceNetworkError(str(e)) from e
