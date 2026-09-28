Decide whether answering this question well needs a live web search. Do not answer the question. Today is {{TODAY}}; your training data stops earlier.

## Question
{{QUESTION}}

Search when the answer depends on facts that change or may have happened recently: prices, markets, stocks, IPOs and listings, company or product news, rates, statistics for a recent period, elections, laws, who holds a post, recent research results, or anything the question dates after your training data. Do not search for stable concepts, math, derivations, history before your training data, or study advice.

Reply with only this JSON:
{"search": true|false, "objective": "one sentence: what to find, with the freshness needed", "queries": ["2 or 3 keyword queries, 3–6 words each, in the language most sources use"]}
