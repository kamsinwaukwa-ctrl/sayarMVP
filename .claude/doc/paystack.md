Introduction
Learn how to integrate our APIs into your application.

API Basics
Before you begin!
You should create a free Paystack account that you can test the API against. We will provide you with test keys that you can use to make API calls.

The Paystack API gives you access to pretty much all the features you can use on our dashboard and lets you extend them for use in your application. It strives to be RESTful and is organized around the main resources you would be interacting with - with a few notable exceptions.

HTTP Methods
Method	Type	Description
POST	String	Creates a new resource on the server.
GET	String	Retrieves a representation of a resource.
PUT	String	Updates an existing resource or creates it if it doesn't exist.
DELETE	String	Deletes a specified resource.
Sample Requests
We provide sample API calls next to each method using cURL. All you need to do is insert your specific parameters, and you can test the calls from the command line. See this tutorial on using cURL with APIs.

You can also use Postman if you aren't familiar with cURL. Postman is an easy to use API development and testing platform. You can explore the Paystack Postman Collection to understand how our APIs work.

Requests and Responses
Both request body data and response data are formatted as JSON. Content type for responses will always be application/json. Generally, all responses will be in the following format:

Keys
status
Boolean
This lets you know if your request was succesful or not. We recommend that you use this in combination with HTTP status codes to determine the result of an API call.
message
String
This is a summary of the response and its status. For instance when trying to retrieve a list of customers, message might read “Customers retrieved”. In the event of an error, the message key will contain a description of the error as with the authorization header situation above. This is the only key that is universal across requests.
data
Object
This contain the results of your request. It can either be an object, or an array depending on the request made. For instance, a request to retrieve a single customer will return a customer object in the data key, while the key would be an array of customers if a list is requested instead.
Response Format
{
  "status": "[boolean]",
  "message": "[string]",
  "data": "[object]"
}
Meta Object
The meta key is used to provide context for the contents of the data key. For instance, if a list of transactions performed by a customer is being retrieved, pagination parameters can be passed along to limit the result set. The meta key will then contain an object with the following attributes:

Keys
total
Number
This is the total number of transactions that were performed by the customer.
skipped
Number
This is the number of records skipped before the first record in the array returned.
perPage
Number
This is the maximum number of records that will be returned per request. This can be modified by passing a new value as a perPage query parameter. Default: 50
page
Number
This is the current page being returned. This is dependent on what page was requested using the page query parameter. Default: 1
pageCount
Number
This is how many pages in total are available for retrieval considering the maximum records per page specified. For context, if there are 51 records and perPage is left at its default value, pageCount will have a value of 2.
Meta Key Structure
{
  "meta": {
    "total": 2,
    "skipped": 0,
    "perPage": 50,
    "page": 1,
    "pageCount": 1
  }
}
Supported Currency
Paystack makes use of the ISO 4217 format for currency codes. When sending an amount, it must be sent in the subunit of that currency.

Sending an amount in subunits simply means multiplying the base amount by 100. For example, if a customer is supposed to make a payment of NGN 100, you would send 10000 = 100 * 100 in your request.

XOF subunit and fractions
While there is no subunit for XOF, developers must multiply the amount by 100 regardless. This doesn't imply that the amount can have a fractional part. If we notice a fractional part during processing, we ignore the fractional part.

Currency code	Subunit	Description	Transaction minimum
NGN	Kobo	Nigerian Naira	₦ 50.00
USD	Cent	US Dollar	$ 2.00
GHS	Pesewa	Ghanaian Cedi	₵ 0.10
ZAR	Cent	South African Rand	R 1.00
KES	Cent	Kenyan Shilling	Ksh. 3.00
XOF	-	West African CFA Franc	XOF 1.00


Authentication
Authenticate your API calls by including your secret key in the Authorization header of every request you make. You can manage your API keys from the dashboard

Generally, we provide both public and secret keys. Public keys are meant to be used from your front-end when integrating using Paystack Inline and in our Mobile SDKs only. By design, public keys cannot modify any part of your account besides initiating transactions to you. The secret keys however, are to be kept secret. If for any reason you believe your secret key has been compromised or you wish to reset them, you can do so from the dashboard.

Secure your secret key
Do not commit your secret keys to git, or use them in client-side code.

Authorization headers should be in the following format: Authorization: Bearer SECRET_KEY

Sample Authorization Header
Authorization: Bearer sk_test_r3m3mb3r2pu70nasm1l3

