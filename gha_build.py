import os
import subprocess
import sys
from os.path import join as jp, dirname, abspath, normcase as nc, expanduser

if __name__ == "__main__":
    environ = os.environ
    os_name = environ["RUNNER_OS"]

    pyb_args = environ["PYB_ARGS"].split()
    deploy_oses = environ["DEPLOY_OSES"].split()
    deploy_pythons = environ["DEPLOY_PYTHONS"].split()
    deploy_branches = environ["DEPLOY_BRANCHES"].split()

    is_production = environ["GITHUB_EVENT_NAME"] != "pull_request"
    if is_production:
        print("Running Production build!")
        if (os_name in deploy_oses and
                environ["WITH_VENV"] == "true" and
                environ["PYTHON_VERSION"] in deploy_pythons and
                environ["GITHUB_REF"] in deploy_branches):
            print("This build will be deployed!")
            pyb_args.append("upload")
    else:
        print("Running PR build!")

    project_dir = environ["GITHUB_WORKSPACE"]
    build_py = jp(project_dir, "build.py")

    if environ["WITH_VENV"] == "true":
        venv_dir = jp(expanduser("~"), ".pyb")
        if os_name == "Windows":
            venv_bin_dir = jp(venv_dir, "Scripts")
            python_bin = jp(venv_bin_dir, "python.exe")
        else:
            venv_bin_dir = jp(venv_dir, "bin")
            python_bin = jp(venv_bin_dir, "python")
        environ["PATH"] = venv_bin_dir + os.pathsep + environ["PATH"]
    else:
        if os_name == "Windows":
            venv_bin_dir = jp(dirname(sys.executable), "Scripts")
            environ["PATH"] = dirname(sys.executable) + os.pathsep + venv_bin_dir + os.pathsep + environ["PATH"]
        else:
            venv_bin_dir = dirname(sys.executable)
            environ["PATH"] = venv_bin_dir + os.pathsep + environ["PATH"]
        python_bin = sys.executable

    cmd_args = [python_bin, build_py] + pyb_args

    print("Will run PyBuilder build with the following args: %r" % cmd_args)

    sys.stdout.flush()

    subprocess.check_call(cmd_args, env=environ)
