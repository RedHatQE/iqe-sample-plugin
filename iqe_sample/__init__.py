import attr
import importscan

from . import fixtures
from iqe.base.application.plugins import ApplicationPlugin, ApplicationPluginException


class ApplicationSampleException(ApplicationPluginException):
    """Basic Exception for sample object"""

    pass


@attr.s
class ApplicationSample(ApplicationPlugin):
    """Holder for application sample related methods and functions"""

    plugin_real_name = "Sample"
    plugin_name = "sample"
    plugin_title = "Sample"
    plugin_package_name = "iqe-sample-plugin"


importscan.scan(fixtures)
