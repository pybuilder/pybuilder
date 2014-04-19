from pybuilder.core import task

@task
def say_hello(project, logger):
    logger.info("Hello {0}, I am an external plugin from PyPI!".format(project.name))
