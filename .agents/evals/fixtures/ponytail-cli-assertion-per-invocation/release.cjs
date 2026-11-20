const { makeRunner } = require('./runner.cjs')
function release(provider) {
  const run = makeRunner(provider)
  try {
    run('inspect')
    run('apply')
    run('verify')
  } finally {
    run('archive')
  }
}
module.exports = { release }
