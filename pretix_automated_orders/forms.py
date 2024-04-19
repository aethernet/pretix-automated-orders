import csv
from collections import namedtuple
from io import StringIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from pretix.base.models import Item
from pretix.base.models.orders import Order


class AutomatedBulkOrdersForm(forms.ModelForm):
    _event = None

    product = forms.ModelChoiceField(
        queryset=None,
        label=_("Product to create order from:"),
        required=True,
        help_text=_("Choose the product you want to offer to each customer."),
    )
    send_recipients = forms.CharField(
        label=_("Recipients"),
        widget=forms.Textarea(
            attrs={
                "placeholder": "email,name\njohn@example.org,John\n\n-- {} --\n\njohn@example.org\njane@example.net".format(
                    _("or")
                )
            }
        ),
        required=True,
        initial="email,name\n",
        help_text=_(
            f"You can either supply a list of email addresses with one email address per line, or a CSV file with a title column "
            'and one or more of the columns:'
        ) + ' "email", "name"',
    )

    class Meta:
        model = Order
        fields = [
            "product",
            "send_recipients",
        ]

    def __init__(self, *args, **kwargs):
        event = None
        if "event" in kwargs:
            event = kwargs.pop("event")
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Item.objects.filter(event=event, default_price=0)

    Recipient = namedtuple("Recipient", "email number name tag")

    def clean_send_recipients(self):
        raw = self.cleaned_data["send_recipients"]
        if not raw:
            return []
        r = raw.split("\n")
        res = []
        if "," in raw or ";" in raw:
            if "@" in r[0]:
                raise ValidationError(
                    _("CSV input needs to contain a header row in the first line.")
                )
            try:
                dialect = csv.Sniffer().sniff(raw[:1024])
                reader = csv.DictReader(StringIO(raw), dialect=dialect)
            except csv.Error as e:
                raise ValidationError(
                    _("CSV parsing failed: {error}.").format(error=str(e))
                )
            if "email" not in reader.fieldnames:
                raise ValidationError(
                    _(
                        'CSV input needs to contain a field with the header "{header}".'
                    ).format(header="email")
                )
            unknown_fields = [
                f
                for f in reader.fieldnames
                if f not in ("email", "name", "tag", "number")
            ]
            if unknown_fields:
                raise ValidationError(
                    _(
                        'CSV input contains an unknown field with the header "{header}".'
                    ).format(header=unknown_fields[0])
                )
            for i, row in enumerate(reader):
                try:
                    EmailValidator()(row["email"])
                except ValidationError as err:
                    raise ValidationError(
                        _("{value} is not a valid email address.").format(
                            value=row["email"]
                        )
                    ) from err
                try:
                    res.append(
                        self.Recipient(
                            name=row.get("name", ""),
                            email=row["email"].strip(),
                            number=int(row.get("number", 1)),
                            tag=row.get("tag", None),
                        )
                    )
                except ValueError as err:
                    raise ValidationError(
                        _("Invalid value in row {number}.").format(number=i + 1)
                    ) from err
        else:
            for e in r:
                try:
                    EmailValidator()(e.strip())
                except ValidationError as err:
                    raise ValidationError(
                        _("{value} is not a valid email address.").format(
                            value=e.strip()
                        )
                    ) from err
                else:
                    res.append(
                        self.Recipient(email=e.strip(), number=1, tag=None, name="")
                    )
        return res

    def clean(self):
        data = super().clean()

        if data.get("send") and not all([data.get("send_recipients")]):
            raise ValidationError(
                _("If orders should be sent by email, recipients need to be specified.")
            )

        if data.get("codes") and data.get("send"):
            recp = self.cleaned_data.get("send_recipients", [])
            code_len = len(data.get("codes"))
            recp_len = sum(r.number for r in recp)
            if code_len != recp_len:
                raise ValidationError(
                    _(
                        "You generated {codes} orders, but entered recipients for {recp} orders."
                    ).format(codes=code_len, recp=recp_len)
                )

        return data
