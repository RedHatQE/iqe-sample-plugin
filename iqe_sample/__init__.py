import attr
import importscan
from iqe.base.application.plugins import ApplicationPlugin, ApplicationPluginException

from . import fixtures


class ApplicationsampleException(ApplicationPluginException):
    """Basic Exception for sample object"""

    pass


@attr.s
class Applicationsample(ApplicationPlugin):
    """Holder for application sample related methods and functions"""

    plugin_app_name = "sample"
    plugin_real_name = "sample"
    plugin_name = "sample"
    plugin_title = "sample"
    plugin_package_name = "iqe-sample-plugin"


importscan.scan(fixtures)