API requests made without authentication will fail with the status code 401: Unauthorized. All API requests must be made over HTTPS.

Secure your requests
Do not set VERIFY_PEER to FALSE. Ensure your server verifies the SSL connection to Paystack.

Pagination
Pagination allows you to efficiently retrieve large sets of data from the Paystack API. Instead of returning all results at once, which, could slow and resource intensive, pagination breaks the sets of data into smaller chunks before sending them. This approach improves performance, reduces network load, and enhances the overall user experience when working with large datasets.

Pagination Types
The Paystack API supports two types of pagination:

Offset Pagination
Cursor Pagination
Each type has its own use cases and implementation details.

Offset Pagination
Offset pagination allows you to request specific page and perPage values when fetching records. The page parameter specifies which page of records to retrieve, while the perPage parameter specifies how many records you want to retrieve per page.

To use offset pagination, include the page and perPage parameters as query parameters in your API request:

Query Parameters
page
Number
The page to retrieve
perPage
Number
This specifies the number of records to return per request. Default: 50
Additional Meta Parameter
The meta object in the JSON response from GET /transaction includes a total_volume parameter, which is the sum of all the transactions that have been fetched.

GET
/transaction?page=1&perPage=50

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction?page=1&perPage=50"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Offset Pagination Metadata
{
  "meta": {
    "total": 7316,
    "total_volume": 397800,
    "skipped": 0,
    "perPage": 50,
    "page": 1,
    "pageCount": 147
  }
}
Cursor Pagination
Cursor pagination uses a unique identifier called a cursor to keep track of where in the dataset to continue from. This method is more efficient for retrieving large datasets and provides more consistent results when items are being added or removed frequently.

To use cursor pagination, include the use_cursor query parameter and set it to true on your first fetch request. The meta object in the JSON response will contain a parameter called next that contains the cursor for the next set of records, and a previous parameter for the previous page. Include these as query parameters in subsequent requests to fetch the next or previous set of data.

Query Parameters
use_cursor
Boolean
Set this to true to retrieve results using cursor pagination
next
String
A cursor to use in pagination, next points to the next page of the dataset. Set this to the next cursor received in the meta object of a previous request.
previous
String
A cursor to use in pagination, previous previous page of the dataset. Set this to the previous cursor received in the meta object of a previous request.
perPage
Number
The number of records to return per request. Default: 50
Cursor Pagination Availability
Cursor-based pagination is currently only available on the following endpoints:

Transactions
Customers
Dedicated Accounts
Transfer Recipient
Transfers
Disputes
GET
/transaction?use_cursor=true&perPage=50

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction?use_cursor=true&perPage=50"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Cursor Pagination Metadata
{
  "meta": {
    "next": "dW5kZWZpbmVkOjQwOTczNTgxNTg=",
    "previous": "null",
    "perPage": 49
  }
}
Best Practices
Choose the Right Pagination Type: Use offset-based pagination for smaller, static datasets. For larger or frequently updated datasets, prefer cursor-based pagination.
Set Reasonable Page Sizes: Start with the default of 50 items per page. Adjust based on your specific needs, but avoid requesting too many items at once more than 1000 items at once to prevent performance issues.
Handle Edge Cases: Always check if there are more pages available. For offset-based pagination, it’s best to fetch pages until no results are returned. For cursor-based pagination, the absence of a next cursor indicates you've reached the end.
Implement Error Handling: Be prepared to handle pagination-related errors, such as invalid page numbers or cursors.
Consider Rate Limits: Be mindful of Paystack's rate limits when implementing pagination, especially if you're fetching large amounts of data. Implement appropriate delays between requests if necessary.
Cache Wisely: If you're caching paginated results, ensure your cache invalidation strategy accounts for potential changes in the dataset.
By following these best practices, you'll be able to efficiently work with large datasets in the Paystack API while providing a smooth experience for your users.

Errors
Paystack's API is RESTful and as such, uses conventional HTTP response codes to indicate the success or failure of requests.

