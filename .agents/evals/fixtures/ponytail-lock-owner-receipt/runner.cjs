function createRunner(publish) {
  let busy = false;
  async function withLease(save) {
    if (busy) return false;
    busy = true;
    try {
      return await save();
    } finally {
      busy = false;
    }
  }
  return async function run(save) {
    const saved = await withLease(save);
    await publish({ saved });
  };
}
module.exports = { createRunner };
