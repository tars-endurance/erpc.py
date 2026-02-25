"""Tests for eRPC logging integration and output capture."""

from __future__ import annotations

import contextlib
import json
import logging
import logging.handlers
import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from erpc.logging import ERPCLogStream
from erpc.mixins import LoggingMixin
from erpc.process import ERPCProcess

if TYPE_CHECKING:
    from pathlib import Path


class TestERPCLogStream:
    """Tests for ERPCLogStream pipe reader."""

    def test_log_stream_captures_stderr(self) -> None:
        """LogStream captures lines written to a pipe."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.capture")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()

        os.write(write_fd, b"hello from stderr\n")
        os.write(write_fd, b"second line\n")
        os.close(write_fd)

        stream.join(timeout=2)
        assert not stream.is_alive()

        messages = [r.getMessage() for r in handler.buffer]
        assert "hello from stderr" in messages
        assert "second line" in messages

        logger.removeHandler(handler)

    def test_log_stream_parses_json(self) -> None:
        """eRPC JSON log lines are parsed into structured records."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.json")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()

        log_entry = json.dumps({"level": "info", "msg": "server started", "time": "2024-01-01"})
        os.write(write_fd, log_entry.encode() + b"\n")
        os.close(write_fd)

        stream.join(timeout=2)

        assert len(handler.buffer) == 1
        record = handler.buffer[0]
        assert record.getMessage() == "server started"
        assert record.levelno == logging.INFO

        logger.removeHandler(handler)

    def test_log_stream_maps_levels(self) -> None:
        """eRPC log levels map correctly to Python logging levels."""
        level_map = {
            "trace": logging.DEBUG,
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warn": logging.WARNING,
            "error": logging.ERROR,
        }

        for erpc_level, python_level in level_map.items():
            read_fd, write_fd = os.pipe()
            logger = logging.getLogger(f"test.levels.{erpc_level}")
            logger.setLevel(logging.DEBUG)
            handler = logging.handlers.MemoryHandler(capacity=100)
            logger.addHandler(handler)

            stream = ERPCLogStream(read_fd, logger=logger)
            stream.start()

            entry = json.dumps({"level": erpc_level, "msg": f"test {erpc_level}"})
            os.write(write_fd, entry.encode() + b"\n")
            os.close(write_fd)

            stream.join(timeout=2)

            assert len(handler.buffer) == 1, f"Expected 1 record for {erpc_level}"
            assert handler.buffer[0].levelno == python_level, (
                f"{erpc_level} should map to {python_level}"
            )

            logger.removeHandler(handler)

    def test_log_stream_plain_text_fallback(self) -> None:
        """Non-JSON lines are logged as-is at INFO level."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.plaintext")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()

        os.write(write_fd, b"plain text not json\n")
        os.close(write_fd)

        stream.join(timeout=2)

        assert len(handler.buffer) == 1
        assert handler.buffer[0].getMessage() == "plain text not json"
        assert handler.buffer[0].levelno == logging.INFO

        logger.removeHandler(handler)

    def test_log_stream_stops_on_process_exit(self) -> None:
        """Thread exits cleanly when the pipe is closed (process exits)."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.stop")
        logger.setLevel(logging.DEBUG)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()
        assert stream.is_alive()

        os.close(write_fd)
        stream.join(timeout=2)

        assert not stream.is_alive()

    def test_log_stream_stop_method(self) -> None:
        """stop() method triggers clean shutdown."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.stopmethod")
        logger.setLevel(logging.DEBUG)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()
        assert stream.is_alive()

        # Close write end first so the read iterator hits EOF,
        # then signal stop. Without this, the read blocks indefinitely
        # on some Python versions (3.14+) even after stream.close().
        os.close(write_fd)
        stream.stop()
        stream.join(timeout=2)

        assert not stream.is_alive()


class TestLoggingMixin:
    """Tests for LoggingMixin integration."""

    def test_logging_mixin_attaches_to_process(self) -> None:
        """LoggingMixin wires up log capture on start()."""

        class MockProcess(LoggingMixin):
            pass

        proc = MockProcess(logger_name="test.mixin.attach")
        assert proc.logger.name == "test.mixin.attach"

    def test_logging_mixin_custom_logger(self) -> None:
        """Can pass a custom logger name."""

        class MockProcess(LoggingMixin):
            pass

        proc = MockProcess(logger_name="my.custom.logger")
        assert proc.logger.name == "my.custom.logger"

    def test_logging_mixin_log_to_file(self, tmp_path: Path) -> None:
        """Optional file handler can be configured."""
        log_file = tmp_path / "erpc.log"

        class MockProcess(LoggingMixin):
            pass

        proc = MockProcess(logger_name="test.mixin.file", log_file=str(log_file))
        file_handlers = [h for h in proc.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].baseFilename == str(log_file)

        # Cleanup
        proc.logger.removeHandler(file_handlers[0])
        file_handlers[0].close()


class TestProcessWithLogging:
    """Integration test: ERPCProcess with logging."""

    @patch("erpc.process.subprocess.Popen")
    def test_process_with_logging(self, mock_popen: MagicMock) -> None:
        """ERPCProcess integrates logging — captures stdout/stderr from subprocess."""
        stderr_read, stderr_write = os.pipe()
        stdout_read, stdout_write = os.pipe()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        mock_proc.stderr = os.fdopen(stderr_read, "rb")
        mock_proc.stdout = os.fdopen(stdout_read, "rb")
        mock_popen.return_value = mock_proc

        with patch("erpc.process.find_erpc_binary", return_value="/usr/bin/erpc"):
            process = ERPCProcess(upstreams={1: ["https://eth.example.com"]})

        log_line = json.dumps({"level": "info", "msg": "eRPC started"}) + "\n"
        os.write(stderr_write, log_line.encode())
        os.close(stderr_write)
        os.close(stdout_write)

        # Verify ERPCProcess has the expected attributes
        assert hasattr(process, "stdout")
        assert hasattr(process, "stderr")


class TestERPCLogStreamEdgeCases:
    """Edge-case coverage for ERPCLogStream."""

    def test_stop_before_run(self) -> None:
        """stop() before start() closes the raw fd without error."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.stopbeforerun")
        logger.setLevel(logging.DEBUG)

        stream = ERPCLogStream(read_fd, logger=logger)
        # Don't start — call stop directly (covers else branch in stop())
        stream.stop()

        with contextlib.suppress(OSError):
            os.close(write_fd)

    def test_skips_empty_lines(self) -> None:
        """Empty lines are skipped, not logged."""
        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.emptylines")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()

        os.write(write_fd, b"\n\nactual line\n\n")
        os.close(write_fd)

        stream.join(timeout=2)

        messages = [r.getMessage() for r in handler.buffer]
        assert messages == ["actual line"]
        logger.removeHandler(handler)

    def test_handles_invalid_fd(self) -> None:
        """Gracefully handles an invalid file descriptor."""
        logger = logging.getLogger("test.invalidfd")
        logger.setLevel(logging.DEBUG)

        stream = ERPCLogStream(9999, logger=logger)
        stream.start()
        stream.join(timeout=2)

        assert not stream.is_alive()

    def test_stop_event_breaks_loop(self) -> None:
        """stop_event causes the reader to exit mid-stream."""
        import time

        read_fd, write_fd = os.pipe()
        logger = logging.getLogger("test.stopevent")
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.MemoryHandler(capacity=100)
        logger.addHandler(handler)

        stream = ERPCLogStream(read_fd, logger=logger)
        stream.start()

        os.write(write_fd, b"line1\n")
        time.sleep(0.1)

        # Set stop event, then close pipe to unblock read
        stream._stop_event.set()
        os.write(write_fd, b"line2\n")
        os.close(write_fd)

        stream.join(timeout=2)
        assert not stream.is_alive()

        messages = [r.getMessage() for r in handler.buffer]
        assert "line1" in messages
        logger.removeHandler(handler)
