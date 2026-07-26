"""
    .. module:: ccai_tests.integrationruntime.test_integrationjsonresultrecorder
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
import unittest

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


class IntegrationJsonResultRecorderRendersHtmlTests(unittest.TestCase):

    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        return

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        return

    def test_is_subclass_of_jsonresultrecorder(self):
        self.assertTrue(issubclass(IntegrationJsonResultRecorder, JsonResultRecorder))

    def test_initialize_report_copies_html_summary_template(self):
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(self.output_dir))
        recorder.initialize_report()
        copied_template = os.path.join(self.output_dir, "testsummary.html")
        self.assertTrue(os.path.exists(copied_template))

    def test_initialize_report_publishes_static_resources(self):
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(self.output_dir))
        recorder.initialize_report()
        static_dest = os.path.join(self.output_dir, "static")
        self.assertTrue(os.path.isdir(static_dest))
        published_count = 0
        for _, _, files in os.walk(static_dest):
            published_count = published_count + len(files)
        self.assertGreater(published_count, 0)

    def test_initialize_report_writes_catalog(self):
        recorder = IntegrationJsonResultRecorder(runid="r1", start=datetime.now(), render_info=_make_render_info(self.output_dir))
        recorder.initialize_report()
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "catalog.json")))


class TestbaseBaseRecorderOmitsHtmlTests(unittest.TestCase):

    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        return

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        return

    def test_base_jsonresultrecorder_writes_catalog_but_not_html(self):
        # After the Phase 3 split, testbase's JsonResultRecorder.initialize_report only generates the
        # output-directory catalog; the HTML summary template copy + static publishing relocated to
        # integration-runtime's IntegrationJsonResultRecorder.
        recorder = JsonResultRecorder(runid="r2", start=datetime.now(), render_info=_make_render_info(self.output_dir))
        recorder.initialize_report()
        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "testsummary.html")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "catalog.json")))


class StaticResourceDeploymentSemanticsTests(unittest.TestCase):
    """
        Semantics of update_render_environment, ported from testbase's
        StaticResourceDeploymentIntegrationTests when the behaviour they
        exercised relocated here: nested resources keep their relative
        paths, existing destination files are never overwritten, and a
        None source deploys nothing.
    """

    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        self.static_src = os.path.join(self.output_dir, "src_static")
        self.static_dest = os.path.join(self.output_dir, "static")
        os.makedirs(self.static_src)
        return

    def tearDown(self):
        shutil.rmtree(self.output_dir, ignore_errors=True)
        return

    def _recorder_with_source(self, source):
        info = _make_render_info(self.output_dir)
        info.static_resource_source = source
        info.static_resource_destination = self.static_dest
        recorder = IntegrationJsonResultRecorder(runid="r3", start=datetime.now(), render_info=info)
        return recorder

    def test_nested_static_resources_keep_their_relative_paths(self):
        os.makedirs(os.path.join(self.static_src, "css", "themes"))
        with open(os.path.join(self.static_src, "css", "themes", "dark.css"), "w") as fh:
            fh.write("body { background: black; }")

        recorder = self._recorder_with_source(self.static_src)
        recorder.update_render_environment()

        deployed = os.path.join(self.static_dest, "css", "themes", "dark.css")
        self.assertTrue(os.path.exists(deployed))

    def test_existing_destination_files_are_not_overwritten(self):
        with open(os.path.join(self.static_src, "app.js"), "w") as fh:
            fh.write("source content")
        os.makedirs(self.static_dest)
        with open(os.path.join(self.static_dest, "app.js"), "w") as fh:
            fh.write("destination content - must survive")

        recorder = self._recorder_with_source(self.static_src)
        recorder.update_render_environment()

        with open(os.path.join(self.static_dest, "app.js"), "r") as fh:
            content = fh.read()
        self.assertEqual(content, "destination content - must survive")

    def test_none_source_deploys_nothing(self):
        recorder = self._recorder_with_source(None)
        recorder.update_render_environment()

        self.assertFalse(os.path.exists(self.static_dest))


if __name__ == "__main__":
    unittest.main()
