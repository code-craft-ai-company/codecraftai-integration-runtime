"""
    .. module:: ccai_tests.integrationruntime.test_integrationruntimedefaulttypefactory
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-contract tests for IntegrationRuntimeDefaultTypeFactory -- it must register
               DefaultIntegratedTestJob as the default job type, at the precedence that sits between
               testbase's base default and testplus's distributed default.

    .. moduleauthor:: CodeCraftX
"""

from ccai.extension.factory.factoryextension import FactoryExtension

from ccai.testbase.factoryprotocols import TestBaseFactoryProtocol
from ccai.testbase.testjob import TestJob

from ccai.integrationruntime.integratedtestjob import IntegratedTestJob, DefaultIntegratedTestJob
from ccai.integrationruntime.integrationruntimedefaulttypefactory import IntegrationRuntimeDefaultTypeFactory


def test_default_job_type_is_default_integrated_test_job() -> None:
    """
        The factory must report DefaultIntegratedTestJob as the testbase default job type.
    """
    found = IntegrationRuntimeDefaultTypeFactory.get_testbase_default_job_type()
    assert found is DefaultIntegratedTestJob
    return


def test_precedence_is_ten() -> None:
    """
        The factory precedence must be 10, sitting between testbase's base default and
        testplus's distributed default.
    """
    assert IntegrationRuntimeDefaultTypeFactory.PRECEDENCE == 10
    return


def test_factory_extends_extension_and_protocol() -> None:
    """
        The factory must extend both FactoryExtension and TestBaseFactoryProtocol.
    """
    assert issubclass(IntegrationRuntimeDefaultTypeFactory, FactoryExtension)
    assert issubclass(IntegrationRuntimeDefaultTypeFactory, TestBaseFactoryProtocol)
    return


def test_default_job_inheritance_chain() -> None:
    """
        The default job inheritance chain must be DefaultIntegratedTestJob -> IntegratedTestJob -> TestJob.
    """
    assert issubclass(DefaultIntegratedTestJob, IntegratedTestJob)
    assert issubclass(IntegratedTestJob, TestJob)
    return
