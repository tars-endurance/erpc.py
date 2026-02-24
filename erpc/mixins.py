"""Mixins for eRPC process management.

Provides :class:`LoggingMixin` for attaching Python logging to eRPC
subprocess output, following the pattern established by
`py-geth <https://github.com/ethereum/py-geth>`_.
"""

from __future__ import annotations

import logging


class LoggingMixin:
    """Mixin that provides a configured :class:`logging.Logger`.

    Attach to any process class to get a ``logger`` property with optional
    file handler support.

    Args:
        logger_name: Name for the logger (default: ``"erpc"``).
        log_file: Optional path to a log file. Adds a
            :class:`logging.FileHandler` when provided.

    Examples:
        ::

            class MyProcess(LoggingMixin):
                pass

            proc = MyProcess(logger_name="my.erpc", log_file="/tmp/erpc.log")
            proc.logger.info("hello")

    """

    def __init__(
        self,
        *args: object,
        logger_name: str = "erpc",
        log_file: str | None = None,
        **kwargs: object,
    ) -> None:
        self._logger = logging.getLogger(logger_name)
        if log_file is not None:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            self._logger.addHandler(handler)
        super().__init__(*args, **kwargs)

    @property
    def logger(self) -> logging.Logger:
        """The configured logger instance."""
        return self._logger
