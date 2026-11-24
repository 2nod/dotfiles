const assert = require('node:assert/strict')
const path = require('node:path')
const { MissingChart, preview } = require(path.resolve(process.argv[2], 'preview.cjs'))

assert.equal(preview(() => 'Current chart', 'stock'), 'Current chart')
assert.equal(preview(title => { throw new MissingChart(title) }, 'stock'), 'Create chart')
assert.throws(() => { throw new MissingChart('stock') }, { name: 'MissingChart', message: 'Missing chart: stock' })
const unrelated = new Error('The chart reader closed unexpectedly')
assert.throws(() => preview(() => { throw unrelated }, 'stock'), error => error === unrelated)
