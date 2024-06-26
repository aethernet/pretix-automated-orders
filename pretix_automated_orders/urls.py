from django.urls import re_path as url

from . import views

urlpatterns = [
    url(
        r"^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/automated_orders/",
        views.OrderBulkCreateView.as_view(),
        name="index",
    ),
]
