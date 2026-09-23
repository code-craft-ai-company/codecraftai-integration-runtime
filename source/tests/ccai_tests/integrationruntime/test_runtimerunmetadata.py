"""
    .. module:: ccai_tests.integrationruntime.test_runtimerunmetadata
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-contract tests for RuntimeRunMetadata -- the unset-value detection that maps
               the RuntimeVariables "(not-set)" sentinel to "(unknown)" placeholders, and the run-metadata
               properties sourced from RuntimeVariables (run_id, title, apod, testrun_timeout).

    The RuntimeVariables boundary is mocked at the module level, so these tests run standalone without
    activating a this-app persona.

    .. moduleauthor:: CodeCraftX
"""

import unittest
import uuid

import unittest.mock

import ccai.integrationruntime.runtimerunmetadata as rrm
from ccai.integrationruntime.runtimerunmetadata import (
    RuntimeRunMetadata,
    _is_unset,
    _resolve_val,
    UNKNOWN,
    NOT_SET_SENTINEL,
)


class IsUnsetAndResolveTests(unittest.TestCase):

    def test_none_is_unset(self):
        self.assertTrue(_is_unset(None))

    def test_empty_string_is_unset(self):
        self.assertTrue(_is_unset(""))

    def test_not_set_sentinel_is_unset(self):
        self.assertTrue(_is_unset(NOT_SET_SENTINEL))

    def test_real_value_is_set(self):
        self.assertFalse(_is_unset("realvalue"))

    def test_resolve_val_substitutes_unknown_for_unset(self):
        self.assertEqual(_resolve_val(NOT_SET_SENTINEL), UNKNOWN)

    def test_resolve_val_passes_through_real_value(self):
        self.assertEqual(_resolve_val("buildinfo"), "buildinfo")


