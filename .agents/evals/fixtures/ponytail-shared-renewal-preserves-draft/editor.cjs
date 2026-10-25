const { renewSession } = require('./renewal.cjs')
async function recoverEditor(effects) {
  await renewSession(effects)
}
module.exports = { recoverEditor }
