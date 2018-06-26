#!/usr/bin/env bash
set -e

id=$(docker create ${REGISTRY}base-backend${IMAGE_TAG})
docker cp $id:/starsona/requirements.txt last-requirements.txt
docker rm $id
if cmp -s requirements.txt last-requirements.txt; then
    echo "base-backend image is up to date"
else
    echo "base-backend image is out of date, rebulding"
    docker build -f docker/dockerfiles/base-backend --tag ${REGISTRY}base-backend${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
fi
rm last-requirements.txt

docker build -f docker/dockerfiles/backend-celery --tag ${REGISTRY}backend-celery${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/backend-gunicorn --tag ${REGISTRY}backend-gunicorn${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
id=$(docker create ${REGISTRY}backend-gunicorn${IMAGE_TAG})
docker cp $id:/starsona/static .
docker rm $id
docker build -f docker/dockerfiles/backend-nginx-${DEPLOYMENT_TYPE:-swarm} --tag ${REGISTRY}backend-nginx-${DEPLOYMENT_TYPE:-swarm}${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/backend-migration --tag ${REGISTRY}backend-migration${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .
docker build -f docker/dockerfiles/backend-console --tag ${REGISTRY}backend-console${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg IMAGE_TAG=${IMAGE_TAG} .

