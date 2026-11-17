const assert = require('node:assert/strict')
const { isDeployedImage } = require('./verify.cjs')
const digest = character => 'sha256:' + character.repeat(64)
const release = { indexDigest: digest('a') }
const index = {
  digest: digest('a'),
  mediaType: 'application/vnd.oci.image.index.v1+json',
  manifests: [
    { digest: digest('b'), platform: { os: 'linux', architecture: 'amd64' } },
    { digest: digest('c'), platform: { os: 'linux', architecture: 'arm64' } },
    { digest: digest('d'), platform: { os: 'unknown', architecture: 'unknown' } },
  ],
}
const amd64 = { os: 'linux', architecture: 'amd64' }
const arm64 = { os: 'linux', architecture: 'arm64' }
const cases = [
  ['the amd64 child of the release index is accepted', release, index, { imageDigest: digest('b'), platform: amd64 }, true],
  ['the arm64 child is accepted for an arm64 runtime', release, index, { imageDigest: digest('c'), platform: arm64 }, true],
  ['an arm64 child is rejected for an amd64 runtime', release, index, { imageDigest: digest('c'), platform: amd64 }, false],
  ['an unrelated image digest is rejected', release, index, { imageDigest: digest('e'), platform: amd64 }, false],
  ['the index digest is rejected as a concrete runtime image', release, index, { imageDigest: digest('a'), platform: amd64 }, false],
  ['a different release index is rejected', { indexDigest: digest('f') }, index, { imageDigest: digest('b'), platform: amd64 }, false],
]
for (const [name, expectedRelease, manifest, runtime, expected] of cases)
  assert.equal(isDeployedImage(expectedRelease, manifest, runtime), expected, name)
console.log('6 artifact identity checks passed')
