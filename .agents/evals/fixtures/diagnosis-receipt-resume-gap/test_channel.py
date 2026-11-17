import unittest
from channel import Channel

class ChannelTests(unittest.TestCase):
    def test_receipt_before_resume_and_publish_callback_keeps_hidden_connection(self):
        channel = Channel()
        channel.accept_message()
        channel.receive("running")
        channel.set_visible(False)
        channel.receive("action_required")
        channel.receive("receipt")
        self.assertTrue(channel.connected)
        self.assertEqual((channel.opens, channel.closes), (1, 0))
        channel.receive("running")
        self.assertEqual((channel.opens, channel.closes), (1, 0))
        channel.receive("complete")
        self.assertFalse(channel.connected)
        self.assertEqual(channel.closes, 1)
        channel.set_visible(True)
        self.assertEqual(channel.opens, 2)

    def test_visible_receipt_never_reopens_connection(self):
        channel = Channel()
        channel.accept_message()
        channel.receive("action_required")
        channel.receive("receipt")
        channel.receive("running")
        channel.receive("complete")
        self.assertEqual((channel.opens, channel.closes), (1, 0))
        channel.set_visible(False)
        self.assertFalse(channel.connected)

    def test_unknown_or_replayed_receipt_does_not_start_work(self):
        channel = Channel()
        channel.receive("receipt")
        channel.set_visible(False)
        self.assertFalse(channel.connected)
        channel.set_visible(True)
        channel.accept_message()
        channel.receive("action_required")
        channel.receive("receipt")
        channel.receive("complete")
        channel.receive("receipt")
        channel.set_visible(False)
        self.assertFalse(channel.connected)

    def test_sending_while_hidden_keeps_connection_and_channels_are_independent(self):
        active, idle = Channel(), Channel()
        active.accept_message()
        active.set_visible(False)
        idle.set_visible(False)
        self.assertTrue(active.connected)
        self.assertFalse(idle.connected)

if __name__ == "__main__":
    unittest.main()
