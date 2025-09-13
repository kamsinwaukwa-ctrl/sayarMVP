API Keys
To enable communication between your application and Korapay, you'll need your API Keys. Kora authenticates every request your application makes with these keys. Generally, every account comes with two sets of API keys - public and secret API keys for Test and Live modes.

Your public keys are non-sensitive identifiers that can be used on the client-side of your application. By design, public keys cannot modify any part of your account besides initiating transactions for you. Your secret keys, on the other hand, are to be kept secret and confidential. They are required for accessing any financial data and can be used to make any API call on your account. Your secret keys should never be shared on any client-side code. Treat them like any other password. And, if for any reason you believe your secret key has been compromised simply reset them by generating new keys. You can generate new API keys from your dashboard.

Obtaining your API Keys
Your API keys are always available on your dashboard. To find your API keys,

Login to your dashboard.
Navigate to Settings on the side menu.
Go to the API Configuration tab on the Settings page.
In the Korapay APIs section, you’d see both your Public and Secret keys, and a button to Generate New API Keys.
🚧
The API keys in test mode are different from the API keys in Live mode. So you need to always ensure that you do not misuse the keys when you switch between modes.

Generating new API Keys
You should always keep your API keys safe and protect your account. However, in the event where your API keys have been compromised, you can easily generate new API keys. Simply click the 'Generate New API Keys' button under the API Configuration tab on the Settings page.


Once you generate new API keys, the old keys become void - you can no longer use them to make API calls. Make sure to update your application to use the newly generated keys.


Testing your Integration
It is important to test your integration before going live to make sure it works properly. That’s why we created test bank accounts, mobile money numbers and test cards for you to simulate different payment scenarios as you integrate with Kora.

Testing Payouts to Bank Accounts
Use the following bank accounts to test these scenarios for your Bank Transfer payout integration:

Scenario	Currency	Bank Code	Account Number
Successful Payout	NGN	033	0000000000
Failed Payout	NGN	035	0000000000
Error: Invalid Account	NGN	011	9999999999
Successful Payout	KES	0068	000000000000
Failed Payout	KES	0053	000000000000
Testing Payouts to Mobile Money
Use the following mobile money details to test these scenarios for your Mobile Money payout integration:

Scenario	Currency	Mobile Money Operator	Mobile Number
Successful Payout	KES	safaricom-ke	254711111111
Failed Payout	KES	airtel-ke	254722222222
Successful Payout	GHS	airtel-gh	233242426222
Failed Payout	GHS	mtn-gh	233722222222
Testing Pay-in Mobile Money
Use the following mobile money numbers to test different scenarios for your Mobile Money pay-in integration:

Scenario	Mobile Number	Currency	OTP	PIN
Successful Payment	254700000000	KES	N/A	1234
Failed Payment	254734611986	KES	N/A	1234
Successful Payment	233240000000	GHS	123456	1234
Failed Payment	233274611986	GHS	123456	1234
Test Cards
Real payment cards would not work in Test mode. If you need to test your card payment integration, you can use any of the following test cards:

For Successful Payment (No Authentication) - Visa
Card Number: 4084 1278 8317 2787
Expiry Date: 09/30
CVV: 123

For Successful Payment (with PIN) - Mastercard
Card Number: 5188 5136 1855 2975
Expiry Date: 09/30
CVV: 123
PIN: 1234

For Successful Payment (with OTP) - Mastercard
Card Number: 5442 0561 0607 2595
Expiry Date: 09/30
CVV: 123
PIN: 1234
OTP: 123456

For Successful Payment (with 3D Secure) - Visa
Card Number: 4562 5437 5547 4674
Expiry Date: 09/30
CVV: 123
OTP: 1234

Successful (with Address Verification Service, AVS) - Mastercard
Card Number: 5384 0639 2893 2071
Expiry Date: 09/30
CVV: 123
PIN: 1234

For Address
City: Lekki
Address: Osapa, Lekki
State: Lagos
Country: Nigeria
Zip Code: 101010

Successful (with Card Enroll) - Verve
Card Number: 5061 4604 1012 0223 210
Expiry Date: 09/30
CVV: 123
PIN: 1234
OTP: 123456

For Failed Payment (Insufficient Funds) - Verve
Card Number: 5060 6650 6066 5060 67
Expiry Date: 09/30
CVV: 408

To simplify testing your card integrations in Test mode, we already created these scenarios on the test Checkout and prefilled the card details for each scenario.


🚧
It is important to note that, just as real payment instruments do not work in Test mode, test cards and bank accounts cannot be used in Live mode or for real payments.

Testing Identity
To test identity verification scenarios on the sandbox environment, the test data below should be used:

