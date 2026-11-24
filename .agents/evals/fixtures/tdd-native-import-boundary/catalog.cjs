const renderLabel = require('./label.cjs')

function createCatalog() {
  const calculateStock = (incoming, sold) => incoming - sold
  return new Map([
    ['stock', calculateStock],
    ['inventory', calculateStock],
    ['label', renderLabel],
  ])
}
module.exports = { createCatalog }
