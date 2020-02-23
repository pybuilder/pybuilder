import os
import subprocess
import sys
from os.path import join as jp, dirname, abspath, realpath as rp

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
        environ["VENV_DIR"] = abspath(".\\venv\\Scripts")

    script_dir = rp(abspath(dirname(sys.modules["__main__"].__file__)))
    script = rp(jp(script_dir, "travis_%s%s" % (sys.argv[1], SUFFIXES[os_name])))
    print("Executing script %r" % script)
    subprocess.check_call([script], env=environ)