For Kenya

Document Type	Scenario	ID Number
International Passport	Valid	A2011111
International Passport	Invalid	A0000000
National ID	Valid	25219766
National ID	Invalid	00000000
Tax PIN	Valid	A009274635J
Tax PIN	Invalid	A0000000000
Phone Number	Valid	0723818211

For Ghana

Document Type	Scenario	ID Number
SSNIT	Valid	C987464748977
SSNIT	Invalid	C000000000000
Driver's License	Valid	070667
Driver's License	Invalid	000000
International Passport	Valid	G0000555
International Passport	Invalid	G0000000
Voters Card	Valid	9001330422
Voters Card	Invalid	0000000000

For Nigeria

Document Type	Scenario	ID Number
BVN	Valid	22222222222
BVN	Invalid	00000000000
vNIN	Valid	KO111111111111IL
vNIN	Invalid	KO000000000000II
NIN	Valid	55555555555
NIN	Invalid	00000000000
International Passport	Valid	A01234567
International Passport	Invalid	A00000000
Voters Card (PVC)	Valid	00A0A0A000000000011
Voters Card (PVC)	Invalid	11A1A1A111111111111
Phone Number	Valid	08000000000
Phone Number	Invalid	08000000001
CAC (RC Number)	Valid	RC00000011
CAC (RC Number)	Invalid	RC11111111

For South Africa

Document Type	Scenario	ID Number
SAID	Valid	8012185201077
SAID	Invalid	8000000000001


Webhooks
Webhooks provide a way to receive notifications for your transactions in real time. While your transaction is being processed, its status progresses until it is completed. This makes it very important to get the final status for that transaction, and that's where webhooks are very beneficial.

Put simply, a webhook URL is an endpoint on your server that can receive API requests from Korapay’s server. Note that the request is going to be an HTTP POST request.

Setting your Webhook URL
You can specify your webhook URL in the API Configuration tab of the Settings page of your dashboard. Make sure that the webhook URL is unauthenticated and publicly available.


The request to the webhook URL comes with a payload, and this payload contains the details of the transaction for which you are being notified.

Webhook Notification Request Payload Definitions
Field	Data Type	Description
event	String	transfer.success, transfer.failed, charge.success or charge.failed, refund.success, refund.failed
data	Object	The object containing transaction details: amount, fee, currency, status, reference
data.amount	Number	Transaction amount
data.fee	Number	Transaction fee
data.currency	String	Transaction currency
data.status	String	Transaction status. This can be success or failed.
data.reference	String	Transaction reference. This reference can be used to query the transaction

Sample Webhook Notification Payloads
Single Payout
Bulk Payout
Pay-in (NG Virtual Bank Account)
Pay-in (Cards, Bank Transfer, Mobile Money)
Refunds

/*
* Applicable Events: "transfer.success", "transfer.failed"
*/
{
  "event": "transfer.success",
  "data": {
    "fee": 15,
    "amount": 150.99,
    "status": "success",
    "currency": "NGN",
    "reference": "Z78EYMAUBQ5"
  }
}

Verifying a Webhook Request
It is important to verify that requests are coming from Korapay to avoid delivering value based on a counterfeit request. To verify our requests, you need to validate the signature assigned to the request.
Valid requests are sent with a header x-korapay-signature which is essentially an HMAC SHA256 signature of ONLY the data object in response payload signed using your secret key.

JavaScript
Java
PHP

const crypto = require(“crypto”);
const secretKey = sk_live_******

router.post(‘/your_webhook_url’, (req, res, next) => {
  const hash = crypto.createHmac('sha256', secretKey).update(JSON.stringify(req.body.data)).digest('hex');

   If (hash === req.headers[‘x-korapay-signature’]) {
     // Continue with the request functionality
   } else {
     // Don’t do anything, the request is not from us.
   }
});
Responding to a Webhook Request
It is important to respond to the requests with a 200 status code to acknowledge that you have received the requests. Korapay does not pay attention to any request parameters apart from the request status code.

Please note that if any other response code is received, or there’s a timeout while sending the request, we retry the request periodically within 72 hours after which retries stop.

Resending a Webhook via the Kora Dashboard
For every transaction, Kora sends a webhook notification to the merchant’s configured webhook URL. If the transaction status is Pending/Failed, the ‘Resend Webhook’ button becomes activated on the dashboard, allowing you to manually trigger the webhook notification again.

Conditions for Resending Webhooks
For Payouts

When channel is api and status is successful or failed.
For Pay-ins

