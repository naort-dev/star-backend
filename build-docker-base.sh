#!/usr/bin/env bash
set -e

docker build -f docker/dockerfiles/base-os --tag ${REGISTRY}starsona-base-os${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
#docker build -f docker/dockerfiles/base-httpd --tag ${REGISTRY}starsona-base-httpd${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/base-nginx --tag ${REGISTRY}starsona-base-nginx${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/base-backend --tag ${REGISTRY}starsona-base-backend${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

