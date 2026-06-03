#!/bin/sh
set -e

IMAGE_NAME="${IMAGE_NAME:-nexyhub-ipc}"
PLATFORM="${PLATFORM:-linux/amd64}"

docker build \
  --platform "${PLATFORM}" \
  -t "${IMAGE_NAME}" \
  -f Dockerfile.ipc \
  .

echo "Image ${IMAGE_NAME} built for ${PLATFORM}"

if [ "${PLATFORM}" = "linux/arm64" ]; then
  OUT="${IMAGE_NAME}.tar"
  docker save -o "${OUT}" "${IMAGE_NAME}"
  echo "Saved to ${OUT}"
fi
