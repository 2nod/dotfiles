function validateItems(items) {
  if (!Array.isArray(items) || items.length === 0 || items.some(x => typeof x !== 'string')) throw new Error('Invalid items');
}
function validateBatch(items) {
  validateItems(items);
  if (items.length > 3) throw new Error('Batch exceeds three items');
}
module.exports = { validateItems, validateBatch };
