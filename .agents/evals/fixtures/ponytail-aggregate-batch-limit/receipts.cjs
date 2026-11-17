const { validateBatch, validateItems } = require('./rules.cjs');
function complete(batches) {
  batches.forEach(validateBatch);
  const combined = batches.flat();
  validateBatch(combined);
  return JSON.stringify({ items: combined });
}
function restore(raw) {
  const receipt = JSON.parse(raw);
  validateBatch(receipt.items);
  return receipt.items;
}
module.exports = { complete, restore };
