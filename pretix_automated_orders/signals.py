from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from pretix.control.signals import nav_event


@receiver(nav_event, dispatch_uid="automated_orders_nav")
def navbar_info(sender, request, **kwargs):
    url = resolve(request.path_info)
    if request.user.has_event_permission(
        request.organizer, request.event, "can_view_orders"
    ) or request.user.has_active_staff_session(request.session.session_key):
        return [
            {
                "label": _("Create automated tickets"),
                "icon": "ticket",
                "url": reverse(
                    "plugins:pretix_automated_orders:index",
                    kwargs={
                        "event": request.event.slug,
                        "organizer": request.organizer.slug,
                    },
                ),
                "active": url.namespace == "plugins:pretix_automated_orders"
                and url.url_name == "index",
            }
        ]
    return []
