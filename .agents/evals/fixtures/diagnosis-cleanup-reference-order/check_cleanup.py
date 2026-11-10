from itertools import chain, permutations, product
import unittest

from cleanup import cleanup_phases


class CleanupContract(unittest.TestCase):
    def test_scope(self):
        phases = cleanup_phases()
        self.assertTrue(phases)
        self.assertTrue(all(phases))
        self.assertEqual(sorted(chain.from_iterable(phases)), ["delete_backend", "delete_certificate", "detach_certificate", "detach_route"])

    def test_every_parallel_order_preserves_other_resources(self):
        for schedule in product(*(permutations(phase) for phase in cleanup_phases())):
            routes = {"legacy": "retired", "primary": "current", "metrics": "monitor"}
            backends = {"retired", "current", "monitor"}
            assigned = {"retired-cert", "current-cert", "monitor-cert"}
            certificates = set(assigned)
            for action in chain.from_iterable(schedule):
                if action == "detach_route":
                    del routes["legacy"]
                elif action == "delete_backend":
                    if "retired" in routes.values():
                        raise RuntimeError("backend still referenced by route")
                    backends.remove("retired")
                elif action == "detach_certificate":
                    assigned.remove("retired-cert")
                elif action == "delete_certificate":
                    if "retired-cert" in assigned:
                        raise RuntimeError("certificate still assigned to proxy")
                    certificates.remove("retired-cert")
                else:
                    self.fail("unknown cleanup operation")
            self.assertEqual(routes, {"primary": "current", "metrics": "monitor"})
            self.assertEqual(backends, {"current", "monitor"})
            self.assertEqual(assigned, {"current-cert", "monitor-cert"})
            self.assertEqual(certificates, assigned)


if __name__ == "__main__":
    unittest.main()
