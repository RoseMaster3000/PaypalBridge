# https://developer.paypal.com/api/rest/
# https://github.com/paypal/PayPal-Python-Server-SDK
# https://github.com/Traktormaster/paypal2


def send_money(recipient_email, amount):
    print("Sending paypal money... (todo)")
    return True


# import paypalrestsdk
# from datetime import datetime
# def send_money_paypal(sender_client_id, sender_secret, recipient_email, amount):
#     """
#     Send money via PayPal using the REST API.

#     Args:
#         sender_client_id (str): Your PayPal client ID
#         sender_secret (str): Your PayPal secret
#         recipient_email (str): Recipient's PayPal email address
#         amount (float): Amount to send in USD
#     """
#     # Configure the PayPal SDK
#     paypalrestsdk.configure({
#         "mode": "sandbox",  # Switch to "live" for production
#         "client_id": sender_client_id,
#         "client_secret": sender_secret
#     })

#     # Create a payout object
#     payout = paypalrestsdk.Payout({
#         "sender_batch_header": {
#             "sender_batch_id": f"Batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
#             "email_subject": "You have a payment"
#         },
#         "items": [{
#             "recipient_type": "EMAIL",
#             "amount": {
#                 "value": str(amount),
#                 "currency": "USD"
#             },
#             "receiver": recipient_email,
#             "note": "Payment transfer",
#             "sender_item_id": f"Transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         }]
#     })

#     try:
#         if payout.create():
#             print(f"Successfully sent ${amount} to {recipient_email}")
#             print(f"Payout ID: {payout.batch_header.payout_batch_id}")
#             return True
#         else:
#             print(f"Failed to send payment: {payout.error}")
#             return False
#     except Exception as e:
#         print(f"Error occurred: {str(e)}")
#         return False

# # Example usage:
# if __name__ == "__main__":
#     # Replace these with your actual credentials and recipient details
#     PAYPAL_CLIENT_ID = "your_client_id_here"
#     PAYPAL_SECRET = "your_secret_here"
#     RECIPIENT_EMAIL = "recipient@example.com"
#     AMOUNT = 1.00

#     send_money(PAYPAL_CLIENT_ID, PAYPAL_SECRET, RECIPIENT_EMAIL, AMOUNT)