exports.mount = (host, readState, trustedOrigin) => {
  const state = { connected: false, checks: 0 }
  const refresh = async () => {
    state.checks += 1
    state.connected = await readState()
  }
  host.on('focus', refresh)
  return { state, refresh }
}
