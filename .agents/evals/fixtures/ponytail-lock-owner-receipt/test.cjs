const assert = require('node:assert/strict');
const { createRunner } = require('./runner.cjs');

async function main() {
  const receipts = [];
  let accepted;
  const run = createRunner(async receipt => {
    receipts.push(receipt);
    accepted ??= receipt;
  });
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let saves = 0;
  const owner = run(async () => {
    saves += 1;
    await gate;
    return true;
  });
  await run(async () => { saves += 1; return true; });
  release();
  await owner;
  assert.equal(saves, 1, 'the non-owner must not save');
  assert.deepEqual(receipts, [{ saved: true }], 'only the owner reports its result');
  assert.deepEqual(accepted, { saved: true }, 'the first accepted receipt must match the save');

  receipts.length = 0;
  await run(async () => false);
  assert.deepEqual(receipts, [{ saved: false }], 'a real negative save result must still be reported');

  receipts.length = 0;
  await assert.rejects(run(async () => { throw new Error('write failed'); }), /write failed/);
  assert.deepEqual(receipts, [], 'a thrown write has no completed receipt');
  await run(async () => true);
  assert.deepEqual(receipts, [{ saved: true }], 'a thrown write must release the lease');

  const independent = [];
  const other = createRunner(async receipt => independent.push(receipt));
  let releaseAgain;
  const nextGate = new Promise(resolve => { releaseAgain = resolve; });
  const pending = run(async () => { await nextGate; return true; });
  await other(async () => true);
  releaseAgain();
  await pending;
  assert.deepEqual(independent, [{ saved: true }], 'independent runners must not share a lease');
  console.log('Owner-only receipts, negative results, and lease release pass.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
