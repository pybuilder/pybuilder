import os
import subprocess

from pybuilder.core import task
from pybuilder.utils import assert_can_execute


@task
def pdoc_generate(project, logger):
    assert_can_execute(command_and_arguments=["pdoc", "--version"],
                       prerequisite="pdoc",
                       caller=pdoc_generate.__name__)

    logger.info("Generating pdoc documentation")

    command_and_arguments = ["pdoc", "--html", "pybuilder", "--all-submodules", "--overwrite", "--html-dir", "api-doc"]
    source_directory = project.get_property("dir_source_main_python")
    environment = {"PYTHONPATH": source_directory,
                   "PATH": os.environ["PATH"]}

    subprocess.check_call(command_and_arguments, shell=False, env=environment)
