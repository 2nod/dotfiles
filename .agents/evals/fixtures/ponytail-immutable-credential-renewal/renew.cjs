const renew = async provider => {
  const current = await provider.read()
  const clientId = await provider.registerClient()
  const token = await provider.authorize(clientId)
  await provider.archive(current.id)
  return provider.create({ clientId, token: token.value })
}
module.exports = { renew }
