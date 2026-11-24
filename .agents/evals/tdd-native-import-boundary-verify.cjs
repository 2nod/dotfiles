const assert = require('node:assert/strict')
const { execFileSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const [workspace, fixture] = process.argv.slice(2).map(directory => path.resolve(directory))
assert.equal(fs.readFileSync(path.join(workspace, 'label.cjs'), 'utf8'),
  fs.readFileSync(path.join(fixture, 'label.cjs'), 'utf8'))

function check(script, engine) {
  execFileSync(process.execPath, ['-e', script], {
    cwd: workspace,
    env: { LABEL_ENGINE: engine },
    stdio: 'inherit',
  })
}
check(`
  const assert = require('node:assert/strict')
  assert.deepEqual(require('./report.cjs').totals(9, 4), [5, 5])
`, '')
check(`
  const assert = require('node:assert/strict')
  const catalog = require('./catalog.cjs').createCatalog()
  assert.equal(catalog.get('stock')(8, 3), 5)
  assert.equal(catalog.get('inventory')(5, 3), 2)
  assert.equal(catalog.get('label')('AB'), '[AB]')
`, 'enabled')
