from webhooks.senders.base import Senderable

from ..conf import (
        WEBHOOK_OWNER_FIELD,
        WEBHOOK_ATTEMPTS,
    )
from ..models import WebhookTarget, Delivery


class DjangoSenderable(Senderable):

    def notify(self, message):
        if self.success:
            Delivery.objects.create(
                webhook_target=self.webhook_target,
                payload=self.payload,
                attempt=self.attempt,
                success=self.success,
                response_message=self.response.content,
                hash_value=self.hash_value,
                response_status=self.response.status_code,
                notification=message
            )
        else:
            Delivery.objects.create(
                webhook_target=self.webhook_target,
                payload=self.payload,
                attempt=self.attempt,
                success=self.success,
                hash_value=self.hash_value,
                notification=message
            )


def sender(wrapped, dkwargs, hash_value=None, *args, **kwargs):
    """
        This is a synchronous sender callable that uses the Django ORM to store
            webhooks and the delivery log. Meant as proof of concept and not
            as something for heavy production sites.

        dkwargs argument requires the following key/values:

            :event: A string representing an event.

        kwargs argument requires the following key/values

            :owner: The user who created/owns the event
    """

    if "event" not in dkwargs:
        msg = "webhooks.django.decorators.hook requires an 'event' argument."
        raise TypeError(msg)
    event = dkwargs['event']

    if "owner" not in kwargs:
        msg = "webhooks.django.senders.orm.sender requires an 'owner' argument."
        raise TypeError(msg)
    owner = kwargs['owner']

    senderobj = DjangoSenderable(
            wrapped, dkwargs, hash_value, WEBHOOK_ATTEMPTS, *args, **kwargs
    )

    # Add the webhook object just so it's around
    # TODO - error handling if this can't be found
    senderobj.webhook_target = WebhookTarget.objects.get(event=event, owner=owner)

    # Get the target url and add it
    senderobj.url = senderobj.webhook_target.target_url

    # Get the payload. This overides the senderobj.payload property.
    senderobj.payload = senderobj.get_payload()

    # Get the creator and add it to the payload.
    senderobj.payload['owner'] = getattr(kwargs['owner'], WEBHOOK_OWNER_FIELD)

    # get the event and add it to the payload
    senderobj.payload['event'] = dkwargs['event']

    return senderobj.send()

sender.doc = """djwebhooks.senders.orm.sender
Decorator for 'hooking' a payload request to a foreign URL using
`djwebhooks.senders.orm.sender`. A payload request is generated by the hooked
function, which must return a JSON-serialized value.

Note: Thanks to json232, the JSON-serialized data can include DateTime objects.

    :event: The name of the event as defined in settings.WEBHOOK_EVENTS
    :owner: Required for the payload function. This represents the user who
        created or manages the event. Is not normally request.user.

Decorator Usage:

    # Define the payload function!
    @hook(event="order.ship")
    def order_ship(order, owner):
        return {
            "order_num": order.order_num,
            "shipping_address": order.shipping_address,
            "line_items": [x.sku for x in order.lineitem_set.all()]
        }

    # Call the payload function!
    def order_confirmation(request, order_num):
        order = get_object_or_404(Order, order_num=order_num)
        if order.is_valid():
            order_ship(order=order, owner=order.merchant)

        return redirect("home")

"""
