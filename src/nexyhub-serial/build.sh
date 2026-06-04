#!/bin/sh
set -e

IMAGE_NAME="nexyhub-serial"
IMAGE_TAG="1.0"
OUTPUT="${IMAGE_NAME}.tar"
PLATFORM="${PLATFORM:-}"

echo "=== Building ${IMAGE_NAME}:${IMAGE_TAG} ==="

cd "$(dirname "$0")"

if [ -n "$PLATFORM" ]; then
    echo "Platform: ${PLATFORM} (cross-compile)"
    docker buildx build \
        --platform "${PLATFORM}" \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        --output "type=docker,dest=${OUTPUT}" \
        -f Dockerfile \
        ../..
else
    echo "Platform: native"
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" -f Dockerfile ../..
    docker save -o "${OUTPUT}" "${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo ""
echo "=== Build complete ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "File:  ${OUTPUT} ($(du -h "${OUTPUT}" | cut -f1))"
