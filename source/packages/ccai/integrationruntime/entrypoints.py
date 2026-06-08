"""
    .. module:: ccai.integrationruntime.entrypoints
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration test entry point — activates the application as a test-run job, then
               runs a test module under an :class:`IntegratedTestJob`.

    Plain ``testbase`` exposes :func:`ccai.testbase.entrypoints.generic_test_entrypoint`, the
    standalone entry point that records to stdout via ``StdoutResultRecorder`` and performs no
    activation. :func:`integrated_test_entrypoint` is the integration counterpart: it performs the
    this-app activation (persona + runtime-variable resolution + ``activate_profile_job``) so the
    presence-folder / ``RuntimeVariables`` behaviour is available, then delegates to the same
    decoupled testbase core with an :class:`IntegratedTestJob`-derived job type — which records JSOS
    + the rendered HTML summary under the presence folder.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional, Type

from ccai.testbase.testjob import TestJob
from ccai.testbase.entrypoints import generic_test_entrypoint

from ccai.integrationruntime.initialize import initialize_integration_runtime, initialize_integration_results
from ccai.integrationruntime.integratedtestjob import DefaultIntegratedTestJob


def integrated_test_entrypoint(job_type: Optional[Type[TestJob]] = None) -> None:
    """
        Integration test entry point for running a test module under an :class:`IntegratedTestJob`.

        Activates the process as a ``TestRun`` job (establishing the application persona, resolving
        runtime variables, and configuring the result resources) and then delegates to the decoupled
        testbase core (:func:`generic_test_entrypoint`) — which performs test-module resolution,
        argument parsing, and job execution. Because the runtime is activated, the
        :class:`IntegratedTestJob` records results under the well-known presence folder.

        :param job_type: The :class:`TestJob` subclass to run. Defaults to
            :class:`DefaultIntegratedTestJob` when not supplied. (Downstream packages such as
            ``testplus`` pass their own ``IntegratedTestJob``-derived type.)

        :returns: This function does not return; ``generic_test_entrypoint`` exits with the
            test result code.
    """
    initialize_integration_runtime()

    initialize_integration_results()

    resolved_job_type = job_type
    if resolved_job_type is None:
        resolved_job_type = DefaultIntegratedTestJob

    generic_test_entrypoint(job_type=resolved_job_type)

    return
