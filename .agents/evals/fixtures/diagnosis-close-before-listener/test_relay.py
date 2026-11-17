import asyncio
import unittest

from relay import Connection, Relay


class Lifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_before_authorization_never_opens_upstream(self):
        connection, relay = Connection(), Relay()
        gate = asyncio.get_running_loop().create_future()
        start = asyncio.create_task(relay.start(connection, gate))
        await asyncio.sleep(0)
        connection.disconnect()
        gate.set_result(None)
        await start
        self.assertEqual(relay.opens, 0)

    async def test_disconnect_after_authorization_stops_upstream_once(self):
        connection, relay = Connection(), Relay()
        gate = asyncio.get_running_loop().create_future()
        gate.set_result(None)
        await relay.start(connection, gate)
        connection.disconnect()
        connection.disconnect()
        self.assertEqual((relay.opens, relay.stops, relay.client_disconnects), (1, 1, 1))

    async def test_normal_finish_is_not_a_client_disconnect(self):
        connection, relay = Connection(), Relay()
        gate = asyncio.get_running_loop().create_future()
        gate.set_result(None)
        await relay.start(connection, gate)
        connection.finish()
        self.assertEqual((relay.opens, relay.stops, relay.client_disconnects), (1, 1, 0))

    async def test_closed_connection_does_not_prevent_independent_connection(self):
        closed, live = Connection(), Connection()
        closed.disconnect()
        first, second = Relay(), Relay()
        gate = asyncio.get_running_loop().create_future()
        gate.set_result(None)
        await first.start(closed, gate)
        await second.start(live, gate)
        self.assertEqual((first.opens, second.opens), (0, 1))
        live.disconnect()
        self.assertEqual(second.stops, 1)


if __name__ == '__main__':
    unittest.main()
