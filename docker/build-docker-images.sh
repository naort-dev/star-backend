#!/usr/bin/env bash
set -e
pwd=`pwd`; cd "${0%/*}"

id=$(docker create ${REGISTRY}base-backend${BASE_IMAGE_TAG})
last_requirements=$(mktemp)
docker cp $id:/starsona/requirements.txt $last_requirements
docker rm $id
if cmp -s ../requirements.txt $last_requirements; then
    echo "base-backend image is up to date"
else
    echo "base-backend image is out of date, must rebuld base images"
    exit 1
fi
rm $last_requirements

docker build -f dockerfiles/backend-celery --tag ${REGISTRY}backend-celery${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg BASE_IMAGE_TAG=${BASE_IMAGE_TAG} ..
docker build -f dockerfiles/backend-gunicorn --tag ${REGISTRY}backend-gunicorn${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg BASE_IMAGE_TAG=${BASE_IMAGE_TAG} ..
id=$(docker create ${REGISTRY}backend-gunicorn${IMAGE_TAG})
docker cp $id:/starsona/static ..
docker rm $id
docker build -f dockerfiles/backend-nginx-${DEPLOYMENT_TYPE:-swarm} --tag ${REGISTRY}backend-nginx-${DEPLOYMENT_TYPE:-swarm}${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg BASE_IMAGE_TAG=${BASE_IMAGE_TAG} ..
docker build -f dockerfiles/backend-migration --tag ${REGISTRY}backend-migration${IMAGE_TAG} --build-arg REGISTRY=${REGISTRY} --build-arg BASE_IMAGE_TAG=${BASE_IMAGE_TAG} ..

cd $pwd
