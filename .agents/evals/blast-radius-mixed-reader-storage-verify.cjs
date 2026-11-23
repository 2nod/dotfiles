const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const workspace = process.argv[2]
const fixture = process.argv[3]
const source = name => path.join(workspace, name)
assert.equal(fs.readFileSync(source('released.cjs'), 'utf8'),
  fs.readFileSync(path.join(fixture, 'released.cjs'), 'utf8'))

const released = require(source('released.cjs'))
const { save, load } = require(source('drafts.cjs'))
const store = new Map([['draft:legacy', { text: 'previous draft' }]])
assert.equal(load(store, 'legacy'), 'previous draft')
save(store, 'current', 'new draft')
assert.equal(load(store, 'current'), 'new draft')
released.open(store)
assert.equal(load(store, 'current'), 'new draft', 'an open released tab deleted the new draft')
assert.equal(load(store, 'legacy'), 'previous draft')
assert.equal(load(store, 'missing'), undefined)