HTTP Codes
200
Request was successful and intended action was carried out. Note that we will always send a 200 if a charge or verify request was made. Do check the data object to know how the charge went (i.e. successful or failed).
201
A resource has successfully been created.
400
A validation or client side error occurred and the request was not fulfilled.
401
The request was not authorized. This can be triggered by passing an invalid secret key in the authorization header or the lack of one.
404
Request could not be fulfilled as the request resource does not exist.
5xx
Request could not be fulfilled due to an error on Paystack's end. This shouldn't happen so please report as soon as you encounter any instance of this.
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Charge attempted",
  "data": {
    "amount": 200,
    "currency": "NGN",
    "transaction_date": "2017-05-24T05:56:12.000Z",
    "status": "success",
    "reference": "zuvbpizfcf2fs7y",
    "domain": "test",
    "metadata": {
      "custom_fields": [
        {
          "display_name": "Merchant name",
          "variable_name": "merchant_name",
          "value": "Van Damme"
        },
        {
          "display_name": "Paid Via",
          "variable_name": "paid_via",
          "value": "API call"
        }
      ]
    },
    "gateway_response": "Successful",
    "message": null,
    "channel": "card",
    "ip_address": "54.154.89.28, 162.158.38.82, 172.31.38.35",
    "log": null,
    "fees": 3,
    "authorization": {
      "authorization_code": "AUTH_6tmt288t0o",
      "bin": "408408",
      "last4": "4081",
      "exp_month": "12",
      "exp_year": "2020",
      "channel": "card",
      "card_type": "visa visa",
      "bank": "TEST BANK",
      "country_code": "NG",
      "brand": "visa",
      "reusable": true,
      "signature": "SIG_uSYN4fv1adlAuoij8QXh",
      "account_name": "BoJack Horseman"
    },
    "customer": {
      "id": 14571,
      "first_name": null,
      "last_name": null,
      "email": "test@email.co",
      "customer_code": "CUS_hns72vhhtos0f0k",
      "phone": null,
      "metadata": null,
      "risk_action": "default"
    },
    "plan": null
  }
}
Not sure where to look? Try search
Type the error or keywords into the search bar above. If you don’t find what you’re looking for, contact us, we’re happy to help.

