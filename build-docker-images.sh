#!/usr/bin/env bash
set -e

docker build -f docker/dockerfiles/backend-celery --tag ${REGISTRY}backend-celery${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/backend-gunicorn --tag ${REGISTRY}backend-gunicorn${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
id=$(docker create ${REGISTRY}backend-gunicorn${IMAGE_TAG})
docker cp $id:/starsona/static .
docker build -f docker/dockerfiles/backend-nginx-${DEPLOYMENT_TYPE:-swarm} --tag ${REGISTRY}backend-nginx-${DEPLOYMENT_TYPE:-swarm}${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/backend-migration --tag ${REGISTRY}backend-migration${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

