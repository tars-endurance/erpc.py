"""eRPC log stream capture.

Reads eRPC subprocess output (stdout/stderr) in a background thread and routes
it through Python's :mod:`logging` system. Supports eRPC's JSON log format with
automatic level mapping, and falls back to plain-text INFO logging for
non-JSON lines.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import IO


#: Mapping from eRPC log level strings to Python logging levels.
ERPC_LEVEL_MAP: dict[str, int] = {
    "trace": logging.DEBUG,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "error": logging.ERROR,
}


class ERPCLogStream(threading.Thread):
    """Reads lines from a file descriptor and logs them via Python logging.

    Runs as a daemon thread that reads from a pipe (typically subprocess
    stderr/stdout) line by line. Each line is either parsed as eRPC JSON
    log format or logged as plain text at INFO level.

    Args:
        fd: File descriptor number to read from.
        logger: Logger instance to emit records to.

    Examples:
        ::

            import os, logging
            read_fd, write_fd = os.pipe()
            stream = ERPCLogStream(read_fd, logger=logging.getLogger("erpc"))
            stream.start()

    """

    def __init__(self, fd: int, *, logger: logging.Logger) -> None:
        super().__init__(daemon=True)
        self._fd = fd
        self._logger = logger
        self._stream: IO[bytes] | None = None
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Read lines from the pipe until EOF or stop is requested."""
        self._stream = os.fdopen(self._fd, "rb")
        try:
            for raw_line in self._stream:
                if self._stop_event.is_set():
                    break
                line = raw_line.decode(errors="replace").rstrip("\n\r")
                if not line:
                    continue
                self._process_line(line)
        except (OSError, ValueError):
            # Pipe closed or fd invalid — expected on shutdown.
            pass
        finally:
            self._close_stream()

    def _process_line(self, line: str) -> None:
        """Parse a single line and emit a log record.

        Attempts JSON parsing first. Falls back to plain-text INFO.

        Args:
            line: A single line of output from the eRPC process.

        """
        try:
            data = json.loads(line)
            level_str = data.get("level", "info")
            level = ERPC_LEVEL_MAP.get(level_str, logging.INFO)
            msg = data.get("msg", line)
            self._logger.log(level, msg)
        except (json.JSONDecodeError, AttributeError):
            self._logger.info(line)

    def stop(self) -> None:
        """Signal the reader thread to stop and close the stream.

        Safe to call multiple times. Blocks briefly for the thread to finish.
        """
        self._stop_event.set()
        self._close_stream()

    def _close_stream(self) -> None:
        """Close the underlying stream, ignoring errors."""
        if self._stream is not None:
            try:
                self._stream.close()
            except OSError:
                pass
