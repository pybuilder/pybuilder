#!/bin/bash

source ~/.bash_profile
pyenv activate pyb-$PYTHON_VERSION

set -eu

DEPLOY_VERSION=""
DEPLOY_BRANCH=""
DEPLOY_OS=""
if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
    echo "Running Production Build"

    for os in $DEPLOY_OSES; do
        if [ "$TRAVIS_OS_NAME" = "$os" ]; then
            DEPLOY_OS=1
            break
        fi
    done

    for v in $DEPLOY_PYTHONS; do
        if [ "$PYTHON_VERSION" = "$v" ]; then
            DEPLOY_VERSION=1
            break
        fi
    done

    for b in $DEPLOY_BRANCHES; do
        if [ "$TRAVIS_BRANCH" = "$b" ]; then
            DEPLOY_BRANCH=1
            break
        fi
    done

    if [ "$DEPLOY_OS$DEPLOY_VERSION$DEPLOY_BRANCH" = "111" ]; then
        echo "This build will be deployed!"
        PYB_ARGS="$PYB_ARGS upload"
    fi
else
    echo "Running PR Build"
fi

./build.py $PYB_ARGS
