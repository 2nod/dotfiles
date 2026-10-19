// Synthetic ES5-style output from an older JavaScript build target.
function DomainFault(code) {
  const error = Error(code);
  error.name = 'DomainFault';
  error.code = code;
  return error;
}
DomainFault.prototype = Object.create(Error.prototype, {
  constructor: { value: DomainFault },
});
module.exports = { DomainFault };
