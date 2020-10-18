choco upgrade chocolatey
choco config set --name="'webRequestTimeoutSeconds'" --value="'3600'"
choco config set --name="'commandExecutionTimeoutSeconds'" --value="'14400'"

choco install -y %PYTHON_PACKAGE% --version=%PYTHON_VERSION% --timeout=14400

set PATH=%PYTHON_BIN%;%PYTHON_BIN%\Scripts;%PATH%

pip install virtualenv
python -m virtualenv \venv

set PATH=%VENV_DIR%;%VENV_DIR%\Scripts;%PATH%

where python
python --version
where pip
pip install -U pip setuptools
pip --version
