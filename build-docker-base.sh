#!/usr/bin/env bash
set -e

docker build -f docker/dockerfiles/base-os --tag ${REGISTRY}base-os${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/base-nginx --tag ${REGISTRY}base-nginx${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/base-letsencrypt --tag ${REGISTRY}base-letsencrypt${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/base-backend --tag ${REGISTRY}base-backend${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

