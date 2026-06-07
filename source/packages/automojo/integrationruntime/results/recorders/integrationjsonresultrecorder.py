"""
    .. module:: automojo.integrationruntime.results.recorders.integrationjsonresultrecorder
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`IntegrationJsonResultRecorder` — extends testbase's JSOS/JSON
               :class:`JsonResultRecorder` with the HTML-summary presentation behaviour relocated out
               of the near-standalone testbase framework in the Phase 3 results split.

    The near-standalone ``automojo-testbase`` :class:`ResultRecorder` base now only generates the
    output-directory catalog; it no longer publishes static render resources or copies the HTML
    summary template. This recorder re-supplies that behaviour for integration runs by overriding
    ``update_render_environment`` (static-resource publishing) and ``initialize_report`` (which
    publishes the resources, copies the HTML summary template, then delegates to the base for the
    catalog).

    .. moduleauthor:: AutomationX
"""

__author__ = "AutomationX"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


import os
import shutil

from automojo.testbase.results.exceptions import ResultRecordingError
from automojo.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder


class IntegrationJsonResultRecorder(JsonResultRecorder):
    """
        A JSOS/JSON result recorder that additionally renders the HTML summary report.

        This recorder extends :class:`automojo.testbase.results.recorders.jsonresultrecorder.JsonResultRecorder`
        (JSOS/JSON serialization plus the output-directory catalog) with the HTML presentation
        behaviour that the near-standalone testbase framework deliberately omits. It is the recorder
        installed by :class:`automojo.integrationruntime.integratedtestjob.IntegratedTestJob`.

        It adds no instance state, so the :class:`JsonResultRecorder` constructor is inherited
        unchanged.
    """

    def update_render_environment(self) -> None:
        """
            Publishes the static render resources required by the HTML presentation.

            Copies the CSS / JavaScript / image resources from
            ``render_info.static_resource_source`` into ``render_info.static_resource_destination``.
            Files are copied only when they do not already exist at the destination, so the method is
            safe to call repeatedly (e.g. for shared-resource deployments).

            :returns: None

            :raises: ResultRecordingError if a destination directory cannot be created or a resource
                     cannot be copied.
        """

        if self._render_info.static_resource_source is not None:
            static_resource_dest_dir = self._render_info.static_resource_destination
            static_resource_src_dir = self._render_info.static_resource_source

            for nxt_root, _, nxt_files in os.walk(static_resource_src_dir):
                for nf in nxt_files:
                    res_src_full = os.path.join(nxt_root, nf)
                    res_src_leaf = res_src_full[len(static_resource_src_dir):].lstrip(os.sep)
                    res_dest_full = os.path.join(static_resource_dest_dir, res_src_leaf)
                    if not os.path.exists(res_dest_full):
                        dest_dir = os.path.dirname(res_dest_full)
                        if not os.path.exists(dest_dir):
                            try:
                                os.makedirs(dest_dir)
                            except OSError as err:
                                errmsg = f"Failed to create directory '{dest_dir}' for static resources."
                                raise ResultRecordingError(
                                    errmsg,
                                    file_path=dest_dir,
                                    operation="creating static resource directory",
                                    original_error=err
                                ) from err
                        try:
                            shutil.copy2(res_src_full, res_dest_full)
                        except OSError as err:
                            errmsg = f"Failed to copy static resource from '{res_src_full}' to '{res_dest_full}'."
                            raise ResultRecordingError(
                                errmsg,
                                file_path=res_dest_full,
                                operation="copying static resource",
                                original_error=err
                            ) from err

        return

    def initialize_report(self) -> None:
        """
            Initializes the HTML report output environment, then performs the base catalog step.

            Publishes the static render resources, copies the HTML summary template into the results
            directory, then delegates to :meth:`JsonResultRecorder.initialize_report` (the base
            output-directory catalog). This preserves the original ordering (static resources, then
            template, then catalog) so the catalog includes the published HTML resources.

            :returns: None

            :raises: ResultRecordingError if the summary template cannot be copied.
        """

        self.update_render_environment()

        summary_html_source = self._render_info.summary_template
        summary_render_html_base = self.get_summary_render_file_basename()
        summary_render_html_dest = os.path.join(self._output_dir, summary_render_html_base)

        try:
            shutil.copy2(summary_html_source, summary_render_html_dest)
        except OSError as err:
            errmsg = f"Failed to copy summary template from '{summary_html_source}' to '{summary_render_html_dest}'."
            raise ResultRecordingError(
                errmsg,
                file_path=summary_render_html_dest,
                operation="copying summary template",
                original_error=err
            ) from err

        super().initialize_report()

        return
