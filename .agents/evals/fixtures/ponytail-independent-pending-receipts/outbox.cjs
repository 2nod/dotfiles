function stage(storage, channel, receipt) {
  storage.set(channel, receipt);
}
function next(storage, channel) {
  return storage.get(channel);
}
function acknowledge(storage, channel, receiptId) {
  storage.delete(channel);
}
function discard(storage, channel) {
  storage.delete(channel);
}
module.exports = { stage, next, acknowledge, discard };
