from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, prefetch_related_objects
from django.shortcuts import reverse, redirect
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView
from django_scopes import scope
from pretix.api.serializers.order import OrderCreateSerializer, OrderSerializer
from pretix.base.i18n import language
from pretix.base.models import Checkin, Order, OrderPosition
from pretix.base.models.auth import User
from pretix.base.models.event import Event
from pretix.base.models.orders import QuestionAnswer
from pretix.base.services.invoices import generate_invoice, invoice_qualified
from pretix.base.services.orders import (
    _order_placed_email,
    _order_placed_email_attendee,
)
from pretix.base.signals import order_paid, order_placed
from pretix.base.views.tasks import AsyncAction
from pretix.celery_app import app
from django.contrib.auth import get_user_model
from pretix.control.permissions import EventPermissionRequiredMixin
from .forms import AutomatedBulkOrdersForm
from pretix.base.models.organizer import Organizer


@app.task
def process_orders(product_id, recipients, event_id, user_id, organizer_id):
    """
    Extracted from pretix/api/view/orders.py
    Modified to handle custom built jsons and celery integration.
    """
    # Celery doesnt support tasks with non-serializable objects.
    # We need to fetch the passed objects from their ids.
    user = get_user_model().objects.get(id=user_id)
    with scope(organizer=Organizer.objects.get(id=organizer_id)):
        event = Event.objects.get(id=event_id)
        # For each order:
        n = len(recipients)
        i = 1
        for customer in recipients:
            i = i + 1
            # for some reason namedtuple casts to list ->  [email, number, name, tag]
            customer_name = customer[2]
            customer_email = customer[0]
            if len(customer_name) == 0:
                customer_name = "Aluno"
            data = {
                "email": customer_email,
                "locale": "fr-be",
                "sales_channel": "web",
                "positions": [
                    {
                        "item": product_id,
                        "attendee_name": customer_name,
                        "attendee_email": customer_email,
                    }
                ],
                "payment_provider": "free",
                "send_email": True,
            }
            serializer = OrderCreateSerializer(data=data, context={"event": event})
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                serializer.save()
                send_mail = serializer._send_mail
                order = serializer.instance
                prefetch_related_objects(
                    [order],
                    Prefetch(
                        "positions",
                        OrderPosition.objects.all().prefetch_related(
                            Prefetch("checkins", queryset=Checkin.objects.all()),
                            "item",
                            "variation",
                            Prefetch(
                                "answers",
                                queryset=QuestionAnswer.objects.prefetch_related(
                                    "options", "question"
                                ).order_by("question__position"),
                            ),
                            "seat",
                        ),
                    ),
                )
                serializer = OrderSerializer(
                    order,
                    context={
                        **serializer.context,
                        "pdf_data": True,
                        "include": [],
                        "exclude": [],
                    },
                )
                order.log_action(
                    "pretix.event.order.placed",
                    user=user if user.is_authenticated else None,
                    auth=None,
                )

            with language(order.locale, event.settings.region):
                payment = order.payments.last()
                order_placed.send(event, order=order)
                if order.status == Order.STATUS_PAID:
                    order_paid.send(event, order=order)
                    order.log_action(
                        "pretix.event.order.paid",
                        {
                            "provider": payment.provider if payment else None,
                            "info": {},
                            "date": now().isoformat(),
                            "force": False,
                        },
                        user=user if user.is_authenticated else None,
                        auth=None,
                    )

                gen_invoice = (
                        invoice_qualified(order)
                        and (
                                (order.event.settings.get("invoice_generate") == "True")
                                or (
                                        order.event.settings.get("invoice_generate") == "paid"
                                        and order.status == Order.STATUS_PAID
                                )
                        )
                        and not order.invoices.last()
                )
                invoice = None
                if gen_invoice:
                    invoice = generate_invoice(order, trigger_pdf=True)

                if send_mail:
                    free_flow = (
                            payment
                            and order.total == Decimal("0.00")
                            and order.status == Order.STATUS_PAID
                            and not order.require_approval
                            and payment.provider in ("free", "boxoffice")
                    )
                    if order.require_approval:
                        email_template = (
                            event.settings.mail_text_order_placed_require_approval
                        )
                        subject_template = (
                            event.settings.mail_subject_order_placed_require_approval
                        )
                        log_entry = "pretix.event.order.email.order_placed_require_approval"
                        email_attendees = False
                    elif free_flow:
                        email_template = event.settings.mail_text_order_free
                        subject_template = event.settings.mail_subject_order_free
                        log_entry = "pretix.event.order.email.order_free"
                        email_attendees = event.settings.mail_send_order_free_attendee
                        email_attendees_template = (
                            event.settings.mail_text_order_free_attendee
                        )
                        subject_attendees_template = (
                            event.settings.mail_subject_order_free_attendee
                        )
                    else:
                        email_template = event.settings.mail_text_order_placed
                        subject_template = event.settings.mail_subject_order_placed
                        log_entry = "pretix.event.order.email.order_placed"
                        email_attendees = event.settings.mail_send_order_placed_attendee
                        email_attendees_template = (
                            event.settings.mail_text_order_placed_attendee
                        )
                        subject_attendees_template = (
                            event.settings.mail_subject_order_placed_attendee
                        )

                    _order_placed_email(
                        event,
                        order,
                        email_template,
                        subject_template,
                        log_entry,
                        invoice,
                        [payment] if payment else [],
                        is_free=free_flow,
                    )
                    if email_attendees:
                        for p in order.positions.all():
                            if (
                                    p.addon_to_id is None
                                    and p.attendee_email
                                    and p.attendee_email != order.email
                            ):
                                _order_placed_email_attendee(
                                    event,
                                    order,
                                    p,
                                    email_attendees_template,
                                    subject_attendees_template,
                                    log_entry,
                                    is_free=free_flow,
                                )

                    if not free_flow and order.status == Order.STATUS_PAID and payment:
                        payment._send_paid_mail(invoice, None, "")
                        if event.settings.mail_send_order_paid_attendee:
                            for p in order.positions.all():
                                if (
                                        p.addon_to_id is None
                                        and p.attendee_email
                                        and p.attendee_email != order.email
                                ):
                                    payment._send_paid_mail_attendee(p, None)
