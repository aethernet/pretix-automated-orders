from django.contrib import messages
from django.shortcuts import reverse, redirect
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from pretix.control.permissions import EventPermissionRequiredMixin
from .forms import AutomatedBulkOrdersForm
from .tasks import process_orders

"""
Pretix Order creator plugin
João Lucas Pires, jpires@evolutio.pt

The approach used here was to create a navigation view to allow the user to interface 
easily with the plugin. A snippet of the vouchers bulk form from the Pretix source code 
was used to allow to obtain a similar method of cleaning the data and building the 
data structures required for the minimal e-mail data.
In order to create the orders itself, the approach uses the create method of the Order 
Serializer in the Pretix API so that Pretix itself throttles the requests and handles
the async stuff.
"""


class OrderBulkCreateView(EventPermissionRequiredMixin, FormView):
    form_class = AutomatedBulkOrdersForm
    template_name = "automated_orders/index.html"
    permission = "can_change_orders"
    task = process_orders

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        return self.render_to_response(self.get_context_data())

    def get_success_url(self, value=None) -> str:
        return reverse(
            "control:event.orders",
            kwargs={
                "organizer": self.request.event.organizer.slug,
                "event": self.request.event.slug,
            },
        )

    def get_error_url(self, value=None):
        return reverse(
            "control:event.orders",
            kwargs={
                "organizer": self.request.event.organizer.slug,
                "event": self.request.event.slug,
            },
        )

    def form_valid(self, form):
        product = form.cleaned_data["product"]
        recipients = form.cleaned_data["send_recipients"]
        self.task.apply_async(
            args=(product.id, recipients, self.request.event.id, self.request.user.id, self.request.event.organizer.id))
        messages.add_message(
            self.request,
            messages.INFO,
            "Automated orders are being created in the background.",
        )
        return redirect(self.get_success_url())

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "event": self.request.event}

    def get_error_message(self, exception):
        return _(
            "There was an error while sending orders via e-mail. Some orders might have been sent."
        )
