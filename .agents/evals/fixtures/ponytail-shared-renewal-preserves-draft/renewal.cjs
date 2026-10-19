async function renewSession(effects) {
  await effects.refreshIdentity()
  effects.reload()
}
module.exports = { renewSession }
