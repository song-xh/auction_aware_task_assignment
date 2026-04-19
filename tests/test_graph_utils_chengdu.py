"""Regression tests for the Chengdu graph loader."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DFS_PATTERN = re.compile(r"After DFS nodeNumber:\s*(?P<nodes>\d+)\s*\|\s*edgeNumber:(?P<edges>\d+)")


def import_graph_with_hash_seed(seed: int) -> tuple[int, int]:
    """Import ``GraphUtils_ChengDu`` in a fresh interpreter and return retained graph sizes."""

    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(seed)
    completed = subprocess.run(
        [sys.executable, "-c", "import GraphUtils_ChengDu"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    match = DFS_PATTERN.search(completed.stdout)
    if match is None:
        raise AssertionError(f"missing DFS summary in output:\n{completed.stdout}")
    return int(match.group("nodes")), int(match.group("edges"))


class GraphUtilsChengduDeterminismTest(unittest.TestCase):
    """Verify the Chengdu graph loader always keeps the same main component."""

    def test_import_keeps_same_large_component_across_hash_seeds(self) -> None:
        """Fresh imports with different hash seeds should retain one stable large component."""

        observed = [import_graph_with_hash_seed(seed) for seed in range(1, 7)]
        self.assertEqual(
            len(set(observed)),
            1,
            f"graph import retained inconsistent components across hash seeds: {observed}",
        )
        node_count, edge_count = observed[0]
        self.assertGreater(node_count, 10000, observed)
        self.assertGreater(edge_count, 10000, observed)

    def test_select_largest_connected_component_prefers_biggest_then_smallest_root(self) -> None:
        """Synthetic graphs should pick the largest component with a stable tie-breaker."""

        from GraphUtils_ChengDu import EdgeModel, GraphUtils, NodeModel

        def build_node(node_id: str, neighbors: list[str]) -> NodeModel:
            node = NodeModel()
            node.nodeId = node_id
            node.neighbors = list(neighbors)
            node.nEdge = {}
            node.lat = "0.0"
            node.lng = "0.0"
            return node

        def connect(edge_id: str, start: NodeModel, end: NodeModel) -> EdgeModel:
            edge = EdgeModel()
            edge.edgeId = edge_id
            edge.startNode = start
            edge.endNode = end
            edge.nodeList = [start.nodeId, end.nodeId]
            start.nEdge[end.nodeId] = edge_id
            end.nEdge[start.nodeId] = edge_id
            return edge

        n1 = build_node("1", ["2"])
        n2 = build_node("2", ["1"])
        n3 = build_node("3", ["4", "5"])
        n4 = build_node("4", ["3", "5"])
        n5 = build_node("5", ["3", "4"])
        n6 = build_node("6", ["7"])
        n7 = build_node("7", ["6"])
        n8 = build_node("8", ["9"])
        n9 = build_node("9", ["8"])

        n_map = {node.nodeId: node for node in (n1, n2, n3, n4, n5, n6, n7, n8, n9)}
        e12 = connect("e12", n1, n2)
        e34 = connect("e34", n3, n4)
        e35 = connect("e35", n3, n5)
        e45 = connect("e45", n4, n5)
        e67 = connect("e67", n6, n7)
        e89 = connect("e89", n8, n9)
        e_map = {edge.edgeId: edge for edge in (e12, e34, e35, e45, e67, e89)}

        graph_utils = GraphUtils()
        component_nodes, component_edges, root = graph_utils.select_largest_connected_component(n_map, e_map)

        self.assertEqual(root.nodeId, "3")
        self.assertEqual({node.nodeId for node in component_nodes}, {"3", "4", "5"})
        self.assertEqual({edge.edgeId for edge in component_edges}, {"e34", "e35", "e45"})


if __name__ == "__main__":
    unittest.main()
