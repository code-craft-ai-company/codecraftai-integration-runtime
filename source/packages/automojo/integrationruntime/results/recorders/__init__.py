"""
    .. module:: automojo.integrationruntime.results.recorders
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-tier result recorders relocated from ``automojo-testbase``. These extend
               testbase's JSOS/JSON ``JsonResultRecorder`` with streaming and (HTML-summary) rendering
               behaviour that the near-standalone framework deliberately omits.

    .. moduleauthor:: AutomationX
"""

__author__ = "AutomationX"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from automojo.integrationruntime.results.recorders.integrationjsonresultrecorder import IntegrationJsonResultRecorder
from automojo.integrationruntime.results.recorders.streamingresultrecorder import StreamingResultRecorder

__all__ = [
    "IntegrationJsonResultRecorder",
    "StreamingResultRecorder"
]
