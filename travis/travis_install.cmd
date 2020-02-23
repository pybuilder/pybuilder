choco install -y %PYTHON_PACKAGE% --version=%PYTHON_VERSION%
set PATH=%PYTHON_BIN%;%PYTHON_BIN%\Scripts;%PATH%
pip install virtualenv
python -m virtualenv venv
set PATH=%VENV_DIR%;%PATH%
where python
python --version