Transactions
Transaction reference not found
Meaning: No transaction could be found with this transaction reference
Solution: Ensure that you're passing the reference of a transaction that exists on this integration
Merchant is not enabled for Partial Debit
Meaning: The Partial Debit service has not been enabled for this integration
Solution: You can send us an email at support@paystack.com to make a request for the service
There was an error checking this authorization. Try again.
Meaning: An unspecified error occurred while checking the authorization code supplied
Solution: Try again or try another authorization code
Oooops, your payment has exceeded the time to pay.
Meaning: The transaction was not made before the Payment Session Timeout had elapsed
Solution: Increase your Payment Session Timeout, or set it to 0 to remove the timeout completely
Duplicate charge request for reference
Meaning: You passed the same reference while trying to initialize a transaction using the Inline or Popup method
Solution: Generate and pass a new transaction reference for every transaction
Invalid character in transaction reference
Meaning: Your transaction reference includes an invalid character. Only -,., =and alphanumeric characters are allowed
Solution: Ensure that you aren't using any characters that aren't alphanumeric or contained in "-,., =" in your transaction reference
Transaction cannot be completed. Session timeout exceeded.
Meaning: The transaction was not completed in the time allowed by your session timeout
Solution: You'll need to initialize a new transaction. If you don't want your transactions to time out, you can increase your Session Timeout  or set it to 0 (no timeout)
Transaction amount limit exceeded
Meaning: The amount you tried to charge is higher than the maximum limit which is 10,000,000 (for all supported currencies)
Solution: You'll need to re-initialize the transaction with lower amount
Pay with transfer is not currently supported for transactions less than NGN 100.00
Meaning: The minimum amount for Pay with Transfers transactions is NGN 100
Solution: Ensure you're passing an amount greater than or equal to NGN 100 in Kobo
Invalid Merchant Selected
Meaning: You're attempting to start a transaction with the API key of a disabled business
Solution: If your business was disabled, you should have been sent an email detailing the reason this happened and how to reactivate your business. Send an email to support@paystack.com if you think this was done in error.
Transaction not found
Meaning: No transaction could be found with this transaction reference
Solution: Ensure that you've copied the transaction reference correctly. Also confirm that the API keys you're using, belong to the business you're searching the transaction reference for.
You must specify a valid amount
Meaning: You've attempted to initiate a transaction with amount set to zero
Solution: Ensure the amount is an integer greater than 0
Email is not allowed to be empty
Meaning: Email address is required when initializing a transaction
Solution: Pass the email to the transaction initialize API
Authorization code is invalid
Meaning: The authorization code for the transaction is not valid
Solution: Use a valid authorization code by generating a new one
Account number must be at least 6 digits in length
Meaning: The bank account number is less than the required minimum number.
Solution: Provide a correct account number when creating a new Subaccount
account_number is required
Meaning: The bank account number is not provided
Solution: Provide a correct account number when creating a new Subaccount
Invalid Amount Sent
Meaning: The amount provided for the transaction or transfer is not valid
Solution: Provide a valid amount based on the recommended minimum
Unable to process transaction
Meaning: This occurs when a customer's transaction is denied by Paystack's fraud system
Solution: The customer needs to escalate to Paystack either through the merchant or via our support channels.
Pickup card (stolen card)
Meaning: This means the customer's card has been reported as lost and a new card has been printed but the customer is yet to pick it up.
Solution: Please advise the customer to visit the bank and pickup their new card. In the meantime, the transaction can be completed using other payments options on the checkout
Invalid Authorization Code
Meaning: You are either passing an empty or wrong authorization code when charging a customer
Solution: Ensure your request doesn't contain an empty authorization. Also make sure you're using the right authorization code for the customer you're trying to charge
Invalid amount passed.
Meaning: You are either sending an empty string or a non-integer value as the amount of a transfer
Solution: You should ensure the length of amount is greater than zero and not a string value
Denied by fraud system
Meaning: The transaction is flagged as a suspicious one by our fraud system.
Solution: The customer should retry the transaction after 24 hours
Duplicate Transaction Reference
Meaning: This transaction reference has already been used on this integration
Solution: Ensure that you use a unique reference for every transaction. Alternatively, leave the reference field blank and we'll auto-generate one for you
Integration has been deactivated
Meaning: The business has been deactivated on Paystack and cannot process transactions any more.
Solution: The customer should reach out to the business and request they activate their integration on Paystack.
Pickup card (lost card)
Meaning: This card has been blocked by the bank cause the cardholder has reported it lost.
Solution: Advise your customer to reach out to their bank to get the block removed or return the card to the bank
at_least cannot be greater than amount
Meaning: The at_least value cannot be greater than the amount value.
Solution: Ensure that the value you're passing for at_least is less than the amount value. This occurs when using Partial Debit feature.
Transaction reference is invalid
Meaning: Incorrect transaction reference was given
Solution: Verify that the transaction reference is correct. Also ensure that this transaction exists on the integration whose API key you're using
Invalid Email Address Passed
Meaning: The email address is improperly formatted.
Solution: Ensure that the email follows the format: "username@example.com"
Declined
Meaning: The card has been blocked by the bank for this transaction.
Solution: Please ask your customer to reach out to their bank to find the reason why the transaction was blocked. You can also advise the customer to activate the card for online transactions.
Transaction ID should be numeric.
Meaning: The transaction ID contains non-numeric characters
Solution: Transaction IDs will always be numeric values. Verify that you're passing the transaction ID, and not reference
Expired card
Meaning: The card used has expired and you should get the customer's newest card details.
Solution: Please ask the customer to pay using a card that's valid.
Insufficient Funds
Meaning: The account tied to the card doesn't have enough to pay for the amount you're charging.
Solution: Please ask the customer to use a card that is well funded or to fund their account that's tied to the card.
Sample generic error
{
  "status": "false",
  "message": "[string]"
}
Not sure where to look? Try search
Type the error or keywords into the search bar above. If you don’t find what you’re looking for, contact us, we’re happy to help.

Transactions
The Transactions API allows you create and manage payments on your integration.

Initialize Transaction
Initialize a transaction from your backend

Headers
authorization
String
Set value to Bearer SECRET_KEY

content-type
String
Set value to application/json

Body Parameters
amount
String
Amount should be in the subunit of the supported currency

email
String
Customer's email address

currency
String
optional
The transaction currency. Defaults to your integration currency.

reference
String
optional
Unique transaction reference. Only -, ., = and alphanumeric characters allowed.

callback_url
String
optional
Fully qualified url, e.g. https://example.com/ . Use this to override the callback url provided on the dashboard for this transaction

plan
String
optional
If transaction is to create a subscription to a predefined plan, provide plan code here. This would invalidate the value provided in amount

invoice_limit
Integer
optional
Number of times to charge customer during subscription to plan

metadata
String
optional
Stringified JSON object of custom data. Kindly check the Metadata page for more information.

channels
Array
optional
An array of payment channels to control what channels you want to make available to the user to make a payment with. Available channels include: ["card", "bank", "apple_pay", "ussd", "qr", "mobile_money", "bank_transfer", "eft"]

split_code
String
optional
The split code of the transaction split. e.g. SPL_98WF13Eb3w

