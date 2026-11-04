const assert = require('node:assert/strict')
const { readAsset } = require('./asset-reader.cjs')
const { makeDownload } = require('./transport.cjs')

async function main() {
  for (const kind of ['original', 'rendered', 'text-free']) {
    const transport = makeDownload()
    const image = await readAsset(kind, transport.download)
    assert.equal(image.toString(), 'fixture-image')
    assert.equal(transport.calls.length, 1)
    assert.equal(transport.calls[0].credentials, kind === 'original' ? 'include' : 'omit')
  }
  const failure = new Error('download unavailable')
  for (const kind of ['original', 'rendered']) {
    await assert.rejects(readAsset(kind, async () => { throw failure }), error => error === failure)
  }
  console.log('Authenticated artwork and signed image credential policies passed')
}
main().catch(error => { console.error(error.message); process.exitCode = 1 })
