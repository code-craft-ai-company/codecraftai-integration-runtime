"""
    .. package:: ccai.integrationruntime
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: The integration test-job layer of the Code Craft AI suite.

    This package hosts :class:`IntegratedTestJob` and the heavyweight reporting /
    integration machinery (JSOS/JSON streaming recorder, HTML summary rendering,
    result server, progress concentrators, streaming infrastructure, and the
    activation-driven integration CLI) that extends the near-standalone
    :mod:`ccai.testbase` single-host test framework.

    Present (Phase 4 core): :class:`IntegratedTestJob` / :class:`DefaultIntegratedTestJob`
    (``integratedtestjob``), :class:`RuntimeOutputContext` (``runtimeoutputcontext``),
    :class:`RuntimeRunMetadata` (``runtimerunmetadata``), and the
    :class:`IntegrationRuntimeDefaultTypeFactory` extension that registers the integration default
    job type. Still to land: the integration entry point / activation wiring, and the reporting
    code migrated out of ``codecraftai-testbase`` (JSON/JSOS recorder HTML rendering, ``templates/v2``,
    streaming, concentrators, result server — Phase 3). See
    ``REFACTOR-TESTBASE-INTEGRATION-RUNTIME-ROADMAP.md`` at the monorepo root.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []
