"""Unit tests for Chengdu task parsing helpers."""

import unittest

from Tasks_ChengDu import parse_task_line


class TaskParseTests(unittest.TestCase):
    """Validate the scalar parsing logic used for Chengdu task loading."""

    def test_parse_task_line_rounds_weight_and_fare_to_two_decimals(self) -> None:
        """Task parsing should preserve the legacy two-decimal rounding semantics without NumPy scalars."""
        task = parse_task_line("1,104.0,30.0,42,10,20,1.234,9.876")

        self.assertEqual(task.num, "1")
        self.assertEqual(task.weight, 1.23)
        self.assertEqual(task.fare, 9.88)


if __name__ == "__main__":
    unittest.main()
