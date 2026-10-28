class Transport {
  constructor() { this.events = []; this.calls = 0; this.failure = null; this.historyDown = false; }
  async history() { if (this.historyDown) throw Error('History unavailable'); return this.events.map(e => ({ ...e })); }
  async send(text) {
    this.calls++;
    const failure = this.failure; this.failure = null;
    if (failure === 'before') throw Error('Request lost');
    this.events.push({ id: this.events.length + 1, text });
    if (failure === 'after') throw Error('Response lost');
  }
}
module.exports = { Transport };
