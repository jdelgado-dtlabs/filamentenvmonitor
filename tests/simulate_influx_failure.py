#!/usr/bin/env python3
"""Simulator to validate influxdb_writer retry/backoff behavior.

This script monkeypatches `filamentbox.InfluxDBClient` with a fake client
that fails a configurable number of times before succeeding. It then
starts the writer thread, enqueues some datapoints, and reports the
attempts and successful writes.
"""

import os
import sys
import time
import threading
import logging
import queue

# Ensure the repository root is on sys.path so we can import filamentbox
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Provide a minimal fake 'influxdb' module so importing `filamentbox` works
# in environments where the real dependency isn't installed.
import types

fake_influx = types.ModuleType("influxdb")


class _DummyClient:
    def __init__(self, *args, **kwargs):
        pass

    def write_points(self, batch):
        return True


fake_influx.InfluxDBClient = _DummyClient
sys.modules["influxdb"] = fake_influx

# Provide minimal fake 'board' and 'adafruit_bme280' modules so hardware
# imports in `filamentbox` don't fail during this simulation.
fake_board = types.ModuleType("board")


class _FakeI2C:
    def __init__(self):
        pass


fake_board.I2C = lambda: _FakeI2C()
sys.modules["board"] = fake_board

fake_ada = types.ModuleType("adafruit_bme280")
basic = types.SimpleNamespace()


class _FakeBME:
    def __init__(self, i2c):
        self.temperature = 25.0
        self.relative_humidity = 40.0
        self.sea_level_pressure = 1013.25


basic.Adafruit_BME280_I2C = _FakeBME
fake_ada.basic = basic
sys.modules["adafruit_bme280"] = fake_ada

from filamentbox.influx_writer import enqueue_data_point, influxdb_writer, WRITE_QUEUE_MAXSIZE
from filamentbox.logging_config import configure_logging
import filamentbox.influx_writer as fb_writer


# For compatibility with test, create a namespace
class _MockFB:
    WRITE_QUEUE_MAXSIZE = WRITE_QUEUE_MAXSIZE
    enqueue_data_point = enqueue_data_point
    BATCH_SIZE = fb_writer.BATCH_SIZE
    FLUSH_INTERVAL = fb_writer.FLUSH_INTERVAL
    influxdb_writer = influxdb_writer
    InfluxDBClient = None


fb = _MockFB()
fb.configure_logging = configure_logging


def run_simulation(failures_before_success=3, run_seconds=8):
    # Enable verbose logging to stdout/stderr
    fb.configure_logging(level=logging.DEBUG)

    # Make writes small and frequent for the simulation
    fb_writer.BATCH_SIZE = 2
    fb_writer.FLUSH_INTERVAL = 1

    # Replace the module-level queue so maxsize changes take effect here
    fb_writer.write_queue = queue.Queue(maxsize=10)

    created_clients = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.attempts = 0
            self.written = []
            self.failures_before_success = failures_before_success
            created_clients.append(self)

        def write_points(self, batch):
            self.attempts += 1
            logging.debug(f"FakeClient.write_points called (attempt {self.attempts})")
            if self.attempts <= self.failures_before_success:
                raise Exception("simulated write failure")
            # On success, record what was written
            self.written.append(list(batch))

    # Monkeypatch
    fb_writer.InfluxDBClient = FakeClient

    stop_event = threading.Event()
    t = threading.Thread(target=fb_writer.influxdb_writer, args=(stop_event,), daemon=True)
    t.start()

    # Enqueue some datapoints quickly
    for i in range(8):
        dp = {"value": i}
        enqueue_data_point(dp)
        time.sleep(0.1)

    # Let the writer run for a while so it experiences failures and eventual success
    start = time.time()
    try:
        while time.time() - start < run_seconds:
            time.sleep(0.5)
    finally:
        stop_event.set()
        # Give writer thread time to exit
        time.sleep(1)

    # Reporting
    if created_clients:
        client = created_clients[0]
        print("FakeClient attempts:", client.attempts)
        print("Successful writes (batches):", len(client.written))
        for idx, b in enumerate(client.written, 1):
            print(f" batch {idx}:", b)
    else:
        print("No FakeClient instance created; writer may not have started.")


if __name__ == "__main__":
    run_simulation(failures_before_success=3, run_seconds=10)
