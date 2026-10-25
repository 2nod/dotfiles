const { renewSession } = require('./renewal.cjs')
async function recoverViewer(effects) {
  await renewSession(effects)
}
module.exports = { recoverViewer }
