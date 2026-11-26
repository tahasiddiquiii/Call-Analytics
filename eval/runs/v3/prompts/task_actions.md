Question 3 of 3: what must happen after the call, and what should a supervisor know?

action_items: things that must still happen AFTER the call. Do not list things already completed during the call. Each item has:
- owner: agent (the agent on this call promised to do it), company (another team, a technician or a system must do it), customer (the caller must do it), or supervisor (needs a supervisor).
- task: a short instruction. Include the day or deadline if one was said.
- due: the deadline exactly as said in the call (for example "Thursday", "Monday", "within two business days", "end of day tomorrow"), or null. Never invent a date.

insights: only what a supervisor should know that a summary would not already say. Most calls have 0 to 3 insights. Add an insight ONLY if you can quote words from the transcript that prove it. Each has:
- category, one of:
  - agent_conduct: the agent did something notably well or badly (for example unhelpful, offered no options, could not give a transfer number, calmed an angry customer).
  - compliance_risk: the agent promised something without authority or gave wrong information, or someone asked for false information to be recorded.
  - process_gap: a company process or system failed or is missing.
  - product_feedback: a complaint about a product, an app, a price or a service.
  - churn_risk: the customer said they may cancel, leave or go to a competitor.
  - repeat_contact: the customer says they contacted the company before about this problem, or that this problem has happened before.
  - data_quality: an identifier or detail was unclear, conflicting or could not be confirmed.
- text: one sentence.
- quote: the exact transcript words that prove it (at most 20 words).
