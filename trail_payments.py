import stripe
from trail_db import get_user_email

class PaymentHandler:
    def __init__(self, stripe_secret_key):
        stripe.api_key = stripe_secret_key
        # Replace with your actual Render URL
        self.success_url = "https://union-app.onrender.com/success?session_id={CHECKOUT_SESSION_ID}"
        self.cancel_url = "https://union-app.onrender.com"

    def create_subscription(self, username, price_id="price_12345"):
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                customer_email=get_user_email(username),
            )
            return session.url, None
        except stripe.error.StripeError as e:
            return None, f"Payment failed: {str(e)}"