import stripe
from django.conf import settings

from airport.models import Order
from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment(order: Order, session: stripe.checkout.Session):
    Payment.objects.create(
        status="PENDING",
        order=order,
        session_url=session.url,
        session_id=session.id,
        amount=session.amount_total / 100,
    )


def create_stripe_session(order: Order) -> stripe.checkout.Session:
    amount = order.route_name.distance * order.tickets.count() * 10

    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": order.route_name,
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url="http://127.0.0.1:8000/api/payments/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="http://127.0.0.1:8000/api/cancel",
    )

    create_payment(order, session)
    return session