subaccount
String
optional
The code for the subaccount that owns the payment. e.g. ACCT_8f4s1eq7ml6rlzj

transaction_charge
Integer
optional
An amount used to override the split configuration for a single split payment. If set, the amount specified goes to the main account regardless of the split configuration.

bearer
String
optional
Use this param to indicate who bears the transaction charges. Allowed values are: account or subaccount (defaults to account).

POST
/transaction/initialize

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/initialize"
authorization="Authorization: Bearer YOUR_SECRET_KEY"
content_type="Content-Type: application/json"
data='{ 
  "email": "customer@email.com", 
  "amount": "20000"
}'

curl "$url" -H "$authorization" -H "$content_type" -d "$data" -X POST
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Authorization URL created",
  "data": {
    "authorization_url": "https://checkout.paystack.com/3ni8kdavz62431k",
    "access_code": "3ni8kdavz62431k",
    "reference": "re4lyvq3s3"
  }
}
Verify Transaction
Confirm the status of a transaction

Transaction ID data type
If you plan to store or make use of the the transaction ID, you should represent it as a unsigned 64-bit integer. To learn more, check out our changelog.

Headers
authorization
String
Set value to Bearer SECRET_KEY

Path Parameters
reference
String
The transaction reference used to intiate the transaction

GET
/transaction/verify/:reference

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/verify/{reference}"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Verification successful",
  "data": {
    "id": 4099260516,
    "domain": "test",
    "status": "success",
    "reference": "re4lyvq3s3",
    "receipt_number": null,
    "amount": 40333,
    "message": null,
    "gateway_response": "Successful",
    "paid_at": "2024-08-22T09:15:02.000Z",
    "created_at": "2024-08-22T09:14:24.000Z",
    "channel": "card",
    "currency": "NGN",
    "ip_address": "197.210.54.33",
    "metadata": "",
    "log": {
      "start_time": 1724318098,
      "time_spent": 4,
      "attempts": 1,
      "errors": 0,
      "success": true,
      "mobile": false,
      "input": [],
      "history": [
        {
          "type": "action",
          "message": "Attempted to pay with card",
          "time": 3
        },
        {
          "type": "success",
          "message": "Successfully paid with card",
          "time": 4
        }
      ]
    },
    "fees": 10283,
    "fees_split": null,
    "authorization": {
      "authorization_code": "AUTH_uh8bcl3zbn",
      "bin": "408408",
      "last4": "4081",
      "exp_month": "12",
      "exp_year": "2030",
      "channel": "card",
      "card_type": "visa ",
      "bank": "TEST BANK",
      "country_code": "NG",
      "brand": "visa",
      "reusable": true,
      "signature": "SIG_yEXu7dLBeqG0kU7g95Ke",
      "account_name": null
    },
    "customer": {
      "id": 181873746,
      "first_name": null,
      "last_name": null,
      "email": "demo@test.com",
      "customer_code": "CUS_1rkzaqsv4rrhqo6",
      "phone": null,
      "metadata": null,
      "risk_action": "default",
      "international_format_phone": null
    },
    "plan": null,
    "split": {},
    "order_id": null,
    "paidAt": "2024-08-22T09:15:02.000Z",
    "createdAt": "2024-08-22T09:14:24.000Z",
    "requested_amount": 30050,
    "pos_transaction_data": null,
    "source": null,
    "fees_breakdown": null,
    "connect": null,
    "transaction_date": "2024-08-22T09:14:24.000Z",
    "plan_object": {},
    "subaccount": {}
  }
}
List Transactions
List transactions carried out on your integration

Transaction ID data type
If you plan to store or make use of the the transaction ID, you should represent it as a unsigned 64-bit integer. To learn more, check out our changelog.

Headers
authorization
String
Set value to Bearer SECRET_KEY

Query Parameters
perPage
Integer
Specify how many records you want to retrieve per page. If not specify we use a default value of 50.

page
Integer
Specify exactly what page you want to retrieve. If not specify we use a default value of 1.

customer
Integer
optional
Specify an ID for the customer whose transactions you want to retrieve

terminalid
String
optional
The Terminal ID for the transactions you want to retrieve

status
String
optional
Filter transactions by status ('failed', 'success', 'abandoned')

from
Datetime
optional
A timestamp from which to start listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

to
Datetime
optional
A timestamp at which to stop listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

amount
Integer
optional
Filter transactions by amount using the supported currency code

