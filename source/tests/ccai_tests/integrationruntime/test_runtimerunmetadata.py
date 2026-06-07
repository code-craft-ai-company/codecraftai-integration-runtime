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

from unittest import mock

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
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_RUN_ID = "run-abc-123"
            metadata = RuntimeRunMetadata()
            self.assertEqual(metadata.run_id, "run-abc-123")

    def test_run_id_generates_uuid_when_unset(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_RUN_ID = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            generated = metadata.run_id
            # uuid.UUID raises ValueError if 'generated' is not a valid uuid string.
            parsed = uuid.UUID(generated)
            self.assertEqual(str(parsed), generated)

    def test_title_falls_back_when_job_name_unset(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_NAME = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata(title="Fallback Title")
            self.assertEqual(metadata.title, "Fallback Title")

    def test_title_uses_job_name_when_set(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_JOB_NAME = "CI Job 42"
            metadata = RuntimeRunMetadata(title="Fallback Title")
            self.assertEqual(metadata.title, "CI Job 42")

    def test_apod_is_none_when_unset(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_AUTOMATION_POD = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            self.assertIsNone(metadata.apod)

    def test_apod_value_when_set(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_AUTOMATION_POD = "pod-7"
            metadata = RuntimeRunMetadata()
            self.assertEqual(metadata.apod, "pod-7")

    def test_testrun_timeout_is_none_when_unset(self):
        with mock.patch.object(rrm, "RuntimeVariables") as mockrv:
            mockrv.AM_TESTRUN_TIMEOUT = NOT_SET_SENTINEL
            metadata = RuntimeRunMetadata()
            self.assertIsNone(metadata.testrun_timeout)


if __name__ == "__main__":
    unittest.main()