When channel is api and status is successful or failed.
When channel is modal and status is successful.
How to Resend a Webhook Notification on a Transaction
On your Kora Dashboard, navigate to the Webhook / Metadata section of the transaction's detail.
Locate the webhook notification for the transaction in question.
If the status is Pending/Failed, the Resend Webhook button will be displayed in the top-right corner.
Click the Resend Webhook button to manually trigger a new webhook notification. Be sure that you need to resend the webhook to avoid duplicate transactions on your end.
The webhook request will be reattempted and the updated status can be reviewed in the dashboard.

Best Practices
It is recommended to do the following when receiving webhook notifications from us:

Keep track of all notifications received: It’s important to keep track of all notifications you’ve received. When a new notification is received proceed to check that this has not been processed before giving value. A retry of already processed notifications can happen if we do not get a 200 HTTP Status code from your notification URL, or if there was a request time out.
Acknowledge receipt of notifications with a 200 HTTP status code: It’s recommended you immediately acknowledge receipt of the notification by returning a 200 HTTP Status code before proceeding to perform other logics, failure to do so might result in a timeout which would trigger a retry of such notification.

Errors
The possible errors returned from Korapay’s API can be grouped into three main categories - General errors, Payout errors, Pay-in errors, and Refund errors.

General Errors
Internal Server Error
This response does not indicate any error with your request, so you can requery the transaction to get a final status or you can report this to us.

Invalid authorization key
This response does not indicate any error with your request. Requery the transaction to get the final status.

Invalid request data
This error occurs when the request is sent with invalid data, more details of the error can be found in the data object which is also sent back as a response. Try the request again once the errors returned in the data object is resolved.

Pay-In Errors
Charge not found
This error occurs when the deposit order ID sent in the request does not exist on our system. This can be treated as a failed transaction.

Duplicate payment reference
This error occurs when the reference sent in the request has already been used for a previous transaction.

*You can see more specific API errors under the guide for each pay-in type.

Payout Errors
Errors that occur before the Payout is initiated
Unable to resolve bank account.
This error occurs when our system is unable to successfully validate a customer’s bank account to determine if it’s valid or not. This can be treated as a failed withdrawal. There would be no need to query for a final status as the withdrawal would not exist on our system. Querying the withdrawal will return the error “Transaction not found”.

Transaction not found
This error occurs when the withdraw order ID attached to the request does not exist on our system. This can be treated as a failed transaction

Invalid account.
This error occurs when the bank account details provided for a withdrawal is not valid. This can be treated as a failed transaction. There would be no need to query for a final status as the transaction would not exist on our system. Querying the withdrawal will return the error “Transaction not found”.

Invalid bank provided.
This error occurs when the destination bank provided for withdrawal is not supported on our system or the bank code is invalid. This can be treated as a failed transaction. There would be no need to query for a final status as the transaction would not exist on our system. Querying the withdrawal will return the error “Transaction not found”

Invalid mobile money operator.
This error occurs when the mobile money operator provided for mobile money payout is not supported on our system or the operator code is invalid. This can be treated as a failed transaction. There would be no need to query for a final status as the transaction would not exist on our system. Querying the withdrawal will return the error “Transaction not found”

Insufficient funds in disbursement wallet
This error occurs when the funds available in your wallet is not enough to process a withdrawal request. This can be treated as a failed withdrawal. Try the request again with a new order ID once funds have been added to your wallet.

Duplicate Transaction Reference. Please use a unique reference
This error occurs when the reference sent in the request has already been used for a previous transaction.

Reasons a Payout could fail after it is initiated
After a payout is initiated, it is possible to get any of the following error responses when you query the transaction using the payment reference.

Insufficient funds in disbursement wallet
This means that the funds available in your merchant wallet are not enough to process the transaction. Try the request again with a new order ID once funds have been added to your wallet

Dormant account
This means that the destination bank account details provided has been marked as dormant by the destination bank and is unable to accept payments for that purpose. Try the request again with a new reference and bank details or have the customer reach out to their bank for further assistance.

Timeout waiting for response from destination
This means that the destination bank did not respond on time. Have the customer try again at a later time or with a different bank.

Destination bank is not available
This means that the destination bank could not be contacted. Have the customer try again at a later time or with a different bank.

Payout terminated due to suspected fraud
This means that the transaction was flagged as fraudulent.

Do not honor
This means that the bank declined the transaction for reasons best known to them, or when a restriction has been placed on a customer’s account. Try the request again at a later time with a new reference or have the customer provide a different bank.

If the problem persists, please advise the customer to contact their bank.

Payout limit exceeded
This means that the transaction being attempted will bring the customer's bank balance above the maximum limit set by their bank or that they have exceeded their limit for that day. Try the request again with a new reference or have the customer provide a different bank.

