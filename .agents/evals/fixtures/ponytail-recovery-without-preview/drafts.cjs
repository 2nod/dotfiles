function saveRecovery(state) {
  return { receipt: state.receipt, preview: state.review }
}
function restoreRecovery(raw) {
  return { receipt: raw.receipt, review: raw.preview }
}
function actions(state) {
  if (!state.review) return []
  return state.receipt ? ['retry'] : ['apply']
}
function applyOrRetry(state, hooks) {
  if (!state.review) return
  if (state.receipt) return hooks.record(state.receipt)
  state.receipt = hooks.save(state.review)
  return hooks.record(state.receipt)
}
module.exports = { saveRecovery, restoreRecovery, actions, applyOrRetry }
