async function readAsset(kind, download) {
  const url = kind === 'original'
    ? 'https://artwork.test/page.jpg'
    : 'https://object-store.test/page.jpg?signature=fixture'
  return download(url, { credentials: 'include' })
}
module.exports = { readAsset }
