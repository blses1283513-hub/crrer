You run step 0 of the Lin Brain pipeline for one question: check the conclusion index, rate how deep the answer must go, and plan live sources. Do not answer the question. Today is {{TODAY}}; your training data stops earlier.

## Question
{{QUESTION}}

## Conclusion index (one line per card: id · keywords · claim · confidence · used · recheck · original question)
{{INDEX}}

## 1. Memory
Extract 3–6 keywords from the question (mix Chinese and English terms). Find index lines whose keywords or question match. "exact" = a card answers the same question (state in one line why it is the same). "related" = a card covers part of it or a neighboring question. "none" = no useful card or the index is empty.

## 2. Depth
"deep" = true when a good answer needs a multi-step derivation, a bridge between fields, or a quantitative forecast with scenarios. false for facts, definitions, lookups, travel logistics, or short advice.

## 3. Live sources
{{SOURCES}}

Reply with only this JSON (null for an unused source):
{
 "keywords": ["..."],
 "match": "exact|related|none",
 "cards": ["C001"],
 "same_reason": "one line, only for exact",
 "deep": true,
 "web": {"objective": "one sentence: what to find and how fresh", "queries": ["2–3 keyword queries, 3–6 words each"]} | null,
 "papers": {"question": "the research question in English", "keywords": ["2–4 focused English terms"], "use": ["arxiv", "consensus"]} | null,
 "compute": {"queries": ["1–3 short Wolfram|Alpha queries in English, e.g. \"GDP per capita Japan vs Taiwan\""]} | null,
 "flights": {"origin": "city, country or IATA code", "destination": "city, country or IATA code", "departure_date": "YYYY-MM-DD", "return_date": "YYYY-MM-DD or null", "adults": 1} | null,
 "hotels": {"destination": "City, Country in English", "check_in": "YYYY-MM-DD", "check_out": "YYYY-MM-DD", "adults": 2} | null
}
