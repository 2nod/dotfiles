const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const { mount } = require('./panel.cjs')
const { finish } = require('./authorization.cjs')

async function main() {
  const host = new EventEmitter()
  let connected = false
  let closed = false
  const sent = []
  const panel = mount(host, async () => connected, 'https://identity.example')
  await panel.refresh()
  assert.equal(panel.state.connected, false)
  connected = true
  finish({
    opener: {
      postMessage(data, targetOrigin) {
        sent.push({ data, targetOrigin })
        if (targetOrigin === '*' || targetOrigin === 'https://desk.example')
          host.emit('message', { origin: 'https://identity.example', data })
      },
    },
    close() { closed = true },
  })
  // The embedded host sends no focus or visibility event after closing the tab.
  for (let n = 0; n < 8; n += 1) await Promise.resolve()
  assert.equal(closed, true)
  assert.equal(panel.state.connected, true, 'Link completion must refresh without a focus event')
  assert.equal(panel.state.checks, 2)
  assert.ok(sent.length > 0)
  assert.ok(sent.every(item => item.data === 'account-link-finished'), 'Notify only; do not forward authorization data')
  connected = false
  host.emit('message', { origin: 'https://identity.example.attacker.invalid', data: 'account-link-finished' })
  host.emit('message', { origin: 'https://identity.example', data: 'unrelated' })
  for (let n = 0; n < 8; n += 1) await Promise.resolve()
  assert.equal(panel.state.checks, 2, 'Untrusted or unrelated events must be ignored')
  assert.equal(panel.state.connected, true)
  host.emit('focus')
  for (let n = 0; n < 8; n += 1) await Promise.resolve()
  assert.equal(panel.state.checks, 3)
  assert.equal(panel.state.connected, false)
  console.log('PASS completion refreshes without focus; invalid notifications are ignored')
}
main().catch(error => { console.error(error.message); process.exitCode = 1 })
