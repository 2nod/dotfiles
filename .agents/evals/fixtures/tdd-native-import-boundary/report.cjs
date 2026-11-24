const { createCatalog } = require('./catalog.cjs')

function totals(incoming, sold) {
  const catalog = createCatalog()
  return [catalog.get('stock')(incoming, sold), catalog.get('inventory')(incoming, sold)]
}
module.exports = { totals }
