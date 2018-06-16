#!/usr/bin/env bash
set -e

docker build -f docker/dockerfiles/starsona-celery --tag ${REGISTRY}starsona-celery${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/starsona-gunicorn --tag ${REGISTRY}starsona-gunicorn${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
id=$(docker create ${REGISTRY}starsona-gunicorn${IMAGE_TAG})
docker cp $id:/starsona/static .
#docker build -f docker/dockerfiles/starsona-httpd --tag ${REGISTRY}starsona-httpd${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} --build-arg DEPLOYMENT_TYPE=${DEPLOYMENT_TYPE:-swarm} .
docker build -f docker/dockerfiles/starsona-nginx --tag ${REGISTRY}starsona-nginx${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} --build-arg DEPLOYMENT_TYPE=${DEPLOYMENT_TYPE:-aws} .
docker build -f docker/dockerfiles/starsona-migration --tag ${REGISTRY}starsona-migration${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

