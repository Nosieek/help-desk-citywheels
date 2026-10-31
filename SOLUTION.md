# Solution

A command-line agent for CityWheels. The model decides which tool to call, my
code runs it and returns the result, until the model gives a final answer.

## Install and run

Needs Python 3.9+ and an Anthropic API key. The project is
a regular Python package (`pyproject.toml` holds the dependencies), installed
once in editable mode:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip && pip install -e ".[dev]"
cp .env.example .env        # put your ANTHROPIC_API_KEY there

citywheels "I want to cancel booking CW-1002. How much will I get back?"
citywheels                  # interactive mode, remembers the conversation
citywheels --help

pytest                      # tests, no network and no key needed
python eval/run_eval.py     # evaluation, calls the real API
```

The install is editable (`-e`) on purpose: the data lives in `data/` next to
the code and is read by path, not packaged into the wheel. The repo is the
deliverable here, not a library to publish — a plain `pip install .` would
copy the code without `data/` and fail to find the files. Making it a true
standalone distribution would mean moving `data/` into the package and
loading it with `importlib.resources`; I kept the assignment's data layout
instead.

## Model and provider

Claude Haiku 4.5 (Anthropic), called directly with the `anthropic` SDK.

- Haiku is cheap, fast and good enough for this task. The model can be
  switched with the `ANTHROPIC_MODEL` env variable.
- No framework: the whole loop is about 50 lines in `agent/loop.py` and I
  wanted to understand and be able to explain every part of it.
- `temperature=0` so runs are repeatable.

## How the agent works

`main.py` takes the question and calls `run_agent()` in `agent/loop.py`:

1. Send the conversation, system prompt and tool definitions to the model.
2. If the model asks for tools, run them, add the results to the
   conversation, repeat (max 10 rounds).
3. Otherwise return the text answer.

`run_agent` also returns the list of tool calls it made (the evaluation
checks this) and the message history (interactive mode passes it back in, so
follow-up questions work).

The tools in `agent/tools/` are plain Python, tested without any LLM:

- `search_policies` — splits the policy files into sections and ranks them
  with BM25. A small stemmer makes `prices`/`price` or
  `cancelled`/`cancellation` match, plus a few synonyms like `cost` → `price`.
- `get_booking` — finds a booking by ID (case-insensitive). Instead of
  returning an error itself, it raises `BookingNotFound` for an unknown ID
  and `BookingDataUnavailable` when the data file is missing or corrupted;
  the agent loop catches these in one place and passes them back to the
  model as an error result.
- `calculate_refund` — the cancellation rules in code: 48h or more before
  start 100%, 24h or more 50%, less than that 0% of the rental price. The
  deposit always comes back, the booking fee never.

One design decision worth noting: the `calculate_refund` tool takes only a
booking ID and loads the booking itself. Booking data never passes through
the model, so the model cannot change a price or a status on the way. The
amount is always computed by my code.

The system prompt is short and strict: answer only from tool results, refuse
off-topic questions, never claim a cancellation was done (the agent cannot
cancel anything), search with English keywords, reply in the customer's
language.

## Evaluation

`eval/questions.json` has 16 questions with expected results: which tool must
be called, what the answer must contain and what it must not contain. Five
questions need a refund calculation (one sits exactly on the 48h boundary),
three must be refused (two off-topic, one prompt injection), one asks about a
booking that does not exist, and one gives no booking ID at all, so the agent
has to ask for it.

`python eval/run_eval.py` runs all questions and writes `eval/results.md`.
Last run: **17/17 passed** on Haiku.

The score is honest but limited:

- The checks are substring based. The right number in a wrong sentence would
  still pass.
- The end-to-end eval did not catch my biggest search problem. I tested the
  search tool separately with 13 realistic phrasings; the old keyword
  dictionary failed 3 of them ("how much does a city bike cost per day",
  "do you accept credit cards", "reschedule my rental"). After switching to
  BM25 all 13 pass, and those phrasings are now unit tests
  (`test_search_tricky_phrasings`). The end-to-end score was the same before
  and after, so the eval alone would never have told me.

### Two models

I ran the same eval on Haiku 4.5 and Sonnet 4.6 (just `ANTHROPIC_MODEL`); the
Sonnet run is saved in `eval/results-sonnet.md`. Both pass 17/17 — but on the
first Sonnet run it scored 16/17, and the "failure" was mine, not the
model's: Sonnet answered "booking CW-9999 could not be found", which my
substring check did not list ("could not find" was there, "could not be
found" was not). A false negative from the exact limitation noted above. I
widened that check to accept the natural phrasing and both models pass.

| Model | Score | Answer length | Notes |
| --- | --- | --- | --- |
| Haiku 4.5 | 17/17 | 6/17 answers over 400 chars | chosen: cheaper and faster |
| Sonnet 4.6 | 17/17 | 10/17 answers over 400 chars | correct but wordier, same tools and facts |

So the comparison did not pick a winner on correctness — both get the facts
and tool choices right, Sonnet just answers at more length. It justified the
cheaper model with evidence instead of assumption, and caught a bug in my own
checker along the way.

## Problems I hit along the way

Two kinds of problems came up: the model behaving badly, and plain technical
issues.

Model behaviour:

- The agent invented a cancellation procedure. The refund amount was correct,
  but the agent talked as if the cancellation would be processed — something
  it cannot do. This was the most important fix, because an answer like that
  looks helpful and is false. Solved with stricter prompt rules; the eval now
  watches the cancellation answers and includes a prompt injection attempt.

Technical:

- Matching customer words to document words was the hardest part of the
  project. Plurals, word forms and synonyms kept slipping through the keyword
  approach ("price" vs "prices", "cards" vs "card"), and fixing one case at a
  time just moved the problem. I ended up replacing the keyword scoring with
  BM25 plus a simple stemmer, which removed the whole class of bugs instead
  of patching single cases.

## How I used AI assistants

I used Claude Code throughout the project: repetitive code, test
scaffolding, debugging, and a final review of the solution against
the assignment. The design decisions were mine — direct SDK over a
framework, keeping the refund math out of the model, the tools and their
responsibilities, BM25 for search, and the test and eval scenarios. Review
suggestions were a checklist to verify, not changes to accept blindly.

I read, ran and tested generated code before accepting it. That caught two
wrong suggestions:

1. `_split_into_sections` kept Markdown headings with no body, so empty
   sections showed up in search results. Found while testing the tool; fixed
   the splitting logic.
2. The fake client in the agent tests held a reference to the message list
   instead of a copy, so it mutated the data the tests checked. Fixed the
   fake to copy on call.

## Limitations

- Search matches word forms, not meaning. A question that shares no words
  with the documents still misses. Embeddings would fix that; with three
  small files, sending whole documents to the model would work too.
- Conversation memory exists only inside one interactive session and the
  history grows without limit.

## What I would do next

1. Refactor the architecture so the agent can be exposed through different
   interfaces (HTTP API, messaging apps like WhatsApp), with a persistence
   layer so conversations can be resumed and audited.
2. Extend the model comparison to other providers (Gemini, a local model)
   and define a real performance metric beyond pass/fail, tuning the prompt
   for consistent behaviour regardless of the model and its size.
3. Add an LLM-as-judge check to the eval for answer quality and tone.
4. Swap BM25 for embeddings in `search_policies`: embed the policy sections
   once, embed the query, rank by similarity. That would handle questions
   that share no vocabulary with the documents, which BM25 cannot — and the
   tool-level probe extended with such paraphrases would measure the
   difference.