Unable to complete this transaction
This means the transaction could not be completed successfully due to downtime with the payment switch as of when the transaction was attempted. Try the request again with a new reference at a later time.

Invalid transaction
This is an error from the payment switch. Try the request again with a new reference.

Payout failed
This means the transaction could not be completed successfully for some unknown reason. Try the request again with a new reference

Refund Initiation Errors
Transaction has not yet been settled
This means that the transaction you are attempting to refund has not yet been settled to your balance. Until the transaction is settled, funds cannot be reversed. Please attempt the refund again after the expected settlement date.

Refund can only be requested on a successful transaction
This means that the original transactions wasn't processed successfully. You can only request a refund for a transaction that was successfully processed.

Transaction not found
This error occurs when the transaction reference submitted for the refund does not exist on our system. This can be treated as a failed refund.

Refund already exists with reference **reference submitted**
This error occurs when the reference sent in the request has already been used for a previously initiated refund. Please attempt the refund again with a different reference.

Refund not supported for this currency, please contact support
This error occurs when refund is not supported for the transaction currency. Please get in touch with our support team. They'll be able to guide on how to proceed.

Refund amount cannot be more than **{currency} {transactionAmountCollected}**
This means that the refund amount provided exceeds the value of the original successful transaction amount. Please update the refund amount you are trying to process and try again

Refund amount cannot be less than **{currency} {minimumRefundAmount}**
This means that the refund amount specified is below the minimum allowed value for processing. The system enforces a minimum refund amount for the currencies supported as shown here. Please get in touch with our support team if you need this reviewed

A full reversal has already been processed for this transaction
This means that a reversal equivalent to the original transaction amount has already been successfully initiated. Please verify the details of the reversal(s) on the transaction details page of the dashboard

A full refund cannot be initiated for this transaction. Please enter an amount less than or equal to **{currency} {transactionAmountCollected}**
This error occurs when no refund amount is passed in the request and the system tries to process a full refund but the total remaining refundable amount for the transaction is less than amount collected. To resolve this, please enter the specific amount you wish to refund. This amount must be less or equal to the amount left to be refunded.

The maximum refundable amount for this transaction is **{currency} {transactionAmountCollected minus amountAlreadyReversed}**
This error occurs when the amount requested to be refunded is more than the maximum refundable amount. To resolve this, please enter the specific amount you wish to refund. This amount must be less or equal to the amount left to be refunded.

Insufficient funds in disbursement wallet
This error occurs when the funds available in your wallet is not enough to process a refund request. This can be treated as a failed refund. Try the request again with the same refund reference once funds have been added to your wallet.

Checkout Standard
Checkout Standard provides a simplified and secure flow for collecting payments from customers. It's easy to integrate.

Integrating the Checkout Standard
We'll use examples to show you how to integrate Kora's payment gateway using the Checkout Standard into your product. Feel free to make the necessary adjustments you need to provide a customized experience on your product. In our first example, we'll be using a simple "Pay" button that should load Checkout Standard on a webpage.

Let's get started:

1 - Get your API Keys
Obtain your API Keys from your dashboard. We recommend you integrate using your test keys to avoid changes to your live data or charging real customers while testing.

2 - Add the pay-ins/collections script
Next, you'll need to add the Kora pay-in/collection script to your website or application.

Sample Form

<form>
    <script src="https://korablobstorage.blob.core.windows.net/modal-bucket/korapay-collections.min.js"></script>
    <button type="button" onclick="payKorapay()"> Pay </button>
</form>
Pay-in Script

<script>
    function payKorapay() {
        window.Korapay.initialize({
            key: "pk_live_*********************",
            reference: "your-unique-reference",
            amount: 22000, 
            currency: "NGN",
            customer: {
              name: "John Doe",
              email: "john@doe.com"
            },
            notification_url: "https://example.com/webhook"
        });
    }
</script>
🚧
Warning!
Avoid exposing your secret key on the client-side (or front end) of your application. Requests to the Kora's API should be initiated from your server.

3 - Initialize the payment gateway.
Use the Korapay.initialize function to pass the relevant transaction details needed to initialize the payment gateway and start accepting payments.

Set the sample API key with your test mode key obtained from your dashboard. This allows you to test through your Korapay account.

Indicate the amount and currency.

Indicate the customer name and email to show on the gateway as the sender of the transaction.

When you’re ready to accept live payments, replace the test key with your live/production key.

4 - Receive confirmation via webhook
When the payment is successful, we will make a POST request to your webhook URL (as set up in your dashboard, or while initializing the transaction using the key: notification_url) in this format:

Code: Response Format

