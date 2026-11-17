import unittest
from pipe import Pipe

class PublishingTests(unittest.TestCase):
    def test_hidden_before_http_success_never_reopens(self):
        pipe = Pipe()
        pipe.begin_publish()
        pipe.visibility(False)
        self.assertTrue(pipe.open)
        pipe.finish_publish("accepted")
        self.assertEqual((pipe.opens, pipe.closes), (1, 0))
        pipe.receive("working")
        pipe.receive("completed")
        self.assertEqual((pipe.opens, pipe.closes), (1, 1))

    def test_definite_rejection_does_not_leave_response_wait(self):
        pipe = Pipe()
        pipe.begin_publish()
        pipe.visibility(False)
        self.assertTrue(pipe.open)
        pipe.finish_publish("rejected")
        self.assertFalse(pipe.open or pipe.waiting)

    def test_unknown_result_keeps_hidden_pipe_until_live_completion(self):
        pipe = Pipe()
        pipe.begin_publish()
        pipe.visibility(False)
        pipe.finish_publish("unknown")
        self.assertTrue(pipe.open)
        self.assertEqual((pipe.opens, pipe.closes), (1, 0))
        pipe.receive("working")
        pipe.receive("completed")
        self.assertFalse(pipe.open)

    def test_live_completion_before_unknown_result_does_not_restart_wait(self):
        pipe = Pipe()
        pipe.begin_publish()
        pipe.visibility(False)
        pipe.receive("working")
        pipe.receive("completed")
        self.assertTrue(pipe.open)
        pipe.finish_publish("unknown")
        self.assertFalse(pipe.open or pipe.waiting)

    def test_visible_success_and_independent_idle_pipe(self):
        active, idle = Pipe(), Pipe()
        active.begin_publish()
        active.finish_publish("accepted")
        idle.visibility(False)
        self.assertTrue(active.open)
        self.assertFalse(idle.open)
        active.receive("working")
        active.receive("completed")
        self.assertEqual((active.opens, active.closes), (1, 0))

if __name__ == "__main__":
    unittest.main()
