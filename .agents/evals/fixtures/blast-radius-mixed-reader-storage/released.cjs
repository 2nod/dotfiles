function open(store) {
  for (const [key, entry] of store) {
    if (key.startsWith('draft:') && typeof entry.text !== 'string') store.delete(key)
  }
}
module.exports = { open }
