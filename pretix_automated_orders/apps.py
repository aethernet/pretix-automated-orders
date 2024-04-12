__version__ = "1.1.7"

from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_automated_orders"
    verbose_name = gettext_lazy("Automated Orders Plugin")

    class PretixPluginMeta:
        name = gettext_lazy("Automated Orders Plugin")
        author = "Joao Lucas Pires"
        description = gettext_lazy("Automates orders given a product and a list of emails.")
        visible = True
        version = "1.1.7"
        category = "FEATURE"
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = "pretix_automated_orders.PluginApp"
