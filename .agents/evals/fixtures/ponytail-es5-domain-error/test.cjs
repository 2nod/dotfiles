const assert = require('node:assert/strict');
const { DomainFault } = require('./fault.cjs');
const { respond } = require('./adapter.cjs');
const fault = new DomainFault('VERSION_MISMATCH');
assert.ok(fault instanceof DomainFault);
assert.ok(fault instanceof Error);
assert.equal(fault.name, 'DomainFault');
assert.equal(fault.message, 'VERSION_MISMATCH');
assert.deepEqual(respond(fault), {
  status: 409, code: 'VERSION_MISMATCH', retryable: false,
});
assert.deepEqual(respond(new Error('Unexpected failure')), {
  status: 500, code: 'INTERNAL', retryable: false,
});
