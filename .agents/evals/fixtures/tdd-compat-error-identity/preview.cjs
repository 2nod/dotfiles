function MissingChart(title) {
  const failure = Error('Missing chart: ' + title)
  failure.name = 'MissingChart'
  return failure
}
MissingChart.prototype = Object.create(Error.prototype)
MissingChart.prototype.constructor = MissingChart

function preview(read, title) {
  try {
    return read(title)
  } catch (failure) {
    if (failure instanceof MissingChart) return 'Create chart'
    throw failure
  }
}

module.exports = { MissingChart, preview }
