Plan which live sources to query before answering this question. Do not answer the question. Today is {{TODAY}}; your training data stops earlier.

## Question
{{QUESTION}}

Sources (use only the ones this question really needs; most questions need none or one):
- web — current facts that change or may have happened recently: prices, markets, stocks, IPOs, company or product news, rates, recent statistics, elections, laws, who holds a post, visa and entry rules, local events, culture and customs of a place.
- papers — the question asks what research or evidence says, or links fields where published work would ground the answer.
  - "arxiv" for physics, math, computer science, statistics, quantitative finance, and electrical engineering.
  - "consensus" for peer-reviewed work in any field, including medicine, biology, psychology, economics, education, and social science.
  - Use both for a question that bridges these areas.
- flights — the student plans a trip and names where to fly from and to.
- hotels — the student plans a stay and names the place.
- For flights or hotels, dates are needed. If only a month or season is given, pick a representative window in the next such period after today. If no time is given at all, leave flights and hotels out.

Do not use any source for stable concepts, math, derivations, or study advice.

Reply with only this JSON (null for an unused source):
{
 "web": {"objective": "one sentence: what to find and how fresh", "queries": ["2–3 keyword queries, 3–6 words each"]} | null,
 "papers": {"question": "the research question in English", "keywords": ["2–4 focused English terms"], "use": ["arxiv", "consensus"]} | null,
 "flights": {"origin": "city, country or IATA code", "destination": "city, country or IATA code", "departure_date": "YYYY-MM-DD", "return_date": "YYYY-MM-DD or null", "adults": 1} | null,
 "hotels": {"destination": "City, Country in English", "check_in": "YYYY-MM-DD", "check_out": "YYYY-MM-DD", "adults": 2} | null
}
