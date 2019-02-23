#!/bin/bash
set -e

if [[ -z "${GIT_BRANCH}" ]]; then
    echo "Must provide GIT_BRANCH in environment" 1>&2
    exit 1
fi

if [[ -z "${VERSION}" ]]; then
    echo "Must provide VERSION in environment" 1>&2
    exit 1
fi

if [[ -z "${CODEBUILD_RESOLVED_SOURCE_VERSION}" ]]; then
    echo "Must provide CODEBUILD_RESOLVED_SOURCE_VERSION in environment" 1>&2
    exit 1
fi

git config --global user.email "build@starsona.com"
git config --global user.name "Starsona Build"

cd $(mktemp -d)
git clone -n -b ${GIT_BRANCH} $1 .

commit_id="${CODEBUILD_RESOLVED_SOURCE_VERSION}"
$(git fetch --tags)

last_tag=$(git tag --sort=-version:refname | grep -m1 "^${VERSION//./\\.}\\." || true)
[[ -z "${last_tag}" ]] && last_tag=${VERSION}.0

version=$(echo ${last_tag} | grep -o '[^-]*$')
major=$(echo ${version} | cut -d. -f1)
minor=$(echo ${version} | cut -d. -f2)
patch=$(echo ${version} | cut -d. -f3)
echo "Latest version: ${major}.${minor}.${patch}"
let patch=$patch+1

echo "Switching ${GIT_BRANCH} to new version: ${major}.${minor}.${patch}"
$(git tag -a ${major}.${minor}.${patch} ${commit_id} -m "Version ${major}.${minor}.${patch}")
echo "Push new tag to remote"
$(git push origin ${major}.${minor}.${patch})

rm -rf $(pwd)
cd -

echo Writing .version file in current directory
echo ${major}.${minor}.${patch} > .version
