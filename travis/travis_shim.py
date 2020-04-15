import os
import subprocess
import sys
from os.path import join as jp, dirname, abspath, normcase as nc, expanduser

SUFFIXES = {"osx": ".sh",
            "linux": ".sh",
            "windows": ".cmd"}

if __name__ == "__main__":
    environ = os.environ
    os_name = environ["TRAVIS_OS_NAME"]

    if os_name == "windows":
        environ["PYTHON_PACKAGE"] = "python%s" % (environ["PYTHON_VERSION"][0])
        environ["PYTHON_BIN"] = abspath("\\Python%s%s" %
                                        (environ["PYTHON_VERSION"][0], environ["PYTHON_VERSION"][2]))
        venv_bin_dir = nc(abspath("\\venv\\Scripts"))
        environ["VENV_DIR"] = venv_bin_dir
    else:
        venv_bin_dir = nc(jp(expanduser("~"), ".pyenv", "versions",
                             "pyb-%s" % environ["PYTHON_VERSION"],
                             "bin"))
        environ["VENV_DIR"] = venv_bin_dir

    script_dir = nc(abspath(dirname(sys.modules["__main__"].__file__)))
    if sys.argv[1] == "install":
        script = nc(jp(script_dir, "travis_%s%s" % (sys.argv[1], SUFFIXES[os_name])))
        print("Executing script %r" % script)
        subprocess.check_call([script], env=environ)
    elif sys.argv[1] == "build":
        pyb_args = environ["PYB_ARGS"].split()
        deploy_oses = environ["DEPLOY_OSES"].split()
        deploy_pythons = environ["DEPLOY_PYTHONS"].split()
        deploy_branches = environ["DEPLOY_BRANCHES"].split()

        is_production = environ["TRAVIS_PULL_REQUEST"] == "false"
        if is_production:
            print("Running Production build!")
            if (environ["TRAVIS_OS_NAME"] in deploy_oses and
                    environ["PYTHON_VERSION"] in deploy_pythons and
                    environ["TRAVIS_BRANCH"] in deploy_branches):
                print("This build will be deployed!")
                pyb_args.append("upload")
        else:
            print("Running PR build!")

        project_dir = dirname(script_dir)
        build_py = nc(jp(project_dir, "build.py"))
        if os_name == "windows":
            python_bin = jp(venv_bin_dir, "python.exe")
        else:
            python_bin = jp(venv_bin_dir, "python")

        environ["PATH"] = venv_bin_dir + os.pathsep + environ["PATH"]
        cmd_args = [python_bin, build_py] + pyb_args

        if (not is_production or environ["PYTHON_VERSION"] in deploy_pythons
                and environ["TRAVIS_OS_NAME"] in deploy_oses):
            print("Will run PyBuilder build with the following args: %r" % cmd_args)

            sys.stdout.flush()

            subprocess.check_call(cmd_args, env=environ)
        else:
            print("Skipping building on OS %r Python %r as "
                  "this production version won't be deployed" % (environ["TRAVIS_OS_NAME"],
                                                                 environ["PYTHON_VERSION"]))
            sys.stdout.flush()
