const assert = require('node:assert/strict');
const { stage, next, acknowledge, discard } = require('./outbox.cjs');
const a = { id: 'alpha', revision: 'saved-alpha' };
const b = { id: 'beta', revision: 'saved-beta' };
{
  const storage = new Map();
  stage(storage, 'one', a);
  stage(storage, 'one', b);
  const recovered = [];
  for (let i = 0; i < 3; i++) {
    const receipt = next(storage, 'one');
    if (!receipt) break;
    recovered.push(receipt);
    acknowledge(storage, 'one', receipt.id);
  }
  assert.deepEqual(recovered.sort((x,y) => x.id.localeCompare(y.id)), [a,b]);
}
{
  const storage = new Map();
  stage(storage, 'one', a);
  acknowledge(storage, 'one', a.id);
  stage(storage, 'one', b);
  acknowledge(storage, 'one', a.id);
  assert.deepEqual(next(storage, 'one'), b, 'a late success must not erase another receipt');
}
{
  const storage = new Map();
  stage(storage, 'one', a);
  stage(storage, 'one', b);
  stage(storage, 'another', a);
  discard(storage, 'one');
  assert.equal(next(storage, 'one'), undefined);
  assert.deepEqual(next(storage, 'another'), a);
}
console.log('independent pending receipts pass');
