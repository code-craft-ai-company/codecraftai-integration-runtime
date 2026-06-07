"""
    .. module:: automojo.integrationruntime.integrationruntimedefaulttypefactory
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Extension factory that registers :class:`IntegratedTestJob` as the default job type
               when ``automojo-integration-runtime`` is installed.

    This mirrors :class:`automojo.testplus.testplusdefaulttypefactory.TestPlusDefaultTypeFactory`:
    it extends the testbase factory protocol via :class:`FactoryExtension` so the super-factory
    search path can discover it. Its ``PRECEDENCE`` sits above the testbase base default
    (``DefaultTestJob``) and below testplus's distributed default — so the resolved default job type
    is ``DefaultTestJob`` with testbase alone, ``DefaultIntegratedTestJob`` once integration-runtime
    is present, and ``DistributedTestJob`` once testplus is present.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Automation Mojo LLC"
__credits__ = []


from typing import Type

from automojo.extension.factory.factoryextension import FactoryExtension

from automojo.testbase.factoryprotocols import TestBaseFactoryProtocol
from automojo.testbase.testjob import TestJob

from automojo.integrationruntime.integratedtestjob import DefaultIntegratedTestJob


class IntegrationRuntimeDefaultTypeFactory(FactoryExtension, TestBaseFactoryProtocol):
    """
        Supplies :class:`DefaultIntegratedTestJob` as the default job type for integration runs when
        no job is explicitly specified.
    """

    PRECEDENCE = 10

    @classmethod
    def get_testbase_default_job_type(cls) -> Type[TestJob]:
        """
            Used to lookup and return the most relevant default job type as determined by the
            super-factory search path.

            Declared as a ``classmethod`` to satisfy the parent contract on
            :class:`automojo.testbase.factoryprotocols.TestBaseFactoryProtocol`.

            :returns: The :class:`DefaultIntegratedTestJob` type.
        """
        return DefaultIntegratedTestJob
