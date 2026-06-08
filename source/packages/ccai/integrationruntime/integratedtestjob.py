"""
    .. module:: ccai.integrationruntime.integratedtestjob
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`IntegratedTestJob` — the integration-tier test job that re-supplies the
               heavyweight reporting/integration behaviour the near-standalone ``testbase``
               :class:`TestJob` deliberately leaves out.

    ``IntegratedTestJob`` extends :class:`ccai.testbase.testjob.TestJob` and overrides the three
    provider hooks the standalone framework exposes:

    * ``_create_output_context`` -> :class:`RuntimeOutputContext` — results / diagnostics /
      per-testcase by-products land under the activated application's well-known presence folder.
    * ``_create_run_metadata`` -> :class:`RuntimeRunMetadata` — build / pipeline / job metadata is
      sourced from the resolved ``RuntimeVariables`` (CI/runtime context) instead of ``(unknown)``
      placeholders.
    * ``_create_recorder`` -> :class:`ccai.testbase.results.recorders.jsonresultrecorder.JsonResultRecorder`
      — JSOS streaming + the rendered HTML summary, in place of the stdout recorder.

    It is *intended* to sit between ``TestJob`` and the landscape-aware ``InteropLibraryTestJob`` —
    target chain ``TestJob -> IntegratedTestJob -> InteropLibraryTestJob -> DistributedTestJob``. As
    built today, ``IntegratedTestJob`` and ``InteropLibraryTestJob`` both extend ``TestJob`` directly
    (siblings); the re-parent of ``InteropLibraryTestJob`` onto ``IntegratedTestJob`` is pending
    (Phase 5).

    NOTE: ``IntegratedTestJob`` assumes the process has already been activated as a test-run job
    (``this-app`` activation sets ``AM_JOB_TYPE`` / ``AM_PRESENCE_DIR`` / ``AM_RESULT_PATH_FOR_TESTS``)
    before ``begin()`` resolves the presence-folder paths. The integration entry point performs that
    activation prior to constructing the job.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from datetime import datetime

from ccai.testbase.testjob import TestJob
from ccai.testbase.output.outputcontext import IOutputContext
from ccai.testbase.output.runmetadata import IRunMetadata
from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.recorders.resultrecorder import ResultRecorder

from ccai.integrationruntime.runtimeoutputcontext import RuntimeOutputContext
from ccai.integrationruntime.runtimerunmetadata import RuntimeRunMetadata
from ccai.integrationruntime.results.recorders.integrationjsonresultrecorder import IntegrationJsonResultRecorder


class IntegratedTestJob(TestJob):
    """
        Integration-tier :class:`TestJob` that records JSOS / HTML results under the activated
        application's presence folder and sources its run metadata from ``RuntimeVariables``.
    """

    def _create_output_context(self) -> IOutputContext:
        """
            Provides the presence-folder-backed output context for integration runs.

            :returns: A :class:`RuntimeOutputContext` instance.
        """
        inst = RuntimeOutputContext()
        return inst

    def _create_run_metadata(self) -> IRunMetadata:
        """
            Provides run metadata sourced from the resolved ``RuntimeVariables``.

            :returns: A :class:`RuntimeRunMetadata` instance.
        """
        run_title = "Test Run"
        if self.name is not None and len(self.name) > 0:
            run_title = self.name

        inst = RuntimeRunMetadata(title=run_title)
        return inst

    def _create_recorder(self, runid: str, start: datetime, render_info: RenderInfo, build_info: BuildInfo,
                         pipeline_info: PipelineInfo, job_info: JobInfo) -> ResultRecorder:
        """
            Provides the JSOS-streaming, HTML-rendering result recorder for integration runs.

            :returns: An :class:`IntegrationJsonResultRecorder` instance.
        """
        inst = IntegrationJsonResultRecorder(runid=runid, start=start, render_info=render_info, apod=self._apod,
                                             build_info=build_info, pipeline_info=pipeline_info, job_info=job_info)
        return inst


class DefaultIntegratedTestJob(IntegratedTestJob):
    """
        The :class:`DefaultIntegratedTestJob` is used as a job container when an integration run does
        not specify a job.
    """
    name = "Test Job"
    description = "Unspecified integration test job."
