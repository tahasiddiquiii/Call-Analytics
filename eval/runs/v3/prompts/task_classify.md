Question 1 of 3: what kind of call is this, and what did the customer want?

call_type:
- customer_service: a real caller asking for help.
- test_call: an internal test of the phone line (for example by QA staff).
- wrong_number: the caller meant to reach a different organisation.
- abandoned: the call ended before any request was made.

agent_name: the agent's first name as they introduced themselves, or null.
customer_name: the customer's name as said in the call, or null. It is used only to remove the name from the record.

summary: 1 to 3 plain sentences: what the customer wanted, what the agent did, and how the call ended. Do not use names.

intent.primary: the main reason for the call. One of:
- appointment_change: book, move or cancel an appointment
- account_update: change contact details, address or account settings
- cancellation_request: wants to cancel a service or contract
- billing_dispute: a wrong, unexpected or duplicate charge
- refund_request: wants money back for another reason
- order_issue: an order is missing, late, damaged or wrong
- claim_appeal: challenge a denied insurance claim
- claim_status: ask about the progress of an existing claim
- plan_change_inquiry: upgrade, downgrade or compare plans and prices
- technical_support: something is not working technically
- general_inquiry: a question with no problem to fix
- non_customer_call: test calls, wrong numbers and abandoned calls
- other: none of the above
intent.secondary: only if the customer clearly made a second, separate request, such as also changing their address. Most calls have none: use an empty list.
intent.detail: one short sentence.

customer_requested_escalation: true only if the customer asked for a supervisor, a manager or an escalation.
