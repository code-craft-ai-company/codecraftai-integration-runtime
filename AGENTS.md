# Personality
AI Agents working in this repository should conduct themselves as a Principal Software
Engineer and Archtect working at the "Code Craft AI LLC" company. This software engineer
is known as 'CodeCraftX'.  The primary goal of 'CodeCraftX' is to help the company build
a suite of Python foundation software packages that are well planned out, highely reusable,
modular and that enable companies to rapidly build advanced automation software system and
automation pipelines.  When building and creating packages, 'CodeCraftX' always focuses
on reusing modular code from other 'codecraftai-*' packages and always works to look at the big
picture and make sure code and functionality is placed in the correct 'codecraftai-*' package.
CodeCraftX is a very creative, but very disciplined software engineer that values code stability,
reusability and scalability over quick fixes and fast delivery.  CodeCraftX always keeps
in mind the companies goal of building a comprehensive suite of foundation Python packages
that are well design, cohesive, and easy to use and that provide rapid but stable results.

# Rules
- Look in the '<repository>/specs' folder for specification files that help to steer development work
- Look in the '<repository>/userguide' folder for files containing standards and conventions
- Look in the '<repository>/prompts' folder for pre-build prompts
- Files inside the .venv folder should not be modified, they are modified by the setup scripts
- Place test results inside the .output folder, don't create .output-* directories in the root of the repository
- Never work around missing dependencies, hault and ask for assistance
- Avoid using relative imports
- When creating specs to build/update other specs, preceed the spec folder with 'x-'
- Only write tests to test product code, never write tests to verify specs
- Always prioritize the reuse of code from 'codecraftai-*' packages over rewriting functionality

# Project Overview
The `codecraftai-integration-runtime` package is the *integration test-job layer* of the
Code Craft AI suite. It builds on the near-standalone `codecraftai-testbase` single-host
test framework and, via the `codecraftai-extension` extensibility mechanism, supplies the
`IntegratedTestJob` class plus the heavyweight reporting/integration machinery that plain
`testbase` deliberately omits.

`IntegratedTestJob` extends `ccai.testbase.testjob.TestJob` and overrides the three
provider hooks the standalone framework exposes (it does NOT override the five `fire_*`
landscape hooks):

* `_create_output_context` -> `RuntimeOutputContext` — results / diagnostics / per-testcase
  by-products land under the activated application's well-known presence folder.
* `_create_run_metadata` -> `RuntimeRunMetadata` — build / pipeline / job metadata is sourced
  from the resolved `RuntimeVariables` instead of `(unknown)` placeholders.
* `_create_recorder` -> `JsonResultRecorder` — JSOS streaming plus the rendered HTML summary,
  in place of `testbase`'s default stdout recorder.

The `JsonResultRecorder` (and the HTML `templates/v2` assets it renders) still physically
live in `codecraftai-testbase` today; `IntegratedTestJob` imports the recorder from there, and
`initialize.py` resolves the template / static-resource paths out of the testbase package
directory. Their relocation into this package is pending (Phase 3 — see below).

## TestJob inheritance chain (as built vs target)

`IntegratedTestJob` is intended to sit between `testbase`'s `TestJob` and the
landscape-aware `InteropLibraryTestJob` (`codecraftai-interop`).

* AS BUILT TODAY: `IntegratedTestJob` and `InteropLibraryTestJob` both extend `TestJob`
  directly — they are siblings. `InteropLibraryTestJob` has not been re-parented onto
  `IntegratedTestJob` yet.
* TARGET (Phase 5, in-flight): `TestJob (testbase) -> IntegratedTestJob (this package) ->
  InteropLibraryTestJob (interop) -> DistributedTestJob (testplus)`.

## Origin

This package was formed by repurposing the former `codecraftai-runtime`. The general runtime
foundation (runtime variables, well-known paths, profile/job enumerations, activation) was
moved *down* into `codecraftai-this-app` (`ccai.thisapp.*`); `codecraftai-runtime` is being
retired and currently holds thin re-export shims. The integration test-job machinery is being
migrated here from `codecraftai-testbase`.

It depends on `codecraftai-testbase`, `codecraftai-this-app`, `codecraftai-extension`,
`codecraftai-foundations`, and the `ccai.xmodules` support libraries.

# Current State

The Phase-4 integration core is BUILT and present on disk:

* `IntegratedTestJob` / `DefaultIntegratedTestJob`
  (`integrationruntime/integratedtestjob.py`)
* `RuntimeOutputContext` (`integrationruntime/runtimeoutputcontext.py`) — the
  presence-folder-backed, activation-gated output context
* `RuntimeRunMetadata` (`integrationruntime/runtimerunmetadata.py`) — run metadata built from
  `RuntimeVariables`
* `IntegrationRuntimeDefaultTypeFactory`
  (`integrationruntime/integrationruntimedefaulttypefactory.py`) — registers
  `DefaultIntegratedTestJob` as the default job type via the testbase factory protocol
* the activation init `initialize_integration_runtime` / `initialize_integration_results`
  (`integrationruntime/initialize.py`)
* `integrated_test_entrypoint` (`integrationruntime/entrypoints.py`)

> STILL PENDING:
> * Phase 3 — migrating the JSON/HTML result recorder, the `templates/v2` assets, the
>   streaming-result infrastructure, the progress concentrators, and the result server out of
>   `codecraftai-testbase` into this package. Until then, `IntegratedTestJob` imports
>   `JsonResultRecorder` from testbase and `initialize.py` resolves the HTML resources from the
>   testbase package directory.
> * Phase 5 — re-parenting `InteropLibraryTestJob` onto `IntegratedTestJob` (see chain above).
>
> See `REFACTOR-TESTBASE-INTEGRATION-RUNTIME-ROADMAP.md` at the monorepo root.

# Testing Conventions
The 'codecraftai-integration-runtime' package repository utilizes the 'testbase' test
framework to test its functionality (it depends on `codecraftai-testbase`). Tests live under
'source/testroots/ccai/tests'.

## Test Granularity
Tests should verify the functionality of individual components or functions in isolation,
focusing on a single aspect of the code for clarity and maintainability.

# Running Tests
After setting up the environment, run the testbase tests with:

```
    source <repository-root>/.venv/bin/activate

    testbase testing run --root ./source/testroots/ccai --includes=ccai.tests --output=./.output

    deactivate
```

# Coding Standards
The code in this repository follows the Code Craft AI Python coding standards
(debuggability over performance, readability over conciseness, explicit over implicit,
Sphinx-style docstrings, no mutable defaults).

# Packaging
Currently, this package is utilized using a reference to the github repository. It is
currently not published.
