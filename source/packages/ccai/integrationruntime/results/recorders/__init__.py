"""
    .. module:: ccai.integrationruntime.results.recorders
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-tier result recorders relocated from ``codecraftai-testbase``. These extend
               testbase's JSOS/JSON ``JsonResultRecorder`` with streaming and (HTML-summary) rendering
               behaviour that the near-standalone framework deliberately omits.

    .. moduleauthor:: CodeCraftX
"""

__author__ = "CodeCraftX"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai.integrationruntime.results.recorders.integrationjsonresultrecorder import IntegrationJsonResultRecorder
from ccai.integrationruntime.results.recorders.streamingresultrecorder import StreamingResultRecorder

__all__ = [
    "IntegrationJsonResultRecorder",
    "StreamingResultRecorder"
]