class RuntimeRunMetadataPropertyTests(unittest.TestCase):

    def test_run_id_uses_runtime_value_when_set(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_RUN_ID = "run-abc-123"
            metadata = RuntimeRunMetadata()
            self.assertEqual(metadata.run_id, "run-abc-123")

    def test_run_id_generates_uuid_when_unset(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_RUN_ID = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            generated = metadata.run_id
            # uuid.UUID raises ValueError if 'generated' is not a valid uuid string.
            parsed = uuid.UUID(generated)
            self.assertEqual(str(parsed), generated)

    def test_title_falls_back_when_job_name_unset(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_NAME = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata(title="Fallback Title")
            self.assertEqual(metadata.title, "Fallback Title")

    def test_title_uses_job_name_when_set(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_NAME = "CI Job 42"
            metadata = RuntimeRunMetadata(title="Fallback Title")
            self.assertEqual(metadata.title, "CI Job 42")

    def test_apod_is_none_when_unset(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_AUTOMATION_POD = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            self.assertIsNone(metadata.apod)

    def test_apod_value_when_set(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_AUTOMATION_POD = "pod-7"
            metadata = RuntimeRunMetadata()
            self.assertEqual(metadata.apod, "pod-7")

    def test_testrun_timeout_is_none_when_unset(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_TESTRUN_TIMEOUT = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            self.assertIsNone(metadata.testrun_timeout)

    def test_job_seed_uses_runtime_value_when_set(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_SEED = "seed-12345"
            metadata = RuntimeRunMetadata()
            self.assertEqual(metadata.job_seed, "seed-12345")

    def test_job_seed_generates_uuid_once_when_unset(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_SEED = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            first = metadata.job_seed
            parsed = uuid.UUID(first)
            self.assertEqual(str(parsed), first)
            # Cached: the seed must be stable across reads within one run.
            self.assertEqual(metadata.job_seed, first)


class CIMetadataFieldMappingTests(unittest.TestCase):
    """
        The AM_* -> BuildInfo / PipelineInfo / JobInfo field mapping, ported
        from testbase's test_ci_metadata_integration.py when CI metadata
        sourcing relocated from TestJob attributes to this class.  These are
        the only tests that pin WHICH runtime variable feeds WHICH field.
    """

    BUILD_VALUES = {
        "AM_BUILD_BRANCH": "integration-test-branch",
        "AM_BUILD_NAME": "integration-build-123",
        "AM_BUILD_FLAVOR": "integration-release",
        "AM_BUILD_RELEASE": "3.0.0-integration",
        "AM_BUILD_URL": "https://ci.integration.example.com/build/123",
    }

    PIPELINE_VALUES = {
        "AM_PIPELINE_ID": "integration-pipeline-uuid",
        "AM_PIPELINE_NAME": "Integration Test Pipeline",
        "AM_PIPELINE_INSTANCE": "integration-instance-uuid",
    }

    JOB_VALUES = {
        "AM_JOB_ID": "integration-job-uuid",
        "AM_JOB_NAME": "Integration Test Job",
        "AM_JOB_TYPE": "TestRun",
        "AM_JOB_OWNER": "Integration Team",
        "AM_JOB_LABEL": "integration-label",
        "AM_JOB_INITIATOR": "integration@example.com",
        "AM_JOB_VENUE": "integration-venue",
        "AM_JOB_SEED": "integration-seed-12345",
        "AM_JOB_TAG": "integration-correlation-tag",
    }

    def _mock_rv(self, mockrv, values):
        for varname, varval in values.items():
            setattr(mockrv, varname, varval)
        return

    def test_build_info_maps_every_build_variable(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            self._mock_rv(mockrv, self.BUILD_VALUES)
            info = RuntimeRunMetadata().build_info()
            self.assertEqual(info.branch, self.BUILD_VALUES["AM_BUILD_BRANCH"])
            self.assertEqual(info.build, self.BUILD_VALUES["AM_BUILD_NAME"])
            self.assertEqual(info.flavor, self.BUILD_VALUES["AM_BUILD_FLAVOR"])
            self.assertEqual(info.release, self.BUILD_VALUES["AM_BUILD_RELEASE"])
            self.assertEqual(info.url, self.BUILD_VALUES["AM_BUILD_URL"])

    def test_pipeline_info_maps_every_pipeline_variable(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            self._mock_rv(mockrv, self.PIPELINE_VALUES)
            info = RuntimeRunMetadata().pipeline_info()
            self.assertEqual(info.id, self.PIPELINE_VALUES["AM_PIPELINE_ID"])
            self.assertEqual(info.name, self.PIPELINE_VALUES["AM_PIPELINE_NAME"])
            self.assertEqual(info.instance, self.PIPELINE_VALUES["AM_PIPELINE_INSTANCE"])

    def test_job_info_maps_every_job_variable(self):
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            self._mock_rv(mockrv, self.JOB_VALUES)
            info = RuntimeRunMetadata().job_info()
            self.assertEqual(info.id, self.JOB_VALUES["AM_JOB_ID"])
            self.assertEqual(info.name, self.JOB_VALUES["AM_JOB_NAME"])
            self.assertEqual(info.type, self.JOB_VALUES["AM_JOB_TYPE"])
            self.assertEqual(info.owner, self.JOB_VALUES["AM_JOB_OWNER"])
            self.assertEqual(info.label, self.JOB_VALUES["AM_JOB_LABEL"])
            self.assertEqual(info.initiator, self.JOB_VALUES["AM_JOB_INITIATOR"])
            self.assertEqual(info.venue, self.JOB_VALUES["AM_JOB_VENUE"])
            self.assertEqual(info.seed, self.JOB_VALUES["AM_JOB_SEED"])
            self.assertEqual(info.tag, self.JOB_VALUES["AM_JOB_TAG"])

    def test_partial_build_environment_substitutes_unknown_not_none(self):
        # Under the old model a partially-set environment leaked None into
        # BuildInfo, whose validation then raised.  RuntimeRunMetadata makes
        # that structurally impossible: every unset member becomes the
        # "(unknown)" placeholder, so the Info object always constructs.
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            self._mock_rv(mockrv, self.BUILD_VALUES)
            mockrv.AM_BUILD_NAME = NOT_SET_SENTINEL
            mockrv.AM_BUILD_URL = None
            info = RuntimeRunMetadata().build_info()
            self.assertEqual(info.branch, self.BUILD_VALUES["AM_BUILD_BRANCH"])
            self.assertEqual(info.build, UNKNOWN)
            self.assertEqual(info.url, UNKNOWN)

    def test_unset_pipeline_still_constructs_with_placeholders(self):
        # PipelineInfo is always created now; a run outside any pipeline gets
        # placeholders rather than a missing object.
        with unittest.mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            self._mock_rv(mockrv, {name: NOT_SET_SENTINEL for name in self.PIPELINE_VALUES})
            info = RuntimeRunMetadata().pipeline_info()
            self.assertEqual(info.id, UNKNOWN)
            self.assertEqual(info.name, UNKNOWN)
            self.assertEqual(info.instance, UNKNOWN)


if __name__ == "__main__":
    unittest.main()
