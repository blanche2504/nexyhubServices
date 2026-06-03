#!/bin/sh

set -e

IMAGE_NAME="nexyhub-can"
IMAGE_TAG="0.1.0"
OUTPUT="${IMAGE_NAME}.tar"
PLATFORM="${PLATFORM:-}"

echo "=== Building ${IMAGE_NAME}:${IMAGE_TAG} ==="

if [ -n "$PLATFORM" ]; then
    echo "Platform: ${PLATFORM} (cross-compile)"
    docker buildx build \
        --platform "${PLATFORM}" \
        -f Dockerfile.can \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        --output "type=docker,dest=${OUTPUT}" \
        .
else
    echo "Platform: native"
    docker build \
        -f Dockerfile.can \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        .
    docker save -o "${OUTPUT}" "${IMAGE_NAME}:${IMAGE_TAG}"
fi

echo ""
echo "=== Build complete ==="
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "File:  ${OUTPUT} ($(du -h "${OUTPUT}" | cut -f1))"
echo ""
echo "To upload: use the web interface to load ${OUTPUT}"
echo "To test locally: docker load < ${OUTPUT}"
