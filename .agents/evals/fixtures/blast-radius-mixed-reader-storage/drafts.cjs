function save(store, id, body) {
  store.set('draft:' + id, { body })
}

function load(store, id) {
  const entry = store.get('draft:' + id)
  return entry?.body ?? entry?.text
}

module.exports = { save, load }
