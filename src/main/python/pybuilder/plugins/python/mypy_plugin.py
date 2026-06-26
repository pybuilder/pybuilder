from pybuilder.core import use_plugin, after, init, task
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder

use_plugin("python.core")
use_plugin("analysis")

DEFAULT_MYPY_OPTIONS = ["--ignore-missing-imports", "--show-error-codes"]


@init
def initialize_mypy_plugin(project):
    project.plugin_depends_on("mypy", ">=1.0")
    project.set_property_if_unset("mypy_options", DEFAULT_MYPY_OPTIONS)
    project.set_property_if_unset("mypy_break_build", False)
    project.set_property_if_unset("mypy_include_test_sources", False)
    project.set_property_if_unset("mypy_include_scripts", False)


@after("prepare")
def assert_mypy_is_executable(project, logger, reactor):
    logger.debug("Checking availability of MyPy")
    reactor.pybuilder_venv.verify_can_execute(["mypy", "--version"], "mypy", "plugin python.mypy")


@task("analyze")
def execute_mypy(project, logger, reactor):
    logger.info("Executing mypy on project sources")

    verbose = project.get_property("verbose")
    project.set_property_if_unset("mypy_verbose_output", verbose)

    command = ExternalCommandBuilder("mypy", project, reactor)

    for opt in project.get_property("mypy_options"):
        command.use_argument(opt)

    include_test_sources = project.get_property("mypy_include_test_sources")
    include_scripts = project.get_property("mypy_include_scripts")

    result = command.run_on_production_source_files(logger,
                                                    include_test_sources=include_test_sources,
                                                    include_scripts=include_scripts,
                                                    include_dirs_only=True)

    break_build = project.get_property("mypy_break_build")

    errors = [line.rstrip()
              for line in result.report_lines
              if ".py:" in line]
    error_count = len(errors)

    if error_count:
        for error in errors:
            logger.warn("mypy: %s", error)

        message = "mypy found {} type error(s).".format(error_count)
        if break_build:
            logger.error(message)
            raise BuildFailedException(message)
        else:
            logger.warn(message)
