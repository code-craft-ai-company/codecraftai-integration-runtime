"""
    .. module:: ccai.integrationruntime.initialize
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration activation/initialisation wiring — establishing the application
               persona, resolving runtime variables, configuring HTML result resources, and
               activating the process as a ``TestRun`` job.

    This is the integration init that used to live in ``ccai.testbase.initialize``
    (``initialize_testbase_runtime`` / ``initialize_testbase_results``). It moved here as part of
    pushing ``testbase`` down the dependency tree: plain ``testbase`` runs standalone (stdout,
    ``SimpleOutputContext``, no activation), while the integration runtime performs the activation
    that lights up the presence-folder / ``RuntimeVariables`` behaviour consumed by
    :class:`ccai.integrationruntime.integratedtestjob.IntegratedTestJob`.

    .. note::
        As of the landed Phase 3 results split, the HTML summary template + static-resource paths
        live in this package's own ``templates/v2``; :class:`IntegrationResultResources` resolves
        them from this package directory.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import os

from ccai.thisapp.wellknown import ThisApplicationSingleton
from ccai.thisapp.persona import establish_app_persona
from ccai.thisapp.enumerations import JobType
from ccai.thisapp.activation import activate_profile_job
from ccai.thisapp.runtimevariables import RuntimeVariables, RuntimeVariablesDesc, resolve_runtime_variables


_PACKAGE_DIR = os.path.dirname(__file__)


class IntegrationResultResources:
    """
        Well-known locations of the HTML summary template and static render resources used by the
        integration result recorder. As of the Phase 3 results split these resources live in this
        package's own ``templates/v2`` directory (relocated out of ``codecraftai-testbase``).
    """

    TEMPLATES_DIR = os.path.join(_PACKAGE_DIR, "templates")
    RESOURCE_DEST_LEAF = os.path.join("static", "v2")
    RESOURCE_SRC_DIR = os.path.join(TEMPLATES_DIR, "v2", "static")
    SUMMARY_TEMPLATE = os.path.join(TEMPLATES_DIR, "v2", "testsummary.html")


def initialize_integration_runtime(name: str = "ccai", logger_name: str = "TB",
                                   log_basename: str = "testrun") -> None:
    """
        Establishes the application persona and resolves runtime variables for an integration run.

        This must be called early in an integration entry point, before constructing an
        :class:`IntegratedTestJob`, so the ``ThisApplication`` singleton and ``RuntimeVariables`` are
        available.

        :param name: The application name (also the home-directory leaf under the user's home).
        :param logger_name: The prefix used to identify log messages.
        :param log_basename: The base name used for log files.

        :returns: None
    """
    home_dir = os.path.join(os.path.expanduser("~"), name)

    establish_app_persona(name=name, home_dir=home_dir, logger_name=logger_name, log_basename=log_basename)

    resolve_runtime_variables()

    return


def initialize_integration_results() -> None:
    """
        Configures the HTML result-resource paths (if unset) and activates the process as a
        ``TestRun`` job.

        Activation sets ``AM_JOB_TYPE`` (lighting up the presence-folder path helpers) and wires up
        logging for the job profile. It must be called after :func:`initialize_integration_runtime`.

        :returns: None
    """
    this_app = ThisApplicationSingleton()

    dest_static_dir = os.path.join(RuntimeVariables.AM_PRESENCE_DIR, "results", IntegrationResultResources.RESOURCE_DEST_LEAF)

    if RuntimeVariables.AM_RESULTS_STATIC_RESOURCE_SRC_DIR is None:
        this_app.override_variable_value(RuntimeVariablesDesc.AM_RESULTS_STATIC_RESOURCE_SRC_DIR, IntegrationResultResources.RESOURCE_SRC_DIR)
    if RuntimeVariables.AM_RESULTS_STATIC_RESOURCE_DEST_DIR is None:
        this_app.override_variable_value(RuntimeVariablesDesc.AM_RESULTS_STATIC_RESOURCE_DEST_DIR, dest_static_dir)
    if RuntimeVariables.AM_RESULTS_STATIC_SUMMARY_TEMPLATE is None:
        this_app.override_variable_value(RuntimeVariablesDesc.AM_RESULTS_STATIC_SUMMARY_TEMPLATE, IntegrationResultResources.SUMMARY_TEMPLATE)

    activate_profile_job(job_type=JobType.TestRun)

    return
