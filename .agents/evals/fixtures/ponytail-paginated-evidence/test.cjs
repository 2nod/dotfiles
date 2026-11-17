const assert = require('node:assert/strict');
const createClient = require('./client.cjs');
const capture = require('./evidence.cjs');
(async () => {
  for (const [old, recent] of [['r-old', 'r-new'], ['alpha', 'omega']]) {
    const pages = [
      { data: [{ type: 'user.message', revision: old }], next: 1 },
      { data: [{ type: 'agent.message', revision: 'irrelevant' }], next: 2 },
      { data: [{ type: 'user.message', revision: recent }], next: null },
    ];
    assert.deepEqual(await capture(createClient(pages), recent), {
      messageRevision: recent, matchesSaved: true,
    });
    assert.deepEqual(await capture(createClient(pages), 'different'), {
      messageRevision: recent, matchesSaved: false,
    });
  }
  assert.deepEqual(await capture(createClient([{data:[],next:null}]), 'absent'), {
    messageRevision: null, matchesSaved: false,
  });
  console.log('complete history evidence verified');
})().catch(e => { console.error(e); process.exitCode = 1; });
