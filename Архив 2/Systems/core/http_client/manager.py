# core/http_client/manager.py

import asyncio
from typing import Optional, Dict, Any, Union, TYPE_CHECKING

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout, ClientResponse, ClientResponseError, ClientError
    from aiohttp import ServerTimeoutError as AiohttpTimeoutError
except ImportError:
    aiohttp = None # type: ignore
    ClientSession = Any # type: ignore
    ClientTimeout = Any # type: ignore
    ClientResponse = Any # type: ignore
    ClientResponseError = Any # type: ignore
    ClientError = Any # type: ignore
    AiohttpTimeoutError = Any # type: ignore

from loguru import logger

if TYPE_CHECKING:
    from Systems.core.app_settings import AppSettings


class HTTPClientManager:
    def __init__(self, default_timeout_seconds: int = 10, app_settings: Optional['AppSettings'] = None):
        if not aiohttp:
            msg = ("Библиотека aiohttp не установлена. Пожалуйста, установите ее (`pip install aiohttp`). "
                   "HTTPClientManager не будет работать.")
            logger.critical(msg)
            raise ImportError(msg)
            
        self._session: Optional[ClientSession] = None
        self._default_timeout_config = ClientTimeout(total=default_timeout_seconds) 
        self._app_settings: Optional['AppSettings'] = app_settings 
        self._is_initialized_successfully = False
        logger.info(f"HTTPClientManager инициализирован (таймаут по умолчанию: {default_timeout_seconds} сек).")

    async def initialize(self) -> None:
        if self._session is None or self._session.closed:
            try:
                self._session = ClientSession(timeout=self._default_timeout_config)
                self._is_initialized_successfully = True
                logger.success("aiohttp.ClientSession успешно создан и инициализирован.")
            except Exception as e:
                logger.error(f"Ошибка при создании aiohttp.ClientSession: {e}", exc_info=True)
                self._session = None
                self._is_initialized_successfully = False
                raise 
        else:
            logger.debug("aiohttp.ClientSession уже был инициализирован.")

    async def dispose(self) -> None:
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                logger.info("aiohttp.ClientSession успешно закрыт.")
            except Exception as e:
                logger.error(f"Ошибка при закрытии aiohttp.ClientSession: {e}", exc_info=True)
        self._session = None
        self._is_initialized_successfully = False

    def is_available(self) -> bool:
        return self._session is not None and not self._session.closed and self._is_initialized_successfully

    def _get_session(self) -> ClientSession:
        if not self.is_available():
            msg = "HTTPClientManager (aiohttp.ClientSession) не инициализирован или закрыт! Вызовите initialize()."
            logger.critical(msg)
            raise RuntimeError(msg)
        return self._session # type: ignore 

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[int] = None,
        raise_for_status: bool = False 
    ) -> Optional[ClientResponse]:
        session = self._get_session()
        current_timeout_config = ClientTimeout(total=timeout_seconds) if timeout_seconds is not None else self._default_timeout_config
        
        request_kwargs = {
            "params": params, "data": data, "json": json_data,
            "headers": headers, "timeout": current_timeout_config,
        }
        active_request_kwargs = {k: v for k, v in request_kwargs.items() if v is not None}

        log_context = {"method": method.upper(), "url": url, "params": params, "json_body": json_data is not None}
        logger.debug(f"HTTP Request: {method.upper()} {url}", **log_context)
        
        try:
            async with session.request(method, url, **active_request_kwargs) as response:
                logger.debug(f"HTTP Response: Status {response.status} for {url}", 
                             **log_context, status_code=response.status)
                if raise_for_status:
                    response.raise_for_status() 
                return response
        except ClientResponseError as e: 
            logger.warning(f"HTTP ClientResponseError: {e.status} {e.message} for {url}", **log_context)
            raise 
        except (asyncio.TimeoutError, AiohttpTimeoutError) as e:
            logger.warning(f"HTTP TimeoutError for {url} (timeout: {current_timeout_config.total}s): {type(e).__name__}", **log_context)
            raise 
        except ClientError as e: 
            logger.error(f"HTTP ClientError for {url}: {e}", **log_context, exc_info=True)
            raise 
        except Exception as e: 
            logger.error(f"Unexpected HTTP Error during request to {url}: {e}", **log_context, exc_info=True)
            raise


    async def get_json(
        self, url: str, params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None, timeout_seconds: Optional[int] = None,
        default_on_error: Optional[Any] = None 
    ) -> Optional[Any]:
        response: Optional[ClientResponse] = None
        try:
            response = await self.request("GET", url, params=params, headers=headers, 
                                          timeout_seconds=timeout_seconds, raise_for_status=True)
            if response: 
                return await response.json()
            return default_on_error 
        except (ClientResponseError, asyncio.TimeoutError, AiohttpTimeoutError, ClientError) as e:
            logger.warning(f"HTTP(S) error during get_json for {url}: {type(e).__name__} - {e}")
            if default_on_error is not None: return default_on_error
            raise
        except aiohttp.ContentTypeError as e_json: 
            logger.warning(f"Failed to decode JSON response from {url}: {e_json}")
            if response: logger.trace(f"Response text (JSON error): {(await response.text())[:200]}")
            if default_on_error is not None: return default_on_error
            raise
        except Exception as e_unexp: 
            logger.error(f"Unexpected error in get_json for {url}: {e_unexp}", exc_info=True)
            if default_on_error is not None: return default_on_error
            raise


    async def post_json_response(
        self, url: str, json_data: Optional[Any] = None, params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None, timeout_seconds: Optional[int] = None,
        default_on_error: Optional[Any] = None 
    ) -> Optional[Any]:
        response: Optional[ClientResponse] = None
        try:
            response = await self.request("POST", url, params=params, json_data=json_data, headers=headers,
                                          timeout_seconds=timeout_seconds, raise_for_status=True)
            if response:
                return await response.json()
            return default_on_error
        except (ClientResponseError, asyncio.TimeoutError, AiohttpTimeoutError, ClientError) as e:
            logger.warning(f"HTTP(S) error during post_json for {url}: {type(e).__name__} - {e}")
            if default_on_error is not None: return default_on_error
            raise
        except aiohttp.ContentTypeError as e_json:
            logger.warning(f"Failed to decode JSON response from {url} after POST: {e_json}")
            if response: logger.trace(f"Response text (JSON error): {(await response.text())[:200]}")
            if default_on_error is not None: return default_on_error
            raise
        except Exception as e_unexp:
            logger.error(f"Unexpected error in post_json for {url}: {e_unexp}", exc_info=True)
            if default_on_error is not None: return default_on_error
            raise