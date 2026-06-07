"""
    .. module:: ccai.integrationruntime.results.recorders.streamingresultrecorder
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Module for streaming-enabled result recorder.

    This module provides a result recorder that streams results to external
    services in real-time while also writing them to local files.

    .. moduleauthor:: CodeCraftX
"""



__author__ = "CodeCraftX"
__copyright__ = "Copyright 2025, Code Craft AI LLC"
__credits__ = []


from typing import Optional

from datetime import datetime

from ccai.testbase.results.model.buildinfo import BuildInfo
from ccai.testbase.results.model.jobinfo import JobInfo
from ccai.testbase.results.model.pipelineinfo import PipelineInfo
from ccai.testbase.results.model.renderinfo import RenderInfo
from ccai.testbase.results.model.forwardinginfo import ForwardingInfo
from ccai.testbase.results.model.streaminginfo import StreamingInfo, StreamingCallback

from ccai.testbase.results.model.resultnode import ResultNode

from ccai.testbase.results.recorders.jsonresultrecorder import JsonResultRecorder
from ccai.integrationruntime.results.streaming.resultstreamer import (
    ResultStreamer,
    create_result_streamer
)


class StreamingResultRecorder(JsonResultRecorder):
    """
        A result recorder that streams results to external services in real-time.
        
        This recorder extends :class:`JsonResultRecorder` to add real-time streaming
        of test results to external monitoring services. Results are both written
        to local files (as with JsonResultRecorder) and streamed to the configured
        external service.
        
        The streaming functionality supports both REST endpoint streaming and
        WebSocket-based streaming, allowing integration with various monitoring
        and dashboard systems.
        
        Context Manager Lifecycle
        -------------------------
        The StreamingResultRecorder extends the JsonResultRecorder lifecycle:
        
        1. **Entry (__enter__)**: 
           - Initializes local file recording (inherited)
           - Starts the result streaming thread
           
        2. **Active Recording**:
           - preview() writes to local file AND streams to external service
           - record() writes to local file AND streams to external service
           
        3. **Exit (__exit__)**:
           - Stops the streaming thread
           - Finalizes local file recording (inherited)
        
        Thread Safety
        -------------
        The StreamingResultRecorder is thread-safe for concurrent recording.
        The streaming thread operates independently and uses a queue to receive
        results from the recording thread.
        
        Example Usage
        -------------
        Basic usage with REST streaming::
        
            from datetime import datetime
            from ccai.testbase.results.recorders.streamingresultrecorder import (
                StreamingResultRecorder
            )
            from ccai.testbase.results.model.renderinfo import RenderInfo
            from ccai.testbase.results.model.streaminginfo import (
                StreamingInfo, StreamingProtocol
            )
            
            # Configure render info (local files)
            render_info = RenderInfo(
                title="My Test Run",
                summary_filename="/output/testsummary.json",
                summary_template="/templates/testsummary.html",
                stream_results_filename="/output/testresults_stream.jsos",
                consolidated_results_filename="/output/testresults.json",
                static_resource_source="/templates/static",
                static_resource_destination="/output/static"
            )
            
            # Configure streaming (external service)
            streaming_info = StreamingInfo(
                protocol=StreamingProtocol.REST,
                streaming_url="https://monitoring.example.com/api/results",
                streaming_headers={"Authorization": "Bearer token123"},
                stream_previews=True,
                stream_results=True
            )
            
            # Use as context manager
            with StreamingResultRecorder(
                runid="run-uuid-123",
                start=datetime.now(),
                render_info=render_info,
                streaming_info=streaming_info
            ) as recorder:
                # Record test results - they are written locally AND streamed
                for test_result in test_results:
                    recorder.preview(test_result)
                    # ... execute test ...
                    recorder.record(test_result)
        
        See Also
        --------
        :class:`JsonResultRecorder` : Base class for JSON result recording
        :class:`ResultStreamer` : Base class for result streaming
        :class:`RestResultStreamer` : REST endpoint streaming implementation
        :class:`WebSocketResultStreamer` : WebSocket streaming implementation
    """
    
    def __init__(self, *, runid: str, start: datetime, render_info: RenderInfo,
                 streaming_info: StreamingInfo,
                 apod: Optional[str] = None, build_info: Optional[BuildInfo] = None,
                 pipeline_info: Optional[PipelineInfo] = None, job_info: Optional[JobInfo] = None,
                 streaming_callback: Optional[StreamingCallback] = None):
        """
            Initializes the StreamingResultRecorder.
            
            :param runid: The uuid string that identifies a set of test results.
            :param start: The date and time of the start of the test run.
            :param render_info: A :class:`RenderInfo` instance containing output file paths.
            :param streaming_info: A :class:`StreamingInfo` instance containing streaming
                                   configuration for the external service.
            :param apod: Optional name of an automation pod.
            :param build_info: Optional :class:`BuildInfo` instance.
            :param pipeline_info: Optional :class:`PipelineInfo` instance.
            :param job_info: Optional :class:`JobInfo` instance.
            :param streaming_callback: Optional :class:`StreamingCallback` for custom
                                       result handling during streaming.
            
            :returns: None
        """
        super().__init__(
            runid=runid,
            start=start,
            render_info=render_info,
            apod=apod,
            build_info=build_info,
            pipeline_info=pipeline_info,
            job_info=job_info
        )
        
        self._streaming_info = streaming_info
        self._streaming_callback = streaming_callback
        self._streamer: Optional[ResultStreamer] = None
    
    def __enter__(self):
        """
            Starts up the recording process and streaming thread.
            
            This method extends the parent __enter__ to also start the
            result streaming thread.
            
            :returns: self - The recorder instance for use within the context block.
        """
        # Initialize local file recording
        super().__enter__()
        
        # Start the streaming thread
        self._streamer = create_result_streamer(
            self._streaming_info,
            self._streaming_callback
        )
        self._streamer.start()
        
        return self
    
    def __exit__(self, ex_type, ex_inst, ex_tb):
        """
            Finalizes the recording process and stops the streaming thread.
            
            This method extends the parent __exit__ to also stop the
            result streaming thread.
            
            :param ex_type: The type of exception being raised, or None.
            :param ex_inst: The exception instance, or None.
            :param ex_tb: The traceback, or None.
            
            :returns: None
        """
        # Stop the streaming thread
        if self._streamer is not None:
            self._streamer.stop()
            self._streamer = None
        
        # Finalize local file recording
        return super().__exit__(ex_type, ex_inst, ex_tb)
    
    def preview(self, result: ResultNode):
        """
            Writes a preview of a result to the stream file and streams it.
            
            This method extends the parent preview to also stream the
            preview to the external service.
            
            :param result: A :class:`ResultNode` object to preview.
            
            :returns: None
        """
        # Write to local file
        super().preview(result)
        
        # Stream to external service
        if self._streamer is not None and self._streamer.is_running:
            result_dict = result.as_dict(is_preview=True)
            self._streamer.stream_preview(result_dict)
    
    def record(self, result: ResultNode):
        """
            Records a final result entry and streams it.
            
            This method extends the parent record to also stream the
            result to the external service.
            
            :param result: A :class:`ResultNode` object to record.
            
            :returns: None
        """
        # Write to local file
        super().record(result)
        
        # Stream to external service
        if self._streamer is not None and self._streamer.is_running:
            result_dict = result.as_dict(is_preview=False)
            self._streamer.stream_result(result_dict)
    
    @property
    def streaming_stats(self) -> dict:
        """
            Returns streaming statistics.
            
            :returns: A dictionary containing streaming statistics including
                      previews_sent, results_sent, errors, and reconnects.
        """
        if self._streamer is not None:
            return self._streamer.stats
        return {
            "previews_sent": 0,
            "results_sent": 0,
            "errors": 0,
            "reconnects": 0
        }
    
    @property
    def is_streaming(self) -> bool:
        """
            Returns True if the streaming thread is running.
            
            :returns: True if streaming is active, False otherwise.
        """
        return self._streamer is not None and self._streamer.is_running
