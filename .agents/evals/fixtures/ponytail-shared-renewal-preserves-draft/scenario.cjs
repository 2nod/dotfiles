const assert = require('node:assert/strict')
const { recoverEditor } = require('./editor.cjs')
const { recoverViewer } = require('./viewer.cjs')
const { renewSession } = require('./renewal.cjs')
function createEffects(options = {}) {
  const state = { draft: 'unsaved local sentence', identity: false, account: false, reloads: 0, saves: 0, order: [] }
  const effects = {
    async refreshIdentity() {
      state.order.push('identity')
      if (options.identityFails) throw new Error('identity unavailable')
      state.identity = true
    },
    async refreshVisibleAccount() {
      assert.equal(state.identity, true)
      state.order.push('account')
      if (options.accountFails) throw new Error('account unavailable')
      state.account = true
    },
    reload() { state.order.push('reload'); state.reloads++; state.draft = '' },
    save() { state.saves++ },
  }
  return { state, effects }
}
async function main() {
  const editor = createEffects()
  await recoverEditor(editor.effects)
  assert.equal(editor.state.draft, 'unsaved local sentence', 'editor renewal must preserve the draft')
  assert.deepEqual(editor.state.order, ['identity', 'account'])
  assert.equal(editor.state.account, true)
  assert.equal(editor.state.reloads, 0)
  assert.equal(editor.state.saves, 0, 'renewal must not implicitly replay saves')
  for (const recover of [recoverViewer, renewSession]) {
    const viewer = createEffects()
    await recover(viewer.effects)
    assert.deepEqual(viewer.state.order, ['identity', 'reload'], 'existing default consumers must still reload')
    assert.equal(viewer.state.reloads, 1)
  }
  const rejectedIdentity = createEffects({ identityFails: true })
  await assert.rejects(recoverEditor(rejectedIdentity.effects), /identity unavailable/)
  assert.deepEqual(rejectedIdentity.state.order, ['identity'])
  assert.equal(rejectedIdentity.state.draft, 'unsaved local sentence')
  const rejectedAccount = createEffects({ accountFails: true })
  await assert.rejects(recoverEditor(rejectedAccount.effects), /account unavailable/)
  assert.equal(rejectedAccount.state.draft, 'unsaved local sentence')
  assert.equal(rejectedAccount.state.reloads, 0)
  assert.equal(rejectedAccount.state.saves, 0)
  console.log('renewal behavior passed')
}
main().catch(error => { console.error(error); process.exitCode = 1 })
