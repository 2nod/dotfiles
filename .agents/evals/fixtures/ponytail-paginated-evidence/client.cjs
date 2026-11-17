module.exports = function createClient(pages) {
  return {
    async firstPage() { return pages[0]; },
    async events() {
      const history = [];
      let cursor = 0;
      do {
        const page = pages[cursor];
        history.push(...page.data);
        cursor = page.next;
      } while (cursor !== null);
      return history;
    },
  };
};
