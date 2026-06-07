"""
    .. module:: ccai.tests.singlehost.integrationruntime.test_runtimeoutputcontext
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-contract tests for RuntimeOutputContext -- it must delegate artefact-directory
               resolution to the activated application's well-known-path helpers, and must NOT swallow the
               SemanticError those helpers raise when the process has not been activated as a test-run job.

    The this-app path-helper boundary is mocked at the module level, so these tests run standalone.

    .. moduleauthor:: CodeCraftX
"""

from unittest import mock

from ccai.errors.exceptions import SemanticError

import ccai.integrationruntime.runtimeoutputcontext as roc
from ccai.integrationruntime.runtimeoutputcontext import RuntimeOutputContext


def test_get_test_results_dir_delegates_to_path_helper() -> None:
    """
        RuntimeOutputContext.get_test_results_dir must delegate to the
        well-known-path helper and return whatever the helper resolves.
    """
    with mock.patch.object(roc, "get_path_for_testresults", return_value="/presence/results/testresults") as mocked:
        context = RuntimeOutputContext()
        found = context.get_test_results_dir()
        assert found == "/presence/results/testresults"
        mocked.assert_called_once()
    return


def test_get_testcase_byproducts_dir_passes_test_id() -> None:
    """
        RuntimeOutputContext.get_testcase_byproducts_dir must pass the test id
        through to the well-known-path helper and return its result.
    """
    with mock.patch.object(roc, "get_path_for_testcase_by_products", return_value="/presence/byproducts/scope1") as mocked:
        context = RuntimeOutputContext()
        found = context.get_testcase_byproducts_dir("scope1")
        assert found == "/presence/byproducts/scope1"
        mocked.assert_called_once_with("scope1")
    return


def test_get_diagnostics_dir_passes_label() -> None:
    """
        RuntimeOutputContext.get_diagnostics_dir must pass the label through to
        the well-known-path helper and return its result.
    """
    with mock.patch.object(roc, "get_path_for_diagnostics", return_value="/presence/diagnostics/prerun") as mocked:
        context = RuntimeOutputContext()
        found = context.get_diagnostics_dir("prerun")
        assert found == "/presence/diagnostics/prerun"
        mocked.assert_called_once_with("prerun")
    return


def test_get_test_results_dir_propagates_semantic_error_when_not_activated() -> None:
    """
        The well-known-path helpers raise SemanticError when AM_JOB_TYPE has
        not been set (the process has not been activated as a test-run job).
        RuntimeOutputContext must let that SemanticError bubble -- it must
        never be swallowed.
    """
    # The well-known-path helpers raise SemanticError when AM_JOB_TYPE has not been set
    # (the process has not been activated as a test-run job). RuntimeOutputContext must let
    # that SemanticError bubble -- it must never be swallowed.
    gating_error = SemanticError("AM_JOB_TYPE is Unknown -- the process is not activated as a test-run job.")
    with mock.patch.object(roc, "get_path_for_testresults", side_effect=gating_error):
        context = RuntimeOutputContext()
        raised = False
        try:
            context.get_test_results_dir()
        except SemanticError:
            raised = True
        assert raised
    return