GET
/transaction

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Transactions retrieved",
  "data": [
    {
      "id": 4099260516,
      "domain": "test",
      "status": "success",
      "reference": "re4lyvq3s3",
      "amount": 40333,
      "message": null,
      "gateway_response": "Successful",
      "paid_at": "2024-08-22T09:15:02.000Z",
      "created_at": "2024-08-22T09:14:24.000Z",
      "channel": "card",
      "currency": "NGN",
      "ip_address": "197.210.54.33",
      "metadata": null,
      "log": {
        "start_time": 1724318098,
        "time_spent": 4,
        "attempts": 1,
        "errors": 0,
        "success": true,
        "mobile": false,
        "input": [],
        "history": [
          {
            "type": "action",
            "message": "Attempted to pay with card",
            "time": 3
          },
          {
            "type": "success",
            "message": "Successfully paid with card",
            "time": 4
          }
        ]
      },
      "fees": 10283,
      "fees_split": null,
      "customer": {
        "id": 181873746,
        "first_name": null,
        "last_name": null,
        "email": "demo@test.com",
        "phone": null,
        "metadata": {
          "custom_fields": [
            {
              "display_name": "Customer email",
              "variable_name": "customer_email",
              "value": "new@email.com"
            }
          ]
        },
        "customer_code": "CUS_1rkzaqsv4rrhqo6",
        "risk_action": "default"
      },
      "authorization": {
        "authorization_code": "AUTH_uh8bcl3zbn",
        "bin": "408408",
        "last4": "4081",
        "exp_month": "12",
        "exp_year": "2030",
        "channel": "card",
        "card_type": "visa ",
        "bank": "TEST BANK",
        "country_code": "NG",
        "brand": "visa",
        "reusable": true,
        "signature": "SIG_yEXu7dLBeqG0kU7g95Ke",
        "account_name": null
      },
      "plan": {},
      "split": {},
      "subaccount": {},
      "order_id": null,
      "paidAt": "2024-08-22T09:15:02.000Z",
      "createdAt": "2024-08-22T09:14:24.000Z",
      "requested_amount": 30050,
      "source": {
        "source": "merchant_api",
        "type": "api",
        "identifier": null,
        "entry_point": "transaction_initialize"
      },
      "connect": null,
      "pos_transaction_data": null
    }
  ],
  "meta": {
    "next": "dW5kZWZpbmVkOjQwMTM3MDk2MzU=",
    "previous": null,
    "perPage": 50
  }
}
Fetch Transaction
Get details of a transaction carried out on your integration

Transaction ID data type
If you plan to store or make use of the the transaction ID, you should represent it as a unsigned 64-bit integer. To learn more, check out our changelog.

Headers
authorization
String
Set value to Bearer SECRET_KEY

Path Parameters
id
Integer
An ID for the transaction to fetch

GET
/transaction/:id

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/{id}"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Transaction retrieved",
  "data": {
    "id": 4099260516,
    "domain": "test",
    "status": "success",
    "reference": "re4lyvq3s3",
    "receipt_number": null,
    "amount": 40333,
    "message": null,
    "gateway_response": "Successful",
    "helpdesk_link": null,
    "paid_at": "2024-08-22T09:15:02.000Z",
    "created_at": "2024-08-22T09:14:24.000Z",
    "channel": "card",
    "currency": "NGN",
    "ip_address": "197.210.54.33",
    "metadata": "",
    "log": {
      "start_time": 1724318098,
      "time_spent": 4,
      "attempts": 1,
      "errors": 0,
      "success": true,
      "mobile": false,
      "input": [],
      "history": [
        {
          "type": "action",
          "message": "Attempted to pay with card",
          "time": 3
        },
        {
          "type": "success",
          "message": "Successfully paid with card",
          "time": 4
        }
      ]
    },
    "fees": 10283,
    "fees_split": null,
    "authorization": {
      "authorization_code": "AUTH_uh8bcl3zbn",
      "bin": "408408",
      "last4": "4081",
      "exp_month": "12",
      "exp_year": "2030",
      "channel": "card",
      "card_type": "visa ",
      "bank": "TEST BANK",
      "country_code": "NG",
      "brand": "visa",
      "reusable": true,
      "signature": "SIG_yEXu7dLBeqG0kU7g95Ke",
      "account_name": null
    },
    "customer": {
      "id": 181873746,
      "first_name": null,
      "last_name": null,
      "email": "demo@test.com",
      "customer_code": "CUS_1rkzaqsv4rrhqo6",
      "phone": null,
      "metadata": {
        "custom_fields": [
          {
            "display_name": "Customer email",
            "variable_name": "customer_email",
            "value": "new@email.com"
          }
        ]
      },
      "risk_action": "default",
      "international_format_phone": null
    },
    "plan": {},
    "subaccount": {},
    "split": {},
    "order_id": null,
    "paidAt": "2024-08-22T09:15:02.000Z",
    "createdAt": "2024-08-22T09:14:24.000Z",
    "requested_amount": 30050,
    "pos_transaction_data": null,
    "source": {
      "type": "api",
      "source": "merchant_api",
      "identifier": null
    },
    "fees_breakdown": null,
    "connect": null
  }
}
Charge Authorization
All authorizations marked as reusable can be charged with this endpoint whenever you need to receive payments

