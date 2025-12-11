import os
import sys
import time
import threading
import queue
import types

# Ensure project root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Inject lightweight fake modules for dependencies that may not be
# installed in the test environment so we can import `filamentbox`.
fake_influx = types.ModuleType("influxdb")


class _DummyClient:
    def __init__(self, *a, **k):
        pass

    def write_points(self, batch):
        return True


fake_influx.InfluxDBClient = _DummyClient
sys.modules["influxdb"] = fake_influx

fake_board = types.ModuleType("board")


class _FakeI2C:
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

import filamentbox.influx_writer as fb_writer


def test_influx_writer_alert_and_persist(tmp_path):
    # Configure test parameters
    fb_writer.BATCH_SIZE = 2
    fb_writer.FLUSH_INTERVAL = 0.2
    fb_writer.write_queue = queue.Queue(maxsize=20)

    # Point persistence to a temp file
    # tmp_path may be a pathlib.Path (pytest) or a str (direct run)
    if isinstance(tmp_path, str):
        db_path = os.path.join(tmp_path, "test.db")
    else:
        db_path = str(tmp_path / "test.db")
    import filamentbox.persistence as fb_persist

    fb_persist.DB_PATH = db_path
    if os.path.exists(db_path):
        os.remove(db_path)

    # Prepare a fake client that fails N times
    failures = 2
    created = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.attempts = 0
            self.written = []
            created.append(self)

        def write_points(self, batch):
            self.attempts += 1
            if self.attempts <= failures:
                raise Exception("simulated failure")
            self.written.append(list(batch))

    fb_writer.InfluxDBClient = FakeClient

    # register an alert handler to capture alert calls
    alerts = []

    def handler(payload):
        alerts.append(payload)

    fb_writer.register_alert_handler(handler)

    # Lower threshold so test triggers quickly
    fb_writer.ALERT_FAILURE_THRESHOLD = 1

    stop_event = threading.Event()
    t = threading.Thread(target=fb_writer.influxdb_writer, args=(stop_event,), daemon=True)
    t.start()

    # Enqueue some datapoints
    for i in range(5):
        fb_writer.enqueue_data_point({"i": i})

    # Let writer run briefly
    time.sleep(2)

    # Stop and wait
    stop_event.set()
    time.sleep(0.5)

    # Assertions
    assert created, "FakeClient was not created"
    client = created[0]
    assert client.attempts >= 1
    assert alerts, "Alert handler was not called"
    # Check that persisted db exists and contains at least one batch
    assert os.path.exists(db_path), f"Persistence db not found at {db_path}"
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM unsent_batches")
        count = cursor.fetchone()[0]
        conn.close()
        assert count > 0, "No persisted batches found in database"
    except sqlite3.OperationalError:
        raise AssertionError("Persistence database table not created or accessible")


if __name__ == "__main__":
    # Run test directly if pytest isn't available
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        try:
            test_influx_writer_alert_and_persist(tmp_path=td)
            print("Test passed")
        except AssertionError as e:
            print("Test failed:", e)
            raise
