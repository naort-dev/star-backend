#!/usr/bin/env bash

docker build -f docker/dockerfiles/base-os . --tag ${REGISTRY}starsona-base-os${IMAGE_TAG}
docker build -f docker/dockerfiles/base-httpd . --tag ${REGISTRY}starsona-base-httpd${IMAGE_TAG}
docker build -f docker/dockerfiles/base-backend . --tag ${REGISTRY}starsona-base-backend${IMAGE_TAG}

