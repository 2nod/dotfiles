const assert = require('node:assert/strict')
function makeProvider({ failAt = null, failCommand = null } = {}) {
  let generation = 0
  let stored
  const calls = []
  return {
    calls,
    refresh() {
      generation++
      calls.push('refresh')
      if (generation === failAt) throw new Error('identity unavailable')
      stored = { value: 'synthetic-' + generation, used: false }
    },
    invoke(command) {
      assert.ok(stored && !stored.used, 'each CLI process needs an unused assertion')
      stored.used = true
      calls.push(command)
      if (command === failCommand) throw new Error('command failed')
      return command
    },
  }
}
module.exports = { makeProvider }