{
   "even"t:  "charge.success" //the notification is only sent for successful charge,
   "data": {
     	"reference": "KPY-C-cUBkIH&98n8b",
     	"currency": "NGN",
     	"amount": "22000", //amount paid by the customer
     	"amount_expected": "22000", //amount that the customer is expected to pay
     	"fee": "25",
     	"status": "success",
     	"payment_reference": "your-unique-reference", //unique reference sent by the merchant
     	"transaction_status": "success" //the status of the charge base on the amount paid by the customer. This can either be `success`, `underpaid` or `overpaid`,
      "metadata": {
        "internalRef": "JD-12-67",
        "age": 15,
        "fixed": true,
      }
   }
}
Configuration parameters
Field

Data Type

Description

key

String

*Required** - Your public key from Korapay. Use the test public key for test transactions and live public key for live transactions
reference

String

*Required** - Your unique transaction reference. Must be unique for every transaction.
amount

Integer

*Required** - Amount to be collected.
currency

String

*Optional** - Currency of the charge, e.g NGN, KES, GHS. The default is NGN (Nigerian Naira)
customer

Object

*Required** - JSON object containing customer details
customer.name

String

*Required **- field in the customer object. Customer name derived from name enquiry.
customer.email

String

*Required** - Field in the customer object. Customer email address
notification_url

String

*Optional** - HTTPS endpoint to send information to on payment termination, success, or failure. This overrides the webhook URL set on your merchant dashboard for this particular transaction
narration

String

*Optional** - Information/narration about the transaction
channels

Array[string]

*Optional** - Methods of payment. E.g, Bank Transfer (bank_transfer), card (card), Pay with Bank (pay_with_bank), Mobile money (mobile_money). Default is [“bank_transfer”][“bank_transfer”]. Note that if only one payment method is available, it cannot be changed to another method.
default_channel

String

*Optional** - Method of payment that should be active by default. E.g Bank Transfer (bank_transfer), card (card), Pay with Bank (pay_with_bank), Mobile money (mobile_money. The payment method selection page is skipped on the first load.
Note that the default channel must also be specified in the channels parameter.

metadata

Object

*Optional** - It takes a JSON object with a maximum of 5 fields/keys. Empty JSON objects are not allowed.
Each field name has a maximum length of 20 characters. Allowed characters: A-Z, a-z, 0-9, and -.

containerId

String

*Optional** - ID of the HTML element you want the payment gateway to be contained in. Note that this would reset all styling on this element. The payment gateway would be resized to fit the container. If this is not set, the payment gateway fills the available screen size.
The recommended size for this container is 400px x 500px (width x height). However, this is not enforced and you can load the checkout in a smaller or larger container.

onClose

[Function]

*Optional** - function to be called when the payment gateway is closed
onSuccess

[Function]

*Optional** - function to be called when the payment is completed successfully
onFailed

[Function]

*Optional** - function to be called when the payment failed
onTokenized

[Function]

Optional - function to be called when card tokenization is completed successfully

onPending

[Function]

*Optional** - sometimes, bank transfers could take some time before they get resolved. In such a case, this function would be called after 20 seconds. This could allow you to manage the experience for your customer by showing a notification or some other information.
merchant_bears_cost

Boolean

*Optional**. This will set who bears the fees of the transaction. If it is set to true, the merchant will bear the fee, while if it is set to false, the customer will bear the fee. By default, it is set to true.
Interacting with Checkout Standard through the Korapay script
When using Checkout Standard, the payment gateway is opened in an iframe to ensure security. Some functions are exposed to allow interactions with the application when specific events occur during a transaction. These include:

Event	Field
Succesful Transaction	onSuccess
Failed Transaction	onFailed
Payment Modal Closed	onClose
Card Tokenized	onTokenized
Bank Transfer Pending	onPending
You can pass functions into these fields while calling Korapay.initialize as shown in the script below.

Code: Script

<script>
    function payKorapay() {
        window.Korapay.initialize({
            key: "pk_juigfweofyfewby732gwo8923e",
            reference: "your-unique-reference",
            amount: 3000, 
            currency: "NGN",
            customer: {
              name: "John Doe",
              email: "john@doe.com"
            },
            onClose: function () {
              // Handle when modal is closed
            },
            onSuccess: function (data) {
              // Handle when payment is successful
            },
            onFailed: function (data) {
              // Handle when payment fails
            }
            ...
        });
    }
</script>
The data returned should have the following fields. Note that no data is returned for the onPending function as the transaction is not yet completed:

Field	Data Type	Description
amount	String	Transaction Amount
reference	String	Transaction Reference
status	String	Transaction Status
To close the modal programmatically, use the Korapay.close function.

