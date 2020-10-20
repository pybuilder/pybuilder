#!/bin/bash

set -eu

git clone https://github.com/pyenv/pyenv.git ~/.pyenv || true
git clone https://github.com/pyenv/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv || true
git clone https://github.com/pyenv/pyenv-update.git ~/.pyenv/plugins/pyenv-update || true
echo 'export PYENV_ROOT="$HOME/.pyenv"' >>~/.bash_profile
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >>~/.bash_profile
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >>~/.bash_profile
echo 'eval "$(pyenv virtualenv-init -)"' >>~/.bash_profile

set +eu
source ~/.bash_profile
set -eu

rm -rf ~/.pyenv/versions/pyb-$PYTHON_VERSION || true
rm -rf ~/.pyenv/versions/$PYTHON_VERSION/envs/pyb-$PYTHON_VERSION || true

pyenv update
INSTALL_OPTION="-s"
if [[ "$PYTHON_VERSION" =~ -dev ]]; then
  INSTALL_OPTION="-f"
fi
pyenv install $PYTHON_VERSION $INSTALL_OPTION
pyenv virtualenv $PYTHON_VERSION pyb-$PYTHON_VERSION

set +eu
source ~/.pyenv/versions/pyb-$PYTHON_VERSION/bin/activate
set -eu

pip install -U pip setuptools
python --version
pip --version
