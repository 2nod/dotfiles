import unittest

from collector import collect_prefix


class SharedRawEngine:
    schema = {
        "step": {"shared": True},
        "market": {"shared": True},
        "player": {"shared": False},
        "private": {"shared": False},
    }

    def __init__(self):
        self.current = 0
        self._refresh()

    def _refresh(self):
        self.state = [
            {"step": self.current, "market": {"price": 7}, "player": 0, "private": "left"},
            {"player": 1, "private": "right"},
        ]

    def step(self):
        self.current += 1
        self._refresh()


class AgentVisibleSharedProjectionTest(unittest.TestCase):
    def test_public_collector_projects_shared_clock_and_preserves_private_state(self):
        engine = SharedRawEngine()
        seen = {0: [], 1: []}

        def controller(observation):
            seen[observation["player"]].append(
                (observation["step"], observation["market"], observation["private"])
            )

        collect_prefix(engine, [controller, controller], steps=2)

        self.assertEqual(
            seen,
            {
                0: [(0, {"price": 7}, "left"), (1, {"price": 7}, "left")],
                1: [(0, {"price": 7}, "right"), (1, {"price": 7}, "right")],
            },
        )


if __name__ == "__main__":
    unittest.main()
