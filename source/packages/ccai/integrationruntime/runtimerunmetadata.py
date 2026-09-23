"""
    .. module:: ccai.integrationruntime.runtimerunmetadata
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration :class:`IRunMetadata` that sources build / pipeline / job metadata
               from the activated application's :class:`RuntimeVariables`.

    Where the standalone :class:`ccai.testbase.output.runmetadata.StandaloneRunMetadata` fills the
    CI/build/pipeline/job descriptors with ``(unknown)`` placeholders, :class:`RuntimeRunMetadata`
    reads the resolved ``AM_*`` runtime variables (now owned by :mod:`ccai.thisapp.runtimevariables`)
    — exactly the values the original ``testbase`` ``TestJob`` read directly before the decoupling.

    :class:`ccai.integrationruntime.integratedtestjob.IntegratedTestJob` installs this by overriding
    ``TestJob._create_run_metadata``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from datetime import datetime
from typing import Any, Optional

import uuid

from ccai.testbase.output.runmetadata import IRunMetadata
from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.jobinfo import JobInfo

from ccai.thisapp.runtimevariables import RuntimeVariables


UNKNOWN = "(unknown)"

# The RuntimeVariables descriptors return the literal string "(not-set)" for an unresolved value
# (rather than None or the DefaultValue sentinel), so an unset CI variable must be detected by it.
NOT_SET_SENTINEL = "(not-set)"


def _is_unset(value: Any) -> bool:
    """
        Indicates whether a runtime-variable value should be treated as unset.

        :param value: The value read from a :class:`RuntimeVariables` descriptor.

        :returns: ``True`` when the value is ``None``, empty, the ``"(not-set)"`` sentinel, or the
                  ``DefaultValue`` sentinel.
    """
    if value is None:
        return True
    if value == "":
        return True
    if value == NOT_SET_SENTINEL:
        return True
    if type(value).__name__ == "DefaultValue":
        return True
    return False


def _resolve_val(value: Any) -> Any:
    """
        Resolves a runtime-variable value to a display value, substituting ``(unknown)`` for unset.

        :param value: The value read from a :class:`RuntimeVariables` descriptor.

        :returns: The value, or ``"(unknown)"`` when it is unset.
    """
    if _is_unset(value):
        return UNKNOWN
    return value


class RuntimeRunMetadata(IRunMetadata):
    """
        Integration run metadata sourced from the activated application's :class:`RuntimeVariables`.
    """

    def __init__(self, title: str = "Test Run"):
        """
            Constructor for a :class:`RuntimeRunMetadata`.

            :param title: A fallback title used when ``AM_JOB_NAME`` is not set.
        """
        self._fallback_title = title
        self._job_seed = None
        return

    @property
    def run_id(self) -> str:
        run_id_value = RuntimeVariables.AM_RUN_ID
        if _is_unset(run_id_value):
            run_id_value = str(uuid.uuid4())
        return str(run_id_value)

    @property
    def apod(self) -> Optional[str]:
        apod_value = RuntimeVariables.AM_AUTOMATION_POD
        if _is_unset(apod_value):
            return None
        return apod_value

    @property
    def title(self) -> str:
        job_name = RuntimeVariables.AM_JOB_NAME
        if _is_unset(job_name):
            return self._fallback_title
        return job_name

    @property
    def starttime(self) -> datetime:
        start_value = RuntimeVariables.AM_STARTTIME
        if _is_unset(start_value):
            start_value = datetime.now()
        return start_value

    @property
    def testrun_timeout(self) -> Optional[int]:
        timeout_value = RuntimeVariables.AM_TESTRUN_TIMEOUT
        if _is_unset(timeout_value):
            return None
        return timeout_value

    @property
    def job_seed(self) -> str:
        if self._job_seed is None:
            seed_value = RuntimeVariables.AM_JOB_SEED
            if _is_unset(seed_value):
                seed_value = str(uuid.uuid4())
            self._job_seed = str(seed_value)
        return self._job_seed

    def build_info(self) -> BuildInfo:
        info = BuildInfo(
            branch=_resolve_val(RuntimeVariables.AM_BUILD_BRANCH),
            build=_resolve_val(RuntimeVariables.AM_BUILD_NAME),
            flavor=_resolve_val(RuntimeVariables.AM_BUILD_FLAVOR),
            release=_resolve_val(RuntimeVariables.AM_BUILD_RELEASE),
            url=_resolve_val(RuntimeVariables.AM_BUILD_URL),
        )
        return info

    def pipeline_info(self) -> PipelineInfo:
        info = PipelineInfo(
            id=_resolve_val(RuntimeVariables.AM_PIPELINE_ID),
            name=_resolve_val(RuntimeVariables.AM_PIPELINE_NAME),
            instance=_resolve_val(RuntimeVariables.AM_PIPELINE_INSTANCE),
        )
        return info

    def job_info(self) -> JobInfo:
        info = JobInfo(
            id=_resolve_val(RuntimeVariables.AM_JOB_ID),
            name=_resolve_val(RuntimeVariables.AM_JOB_NAME),
            type=_resolve_val(RuntimeVariables.AM_JOB_TYPE),
            owner=_resolve_val(RuntimeVariables.AM_JOB_OWNER),
            label=_resolve_val(RuntimeVariables.AM_JOB_LABEL),
            initiator=_resolve_val(RuntimeVariables.AM_JOB_INITIATOR),
            venue=_resolve_val(RuntimeVariables.AM_JOB_VENUE),
            seed=self.job_seed,
            tag=_resolve_val(RuntimeVariables.AM_JOB_TAG),
        )
        return info
