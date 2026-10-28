const editor = require('./editor.cjs');
const prototype = require('./prototype.cjs');
module.exports = {
  menu: [{ title: 'Editor', path: '/workspace' }, { title: 'Prototype', path: '/workspace/prototype' }],
  open(path) {
    if (path === '/workspace') return editor();
    if (path === '/workspace/prototype') return prototype();
    return '404';
  },
};
