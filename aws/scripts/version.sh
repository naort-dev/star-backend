#!/bin/bash
set -e

git config --global user.email "build@starsona.com"
git config --global user.name "Starsona Build"

cd $(mktemp -d)
git clone -n -b $GIT_BRANCH $1 .

major_max=1;
minor_max=0;
patch_max=0;
major_version=${MAJOR_VERSION:-1}
minor_version=${MINOR_VERSION:-0}

commit_id="${CODEBUILD_RESOLVED_SOURCE_VERSION}"
$(git fetch --tags)
last_tag=$(git tag --sort=-version:refname | head -1)

if [[ $last_tag ]]; then
    version=$(echo $last_tag | grep -o '[^-]*$')
    major=$(echo $version | cut -d. -f1)
    minor=$(echo $version | cut -d. -f2)
    patch=$(echo $version | cut -d. -f3)
    if [ "$major_max" -lt "$major" ]; then
        let major_max=$major
    fi
    if [ "$minor_max" -lt "$minor" ]; then
        let minor_max=$minor
    fi
    if [ "$patch_max" -lt "$patch" ]; then
        let patch_max=$patch
    fi
    echo 'Latest version:' $major_max'.'$minor_max'.'$patch_max
    let patch_max=($patch_max+1)
fi
if [ "$major_max" -lt "${major_version}" ] || [ "$minor_max" -lt "${minor_version}" ]; then
    major_max="${major_version}"
    minor_max="${minor_version}"
    patch_max=0
fi
echo 'Switching to new version:' $major_max'.'$minor_max'.'$patch_max
$(git tag -a $major_max.$minor_max.$patch_max $commit_id -m "Version $major_max.$minor_max.$patch_max")
echo 'Push tag to remote'
$(git push origin $major_max.$minor_max.$patch_max)

rm -rf $(pwd)
cd -

echo Writing .version file in current directory
echo $major_max.$minor_max.$patch_max > .version
