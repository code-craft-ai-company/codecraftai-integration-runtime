=========================
automojo-integration-runtime
=========================

The ``automojo-integration-runtime`` package is the *integration test-job layer*
of the Automation Mojo suite.  It builds on the near-standalone ``automojo-testbase``
single-host test framework and, using the ``automojo-extension`` extensibility
mechanism, supplies the ``IntegratedTestJob`` that adds the heavyweight reporting
and integration behaviour that plain ``testbase`` deliberately leaves out:

* JSOS / JSON streaming result recording to a well-known results directory
* HTML-rendered test summaries (templates, static resources)
* build / pipeline / job metadata sourced from ``automojo.thisapp`` runtime variables
* the result server, progress concentrators, and streaming infrastructure
* the integration / activation-driven CLI commands

``automojo-testbase`` records to **stdout** (and optional JSOS/JSON files) and has no
dependency on this package.  Packages that need persistent, rendered, CI-grade results
(``automojo-interop``, ``automojo-testplus`` and their downstreams) build their TestJob
hierarchy on ``IntegratedTestJob`` from this package.

This package was formed by **renaming and repurposing** the former ``automojo-runtime``
package.  The general runtime foundation (runtime variables, well-known paths, profile/job
enumerations, activation) moved *down* into ``automojo-this-app``; what remains here is the
integration test-job machinery migrated out of ``automojo-testbase``.

See ``AGENTS.md`` for the project overview and ``REFACTOR-TESTBASE-INTEGRATION-RUNTIME-ROADMAP.md``
in the monorepo root for the migration plan.

Build / Test / Run
==================

This repository follows the shared ``automojo-*`` skeleton.

1. Re-home the repository (regenerates ``.env``)::

    ./repository-setup/rehome-repository

2. Set up the virtual environment::

    ./development/setup-environment
    poetry install --all-extras

3. Run the tests::

    source ./.venv/bin/activate
    testbase testing run --root ./source/testroots/automojo --includes=automojo.tests --output=./.output
    deactivate
