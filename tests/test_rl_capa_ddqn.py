"""Tests for RL-CAPA DDQN primitives."""

from __future__ import annotations

import unittest

import numpy as np
import torch


class RLCAPADDQNTests(unittest.TestCase):
    """Validate replay, networks, and DDQN update behavior."""

    def test_replay_buffer_samples_batched_transitions(self) -> None:
        """The replay buffer should return fixed-size batches of stored transitions."""
        from rl_capa.ddqn.replay_buffer import ReplayBuffer
        from rl_capa.transitions import Transition

        buffer = ReplayBuffer(capacity=8)
        for index in range(4):
            buffer.push(
                Transition(
                    state=np.array([float(index)] * 4, dtype=np.float32),
                    action=index % 2,
                    reward=float(index),
                    next_state=np.array([float(index + 1)] * 4, dtype=np.float32),
                    done=False,
                )
            )

        batch = buffer.sample(batch_size=2)

        self.assertEqual(batch.states.shape, (2, 4))
        self.assertEqual(batch.actions.shape, (2,))
        self.assertEqual(batch.rewards.shape, (2,))

    def test_q_networks_emit_expected_action_dimensions(self) -> None:
        """Batch and parcel Q-networks should match their action-space cardinalities."""
        from rl_capa.ddqn.networks import BatchQNetwork, CrossQNetwork

        batch_network = BatchQNetwork(input_dim=4, action_dim=11)
        cross_network = CrossQNetwork(input_dim=4)

        self.assertEqual(batch_network(torch.zeros(2, 4)).shape, (2, 11))
        self.assertEqual(cross_network(torch.zeros(3, 4)).shape, (3, 2))

    def test_ddqn_agent_train_step_returns_numeric_loss(self) -> None:
        """A DDQN train step should produce a finite scalar loss after enough samples exist."""
        from rl_capa.ddqn.agent import DDQNAgent
        from rl_capa.ddqn.replay_buffer import ReplayBuffer
        from rl_capa.transitions import Transition

        agent = DDQNAgent(
            state_dim=4,
            action_dim=3,
            learning_rate=1e-3,
            discount_factor=0.9,
            epsilon_start=1.0,
            epsilon_end=0.1,
            epsilon_decay_steps=100,
            target_update_interval=10,
        )
        buffer = ReplayBuffer(capacity=32)
        for index in range(8):
            buffer.push(
                Transition(
                    state=np.array([float(index)] * 4, dtype=np.float32),
                    action=index % 3,
                    reward=1.0,
                    next_state=np.array([float(index + 1)] * 4, dtype=np.float32),
                    done=False,
                )
            )

        loss = agent.train_step(buffer=buffer, batch_size=4)

        self.assertIsInstance(loss, float)
        self.assertTrue(np.isfinite(loss))


if __name__ == "__main__":
    unittest.main()
