function makeRunner(provider) {
  provider.refresh()
  return command => provider.invoke(command)
}
module.exports = { makeRunner }
