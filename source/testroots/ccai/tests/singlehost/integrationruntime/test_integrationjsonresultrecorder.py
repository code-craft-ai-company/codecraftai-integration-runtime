"""
    .. module:: ccai.tests.singlehost.integrationruntime.test_integrationjsonresultrecorder
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-contract tests for the Phase 3 recorder HTML split. IntegrationJsonResultRecorder
               (integration-runtime) must render the HTML summary -- copy the summary template + publish the
               static resources -- on top of the JSOS/JSON catalog, while testbase's base JsonResultRecorder
               must only write the catalog and must NOT render HTML.

    Uses the real relocated templates under ccai.integrationruntime/templates/v2 + temp output dirs, so
    it runs standalone without activation.

    .. moduleauthor:: CodeCraftX
"""

import os
import shutil
import tempfile

from datetime import datetime

import ccai.integrationruntime as _ir_pkg

from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder

from ccai.integrationruntime.results.recorders.integrationjsonresultrecorder import IntegrationJsonResultRecorder


_IR_TEMPLATES_V2 = os.path.join(os.path.dirname(_ir_pkg.__file__), "templates", "v2")


def _make_render_info(output_dir: str) -> RenderInfo:
    """
        Builds a :class:`RenderInfo` rooted at the given output directory and pointed at the relocated
        integration-runtime HTML template + static resources.

        :param output_dir: The directory that artefacts (summary, stream, static) are written under.

        :returns: A populated :class:`RenderInfo`.
    """
    info = RenderInfo(
        title="Integration Contract Test",
        summary_filename=os.path.join(output_dir, "testrun_summary.json"),
        summary_template=os.path.join(_IR_TEMPLATES_V2, "testsummary.html"),
        stream_results_filename=os.path.join(output_dir, "testrun_results_stream.jsos"),
        consolidated_results_filename=os.path.join(output_dir, "testrun_results.json"),
        static_resource_source=os.path.join(_IR_TEMPLATES_V2, "static"),
        static_resource_destination=os.path.join(output_dir, "static"),
    )
    return info


def _establish_env() -> str:
    """
        Replicates the original ``setUp`` for each test by creating a fresh temporary output directory.

        :returns: The path to the newly created temporary output directory.
    """
    output_dir = tempfile.mkdtemp()
    return output_dir


def _cleanup_env(output_dir: str) -> None:
    """
        Replicates the original ``tearDown`` for each test by removing the temporary output directory.

        :param output_dir: The temporary output directory to remove.
    """
    shutil.rmtree(output_dir, ignore_errors=True)
    return


def test_is_subclass_of_jsonresultrecorder() -> None:
    """
        Verifies that :class:`IntegrationJsonResultRecorder` is a subclass of the testbase
        :class:`JsonResultRecorder`.
    """
    output_dir = _establish_env()
    try:
        assert issubclass(IntegrationJsonResultRecorder, JsonResultRecorder)
    finally:
        _cleanup_env(output_dir=output_dir)
    return


def test_initialize_report_copies_html_summary_template() -> None:
    """
        Verifies that :meth:`IntegrationJsonResultRecorder.initialize_report` copies the HTML summary
        template into the output directory.
    """
    output_dir = _establish_env()
    try:
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(output_dir))
        recorder.initialize_report()
        copied_template = os.path.join(output_dir, "testsummary.html")
        assert os.path.exists(copied_template)
    finally:
        _cleanup_env(output_dir=output_dir)
    return


def test_initialize_report_publishes_static_resources() -> None:
    """
        Verifies that :meth:`IntegrationJsonResultRecorder.initialize_report` publishes the static
        resources into the output directory.
    """
    output_dir = _establish_env()
    try:
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(output_dir))
        recorder.initialize_report()
        static_dest = os.path.join(output_dir, "static")
        assert os.path.isdir(static_dest)
        published_count = 0
        for _, _, files in os.walk(static_dest):
            published_count = published_count + len(files)
        assert published_count > 0
    finally:
        _cleanup_env(output_dir=output_dir)
    return


def test_initialize_report_writes_catalog() -> None:
    """
        Verifies that :meth:`IntegrationJsonResultRecorder.initialize_report` writes the output-directory
        catalog.
    """
    output_dir = _establish_env()
    try:
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(output_dir))
        recorder.initialize_report()
        assert os.path.exists(os.path.join(output_dir, "catalog.json"))
    finally:
        _cleanup_env(output_dir=output_dir)
    return


def test_base_jsonresultrecorder_writes_catalog_but_not_html() -> None:
    """
        Verifies that after the Phase 3 split, the testbase :class:`JsonResultRecorder` writes only the
        output-directory catalog and does NOT render the HTML summary.
    """
    output_dir = _establish_env()
    try:
        # After the Phase 3 split, testbase's JsonResultRecorder.initialize_report only generates the
        # output-directory catalog; the HTML summary template copy + static publishing relocated to
        # integration-runtime's IntegrationJsonResultRecorder.
        recorder = JsonResultRecorder(runid="r2", start=datetime.now(), render_info=_make_render_info(output_dir))
        recorder.initialize_report()
        assert not os.path.exists(os.path.join(output_dir, "testsummary.html"))
        assert os.path.exists(os.path.join(output_dir, "catalog.json"))
    finally:
        _cleanup_env(output_dir=output_dir)
    return
