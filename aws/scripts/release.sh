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

cwd=$(pwd)
cd $(mktemp -d)
git clone -n -b ${GIT_BRANCH} $1 .
git fetch --tags

last_tag=$(git tag --sort=-version:refname | grep -m1 "^${VERSION//./\\.}\\." || true)
commit_id=$(git rev-list -n 1 ${last_tag})
echo "Latest commit: ${commit_id}"
echo "Codebuild commit: ${CODEBUILD_RESOLVED_SOURCE_VERSION}"
if [[ "${commit_id}" != "${CODEBUILD_RESOLVED_SOURCE_VERSION}" ]]; then
    echo "Not the latest build, exiting"
    exit 1
fi

version=$(echo ${last_tag} | grep -o '[^-]*$')
major=$(echo ${version} | cut -d. -f1)
minor=$(echo ${version} | cut -d. -f2)
patch=$(echo ${version} | cut -d. -f3)
release=${major}.${minor}

echo "Latest version on ${GIT_BRANCH}: ${major}.${minor}.${patch}"
echo "Create hotfix branch: ${release} off ${major}.${minor}.${patch}"
git checkout -b ${release} "${major}.${minor}.${patch}"

echo "Push hotfix branch ${release} to remote"
git push origin ${release}

echo "Checkout ${GIT_BRANCH}"
git checkout ${GIT_BRANCH}

let minor=$minor+1
patch=0

echo "Switching ${GIT_BRANCH} to new version: ${major}.${minor}.${patch}"
git tag -a ${major}.${minor}.${patch} -m "Version ${major}.${minor}.${patch}"

echo "Push new tag to remote"
git push
git push origin ${major}.${minor}.${patch}

rm -rf $(pwd)
cd -

echo "Writing artifacts file in current directory"
echo "${major}.${minor}" > .codepipeline
echo "${release}" > .hotfix
