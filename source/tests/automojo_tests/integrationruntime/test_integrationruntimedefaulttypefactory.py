"""
    .. module:: automojo_tests.integrationruntime.test_integrationruntimedefaulttypefactory
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Integration-contract tests for IntegrationRuntimeDefaultTypeFactory -- it must register
               DefaultIntegratedTestJob as the default job type, at the precedence that sits between
               testbase's base default and testplus's distributed default.

    .. moduleauthor:: AutomationX
"""

import unittest

from automojo.extension.factory.factoryextension import FactoryExtension

from automojo.testbase.factoryprotocols import TestBaseFactoryProtocol
from automojo.testbase.testjob import TestJob

from automojo.integrationruntime.integratedtestjob import IntegratedTestJob, DefaultIntegratedTestJob
from automojo.integrationruntime.integrationruntimedefaulttypefactory import IntegrationRuntimeDefaultTypeFactory


class IntegrationRuntimeDefaultTypeFactoryTests(unittest.TestCase):

    def test_default_job_type_is_default_integrated_test_job(self):
        found = IntegrationRuntimeDefaultTypeFactory.get_testbase_default_job_type()
        self.assertIs(found, DefaultIntegratedTestJob)

    def test_precedence_is_ten(self):
        self.assertEqual(IntegrationRuntimeDefaultTypeFactory.PRECEDENCE, 10)

    def test_factory_extends_extension_and_protocol(self):
        self.assertTrue(issubclass(IntegrationRuntimeDefaultTypeFactory, FactoryExtension))
        self.assertTrue(issubclass(IntegrationRuntimeDefaultTypeFactory, TestBaseFactoryProtocol))

    def test_default_job_inheritance_chain(self):
        self.assertTrue(issubclass(DefaultIntegratedTestJob, IntegratedTestJob))
        self.assertTrue(issubclass(IntegratedTestJob, TestJob))


if __name__ == "__main__":
    unittest.main()
