const { DomainFault } = require('./fault.cjs');
function respond(error) {
  if (error instanceof DomainFault) {
    return { status: 409, code: error.code, retryable: false };
  }
  return { status: 500, code: 'INTERNAL', retryable: false };
}
module.exports = { respond };
