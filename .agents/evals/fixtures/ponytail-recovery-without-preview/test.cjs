const assert = require('node:assert/strict')
const {saveRecovery, restoreRecovery, actions, applyOrRetry} = require('./drafts.cjs')
const receipt = {id: 'receipt-7', version: 'version-2', refs: ['item-3']}
const review = {items: [{text: 'A private draft that must not be copied.'}]}
const tests = [
  ['storage contains only the receipt', () => {
    assert.deepEqual(saveRecovery({review, receipt}), {receipt})
  }],
  ['restoration needs no preview', () => {
    const state = restoreRecovery(JSON.parse(JSON.stringify({receipt})))
    assert.deepEqual(state.receipt, receipt)
    assert.deepEqual(actions(state), ['retry'])
  }],
  ['a restored receipt records exactly once and never saves again', () => {
    let saves = 0, records = 0
    const state = restoreRecovery({receipt})
    applyOrRetry(state, {save: () => {saves++; return receipt}, record: value => {records++; assert.deepEqual(value, receipt)}})
    assert.equal(saves, 0)
    assert.equal(records, 1)
  }],
  ['a fresh review still saves and records once', () => {
    let saves = 0, records = 0
    const state = {review}
    assert.deepEqual(actions(state), ['apply'])
    applyOrRetry(state, {save: value => {saves++; assert.deepEqual(value, review); return receipt}, record: value => {records++; assert.deepEqual(value, receipt)}})
    assert.equal(saves, 1)
    assert.equal(records, 1)
    assert.deepEqual(state.receipt, receipt)
  }],
  ['a record failure keeps the receipt, and a reload retries recording only', () => {
    let saves = 0, records = 0
    const state = {review}
    assert.throws(() => applyOrRetry(state, {save: () => {saves++; return receipt}, record: () => {records++; throw new Error('record failed')}}), /record failed/)
    const restored = restoreRecovery(JSON.parse(JSON.stringify(saveRecovery(state))))
    assert.deepEqual(actions(restored), ['retry'])
    applyOrRetry(restored, {save: () => {throw new Error('duplicate save')}, record: value => {records++; assert.deepEqual(value, receipt)}})
    assert.equal(saves, 1)
    assert.equal(records, 2)
  }],
  ['no review and no receipt has no action or write', () => {
    const state = {}
    assert.deepEqual(actions(state), [])
    applyOrRetry(state, {save: () => {throw new Error('unexpected save')}, record: () => {throw new Error('unexpected record')}})
  }],
]
let failures = 0
for (const [name, test] of tests) {
  try {test(); console.log('PASS ' + name)}
  catch (error) {failures++; console.error('FAIL ' + name + ': ' + error.message)}
}
process.exitCode = failures === 0 ? 0 : 1
