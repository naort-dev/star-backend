#!/usr/bin/env bash
set -e

docker build -f docker/dockerfiles/starsona-celery --tag ${REGISTRY}starsona-celery${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/starsona-gunicorn --tag ${REGISTRY}starsona-gunicorn${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
id=$(docker create ${REGISTRY}starsona-gunicorn${IMAGE_TAG})
docker cp $id:/starsona/static .
docker build -f docker/dockerfiles/starsona-nginx-${DEPLOYMENT_TYPE:-swarm} --tag ${REGISTRY}starsona-nginx-${DEPLOYMENT_TYPE:-swarm}${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/starsona-migration --tag ${REGISTRY}starsona-migration${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