Headers
authorization
String
Set value to Bearer SECRET_KEY

content-type
String
Set value to application/json

Body Parameters
amount
String
Amount should be in the subunit of the supported currency

email
String
Customer's email address

authorization_code
String
Valid authorization code to charge

reference
String
optional
Unique transaction reference. Only -, ., = and alphanumeric characters allowed.

currency
String
optional
Currency in which amount should be charged.

metadata
String
optional
Stringified JSON object. Add a custom_fields attribute which has an array of objects if you would like the fields to be added to your transaction when displayed on the dashboard. Sample: {"custom_fields":[{"display_name":"Cart ID","variable_name": "cart_id","value": "8393"}]}

channels
Array
optional
Send us 'card' or 'bank' or 'card','bank' as an array to specify what options to show the user paying

subaccount
String
optional
The code for the subaccount that owns the payment. e.g. ACCT_8f4s1eq7ml6rlzj

transaction_charge
Integer
optional
A flat fee to charge the subaccount for this transaction in the subunit of the supported currency. This overrides the split percentage set when the subaccount was created. Ideally, you will need to use this if you are splitting in flat rates (since subaccount creation only allows for percentage split).

bearer
String
optional
Who bears Paystack charges? account or subaccount (defaults to account).

queue
Boolean
optional
If you are making a scheduled charge call, it is a good idea to queue them so the processing system does not get overloaded causing transaction processing errors. Send queue:true to take advantage of our queued charging.

POST
/transaction/charge_authorization

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/charge_authorization"
authorization="Authorization: Bearer YOUR_SECRET_KEY"
content_type="Content-Type: application/json"
data='{ 
  "email": "customer@email.com", 
  "amount": "20000", 
  "authorization_code": "AUTH_72btv547"
}'

curl "$url" -H "$authorization" -H "$content_type" -d "$data" -X POST
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Charge attempted",
  "data": {
    "amount": 35247,
    "currency": "NGN",
    "transaction_date": "2024-08-22T10:53:49.000Z",
    "status": "success",
    "reference": "0m7frfnr47ezyxl",
    "domain": "test",
    "metadata": "",
    "gateway_response": "Approved",
    "message": null,
    "channel": "card",
    "ip_address": null,
    "log": null,
    "fees": 10247,
    "authorization": {
      "authorization_code": "AUTH_uh8bcl3zbn",
      "bin": "408408",
      "last4": "4081",
      "exp_month": "12",
      "exp_year": "2030",
      "channel": "card",
      "card_type": "visa ",
      "bank": "TEST BANK",
      "country_code": "NG",
      "brand": "visa",
      "reusable": true,
      "signature": "SIG_yEXu7dLBeqG0kU7g95Ke",
      "account_name": null
    },
    "customer": {
      "id": 181873746,
      "first_name": null,
      "last_name": null,
      "email": "demo@test.com",
      "customer_code": "CUS_1rkzaqsv4rrhqo6",
      "phone": null,
      "metadata": {
        "custom_fields": [
          {
            "display_name": "Customer email",
            "variable_name": "customer_email",
            "value": "new@email.com"
          }
        ]
      },
      "risk_action": "default",
      "international_format_phone": null
    },
    "plan": null,
    "id": 4099490251
  }
}
View Transaction Timeline
View the timeline of a transaction

Headers
authorization
String
Set value to Bearer SECRET_KEY

Path Parameters
id_or_reference
String
The ID or the reference of the transaction

GET
/transaction/timeline/:id_or_reference

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/timeline/{id_or_reference}"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Timeline retrieved",
  "data": {
    "start_time": 1724318098,
    "time_spent": 4,
    "attempts": 1,
    "errors": 0,
    "success": true,
    "mobile": false,
    "input": [],
    "history": [
      {
        "type": "action",
        "message": "Attempted to pay with card",
        "time": 3
      },
      {
        "type": "success",
        "message": "Successfully paid with card",
        "time": 4
      }
    ]
  }
}
Transaction Totals
Total amount received on your account

