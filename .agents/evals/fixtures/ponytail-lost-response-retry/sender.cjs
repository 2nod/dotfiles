class Sender {
  constructor(transport) { this.transport = transport; this.draft = ''; }
  async submit(text) {
    this.draft = text;
    try { await this.transport.send(text); this.draft = ''; return true; }
    catch { return false; }
  }
}
module.exports = { Sender };
