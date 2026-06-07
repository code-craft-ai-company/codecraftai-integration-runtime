"""
    .. module:: ccai.integrationruntime.runtimeoutputcontext
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration :class:`IOutputContext` that resolves run artefact directories under
               the activated application's well-known presence folder.

    Where the standalone :class:`ccai.testbase.output.outputcontext.SimpleOutputContext` roots
    everything under ``<cwd>/.output``, :class:`RuntimeOutputContext` delegates to the well-known
    path helpers in :mod:`ccai.thisapp.paths` so that, when the process has been activated as a
    test-run job, results / diagnostics / per-testcase by-products land under the presence folder
    (``AM_PRESENCE_DIR`` / ``AM_RESULT_PATH_FOR_TESTS``). Those helpers are *activation-gated* — they
    raise :class:`SemanticError` unless ``AM_JOB_TYPE`` has been set — which is exactly why plain
    ``testbase`` must NOT use this context.

    :class:`ccai.integrationruntime.integratedtestjob.IntegratedTestJob` installs this context by
    overriding ``TestJob._create_output_context``.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from ccai.testbase.output.outputcontext import IOutputContext

from ccai.thisapp.paths import (
    get_path_for_testresults,
    get_path_for_testcase_by_products,
    get_path_for_diagnostics,
    get_summary_html_template_source,
    get_summary_static_resource_src_dir,
    get_summary_static_resource_dest_dir,
)


class RuntimeOutputContext(IOutputContext):
    """
        Integration output context that resolves artefact directories under the activated
        application's well-known presence folder via :mod:`ccai.thisapp.paths`.
    """

    def get_test_results_dir(self) -> str:
        results_dir = get_path_for_testresults()
        return results_dir

    def get_testcase_byproducts_dir(self, test_id: str) -> str:
        byproducts_dir = get_path_for_testcase_by_products(test_id)
        return byproducts_dir

    def get_diagnostics_dir(self, label: str) -> str:
        diagnostics_dir = get_path_for_diagnostics(label)
        return diagnostics_dir

    def get_summary_template_source(self) -> Optional[str]:
        template_source = get_summary_html_template_source()
        return template_source

    def get_static_resource_source(self) -> Optional[str]:
        resource_source = get_summary_static_resource_src_dir()
        return resource_source

    def get_static_resource_destination(self) -> Optional[str]:
        resource_destination = get_summary_static_resource_dest_dir()
        return resource_destination