Headers
authorization
String
Set value to Bearer SECRET_KEY

Query Parameters
perPage
Integer
Specify how many records you want to retrieve per page. If not specify we use a default value of 50.

page
Integer
Specify exactly what page you want to retrieve. If not specify we use a default value of 1.

from
Datetime
optional
A timestamp from which to start listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

to
Datetime
optional
A timestamp at which to stop listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

GET
/transaction/totals

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/totals"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Transaction totals",
  "data": {
    "total_transactions": 42670,
    "total_volume": 6617829946,
    "total_volume_by_currency": [
      {
        "currency": "NGN",
        "amount": 6617829946
      },
      {
        "currency": "USD",
        "amount": 28000
      }
    ],
    "pending_transfers": 6617829946,
    "pending_transfers_by_currency": [
      {
        "currency": "NGN",
        "amount": 6617829946
      },
      {
        "currency": "USD",
        "amount": 28000
      }
    ]
  }
}
Export Transaction
Export a list of transactions carried out on your integration

Headers
authorization
String
Set value to Bearer SECRET_KEY

Query Parameters
perPage
Integer
Specify how many records you want to retrieve per page. If not specify we use a default value of 50.

page
Integer
Specify exactly what page you want to retrieve. If not specify we use a default value of 1.

from
Datetime
optional
A timestamp from which to start listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

to
Datetime
optional
A timestamp at which to stop listing transaction e.g. 2016-09-24T00:00:05.000Z, 2016-09-21

customer
Integer
optional
Specify an ID for the customer whose transactions you want to retrieve

status
String
optional
Filter transactions by status ('failed', 'success', 'abandoned')

currency
String
optional
Specify the transaction currency to export

amount
Integer
optional
Filter transactions by amount, using the supported currency

settled
Boolean
optional
Set to true to export only settled transactions. false for pending transactions. Leave undefined to export all transactions

settlement
Integer
optional
An ID for the settlement whose transactions we should export

payment_page
Integer
optional
Specify a payment page's id to export only transactions conducted on said page

GET
/transaction/export

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/export"
authorization="Authorization: Bearer YOUR_SECRET_KEY"

curl "$url" -H "$authorization" -X GET
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Export successful",
  "data": {
    "path": "https://s3.eu-west-1.amazonaws.com/files.paystack.co/exports/463433/transactions/Integration_name_transactions_1724324423843.csv?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAI7CL5IZL2DJHOPPA%2F20240822%2Feu-west-1%2Fs3%2Faws4_request&X-Amz-Date=20240822T110023Z&X-Amz-Expires=60&X-Amz-Signature=40525f4f361e07c09a445a1a6888d135758abd507ed988ee744c2d94ea14cf1e&X-Amz-SignedHeaders=host",
    "expiresAt": "2024-08-22 11:01:23"
  }
}
Partial Debit
Retrieve part of a payment from a customer

Headers
authorization
String
Set value to Bearer SECRET_KEY

content-type
String
Set value to application/json

Body Parameters
authorization_code
String
Authorization Code

currency
String
Specify the currency you want to debit. Allowed values are NGN or GHS.

amount
String
Amount should be in the subunit of the supported currency

email
String
Customer's email address (attached to the authorization code)

reference
String
optional
Unique transaction reference. Only -, ., = and alphanumeric characters allowed.

at_least
String
optional
Minimum amount to charge

POST
/transaction/partial_debit

cURL
cURL
Copy
#!/bin/sh
url="https://api.paystack.co/transaction/partial_debit"
authorization="Authorization: Bearer YOUR_SECRET_KEY"
content_type="Content-Type: application/json"
data='{ 
  "authorization_code": "AUTH_72btv547", 
  "currency": "NGN", 
  "amount": "20000",
  "email": "customer@email.com"
}'

curl "$url" -H "$authorization" -H "$content_type" -d "$data" -X POST
Sample Response

200 Ok
200 Ok
Copy
{
  "status": true,
  "message": "Charge attempted",
  "data": {
    "amount": 50000,
    "currency": "NGN",
    "transaction_date": "2024-08-22T11:13:48.000Z",
    "status": "success",
    "reference": "ofuhmnzw05vny9j",
    "domain": "test",
    "metadata": "",
    "gateway_response": "Approved",
   