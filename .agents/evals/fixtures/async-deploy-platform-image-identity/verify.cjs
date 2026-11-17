exports.isDeployedImage = (release, index, runtime) =>
  release.indexDigest === runtime.imageDigest
