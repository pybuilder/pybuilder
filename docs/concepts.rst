Concepts
#########



Introduction
***************************
PyBuilder is a multi-purpose software build tool. Most commonly it targets the building and management of software with a strong focus on Python.


Advantages for python projects
******************************

Some of the capabilities provided by PyBuilder out-of-the box are:
    * Automatic execution of unit and integration tests on every build
    * Automatic analysis of the code coverage
    * Automatic execution and result interpretation of analysis tools, such as flake8
    * Automatic generation of distutils script ``setup.py``

The general idea is that everything you do in your continuous integration chain, you also do locally before checking in your work.


Why Another Build Tool
**********************

When working on large scale software projects based on Java and Groovy I delved into the build process using tools such as Apache Ant, Apache Maven or Gradle. Although none of these tools is perfect they all provide a powerful and extensible way for building and testing software.

When focusing on Python I looked for a similar tool and got frustrated by the large number of tools that all match some aspect of the build and test process. Unfortunately, many of those tools were not suitable for composition and there was no central point of entry.

I suddenly found myself writing “build scripts” in Python over and over again using the tools I found out to be useful.

PyBuilder was born on the attempt to create a reusable tool that should:
    * Make simple things simple
    * Make hard things as simple as possible
    * Let me use whatever tool I want to integrate
    * Integrate these tools into a common view
    * Let me use Python (which is really great) to write my build files

Design
*********

PyBuilder executes build logic that is organized into tasks and actions.

Tasks are the main building blocks of the build logic. A task is an enclosed piece of build logic to be executed as a single unit. Each task can name a set of other tasks that it depends on. PyBuilder ensures that a task gets executed only after all of its dependencies have been executed.

Actions are smaller pieces of build logic than tasks. They are bound to the execution of task. Each action states that it needs to be executed before or after a named task. PyBuilder will execute the action if and only if the named task is executed, either directly or through another tasks’ dependencies.

Actions as well as tasks are decorated plain Python functions. Thus, you can structure your code the way you like if you provide a single point of entry to a build step.

Both task and action functions can request parameters known to PyBuilder through dependency injection by parameter name.

