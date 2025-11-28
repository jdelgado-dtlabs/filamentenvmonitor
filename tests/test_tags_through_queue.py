#!/usr/bin/env python3
"""Test that tags persist through the data point queue and enqueue/dequeue cycle."""

import os
import sys
import json
import queue
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestTagsThroughQueue(unittest.TestCase):
    """Test that tags survive the queue and serialization/deserialization."""

    def test_tags_survive_queue_cycle(self):
        """Test that tags in a data point survive enqueue and dequeue."""
        # Create a test data point with tags
        data_point = {
            "measurement": "environment",
            "tags": {
                "location": "filamentbox",
                "device": "sensor-1",
                "region": "warehouse",
            },
            "fields": {
                "time": 1234567890,
                "temperature_c": 23.5,
                "temperature_f": 74.3,
                "humidity": 45.2,
            },
        }

        # Put it in a queue
        test_queue = queue.Queue()
        test_queue.put(data_point)

        # Dequeue it
        retrieved_point = test_queue.get()

        # Verify tags are intact
        self.assertIn("tags", retrieved_point, "Tags should survive queue cycle")
        self.assertEqual(
            retrieved_point["tags"],
            data_point["tags"],
            "Tags should be identical after queue round-trip",
        )
        self.assertEqual(retrieved_point["measurement"], "environment")
        self.assertEqual(retrieved_point["fields"]["temperature_c"], 23.5)

    def test_tags_in_batch_serialization(self):
        """Test that tags survive when data point is part of a batch and serialized."""
        # Create multiple data points with tags
        points = [
            {
                "measurement": "environment",
                "tags": {"location": "filamentbox", "device": "sensor-1"},
                "fields": {"temperature_c": 20.0, "humidity": 50.0},
            },
            {
                "measurement": "environment",
                "tags": {"location": "filamentbox", "device": "sensor-2"},
                "fields": {"temperature_c": 21.5, "humidity": 55.0},
            },
        ]

        # Serialize to JSON (as persistence would do)
        batch_json = json.dumps(points)

        # Deserialize (as recovery would do)
        recovered_points = json.loads(batch_json)

        # Verify all tags are intact
        self.assertEqual(len(recovered_points), 2)
        for i, point in enumerate(recovered_points):
            self.assertIn("tags", point, f"Point {i} should have tags after serialization")
            self.assertEqual(
                point["tags"]["location"],
                "filamentbox",
                f"Point {i} location tag should be preserved",
            )
            self.assertIn("device", point["tags"])

    def test_tags_in_batch_list(self):
        """Test that a batch (list) of data points with tags is valid for InfluxDB."""
        # Simulate a batch as it would be passed to influxdb_client.write_points()
        batch = [
            {
                "measurement": "environment",
                "tags": {"location": "filamentbox", "device": "sensor-1"},
                "fields": {"temperature_c": 23.5, "humidity": 45.0, "time": 1234567890},
            },
            {
                "measurement": "environment",
                "tags": {"location": "filamentbox", "device": "sensor-2"},
                "fields": {"temperature_c": 24.0, "humidity": 46.0, "time": 1234567891},
            },
            {
                "measurement": "environment",
                "tags": {"location": "warehouse", "device": "sensor-3"},
                "fields": {"temperature_c": 22.5, "humidity": 44.0, "time": 1234567892},
            },
        ]

        # Verify each point in batch has tags
        for point in batch:
            self.assertIn("tags", point, "Each point in batch should have tags")
            self.assertIn("measurement", point)
            self.assertIn("fields", point)
            # Verify tags are dicts with string keys and values
            for tag_key, tag_value in point["tags"].items():
                self.assertIsInstance(tag_key, str)
                self.assertIsInstance(tag_value, str)

    def test_empty_batch_without_tags(self):
        """Test that data points without tags are still valid."""
        # Data point without tags
        data_point = {
            "measurement": "environment",
            "fields": {
                "temperature_c": 23.5,
                "humidity": 45.0,
                "time": 1234567890,
            },
        }

        # Should be valid
        self.assertNotIn("tags", data_point, "Point without tags should not have tags key")
        self.assertIn("measurement", data_point)
        self.assertIn("fields", data_point)

        # Should serialize/deserialize fine
        json_str = json.dumps(data_point)
        recovered = json.loads(json_str)
        self.assertNotIn("tags", recovered)

    def test_mixed_batch_with_and_without_tags(self):
        """Test that a batch can contain points with and without tags."""
        batch = [
            {
                "measurement": "environment",
                "tags": {"location": "filamentbox"},
                "fields": {"temperature_c": 23.5, "humidity": 45.0},
            },
            {
                "measurement": "environment",
                "fields": {"temperature_c": 24.0, "humidity": 46.0},
            },
            {
                "measurement": "environment",
                "tags": {"location": "warehouse", "device": "sensor-3"},
                "fields": {"temperature_c": 22.5, "humidity": 44.0},
            },
        ]

        # Verify structure
        self.assertIn("tags", batch[0])
        self.assertNotIn("tags", batch[1])
        self.assertIn("tags", batch[2])

        # Serialize and deserialize
        batch_json = json.dumps(batch)
        recovered_batch = json.loads(batch_json)

        # Verify structure is preserved
        self.assertIn("tags", recovered_batch[0])
        self.assertNotIn("tags", recovered_batch[1])
        self.assertIn("tags", recovered_batch[2])
        self.assertEqual(recovered_batch[2]["tags"]["location"], "warehouse")


if __name__ == "__main__":
    unittest.main()
