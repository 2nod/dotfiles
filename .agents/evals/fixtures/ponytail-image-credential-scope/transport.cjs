function makeDownload() {
  const calls = []
  async function download(url, options) {
    calls.push({ url, credentials: options.credentials })
    const signed = new URL(url).hostname === 'object-store.test'
    if (signed && options.credentials !== 'omit') throw new Error('credentialed CORS blocked')
    if (!signed && options.credentials !== 'include') throw new Error('CDN access denied')
    return Buffer.from('fixture-image')
  }
  return { download, calls }
}
module.exports = { makeDownload }
