if (process.env.LABEL_ENGINE !== 'enabled') {
  throw new Error('label engine unavailable')
}

module.exports = function renderLabel(code) {
  return '[' + code + ']'
}
