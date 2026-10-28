const makeProvider = ({ failUpdate = false } = {}) => {
  let stored = { id: 'credential-one', clientId: 'existing-client', token: 'old-token' }
  const calls = []
  return {
    calls,
    read: async () => ({ ...stored }),
    registerClient: async () => { calls.push('register'); return 'replacement-client' },
    authorize: async clientId => ({ clientId, value: 'renewed-token' }),
    archive: async () => { calls.push('archive'); stored = null },
    create: async credential => {
      calls.push('create')
      if (failUpdate) throw new Error('upstream unavailable')
      stored = { id: 'replacement', ...credential }
      return stored
    },
    update: async (id, { token }) => {
      calls.push('update')
      if (failUpdate) throw new Error('upstream unavailable')
      if (id !== stored.id || token.clientId !== stored.clientId) throw new Error('immutable client mismatch')
      stored = { ...stored, token: token.value }
      return stored
    },
    snapshot: () => stored === null ? null : { ...stored },
  }
}
module.exports = { makeProvider }
