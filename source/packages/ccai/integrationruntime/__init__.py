"""
    .. package:: ccai.integrationruntime
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration test-job layer of the Code Craft AI suite.

    This package hosts :class:`IntegratedTestJob` and the heavyweight reporting /
    integration machinery (JSOS/JSON streaming recorder, HTML summary rendering,
    result server, progress concentrators, streaming infrastructure, and the
    activation-driven integration CLI) that extends the near-standalone
    :mod:`ccai.testbase` single-host test framework.

    Present (Phase 4 core plus the landed Phase 3 results split): :class:`IntegratedTestJob` /
    :class:`DefaultIntegratedTestJob` (``integratedtestjob``), :class:`RuntimeOutputContext`
    (``runtimeoutputcontext``), :class:`RuntimeRunMetadata` (``runtimerunmetadata``), the
    :class:`IntegrationRuntimeDefaultTypeFactory` extension that registers the integration default
    job type, the integration entry point / activation wiring (``entrypoints``, ``initialize``), and
    the reporting code split out of ``codecraftai-testbase`` -- the JSON/JSOS streaming recorder, HTML
    summary rendering, ``templates/v2``, streaming infrastructure, progress concentrators, and result
    server -- all now local to this package. See
    ``REFACTOR-TESTBASE-INTEGRATION-RUNTIME-ROADMAP.md`` at the monorepo root.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []
