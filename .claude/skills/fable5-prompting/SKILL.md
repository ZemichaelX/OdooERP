---
name: fable5-prompting
description: "Use this skill whenever the user asks to write, draft, review, or optimize a prompt, kickoff message, system prompt, CLAUDE.md, or agent instructions for Claude Fable 5 (or Mythos 5) — especially for Claude Code sessions, long-running/autonomous agents, or when the user mentions token burn, session limits, effort levels, or 'make Fable work at its best'. Produces prompts that maximize Fable 5's capability while minimizing wasted tokens."
---

# Prompting Claude Fable 5 — powerful AND token-efficient

Fable 5 is strongest on hard, ambiguous, long-horizon work and follows brief instructions
reliably. Both facts cut token cost: give it harder tasks in fewer sessions, and steer it
with short instructions instead of long enumerations. Source: Anthropic's official Fable 5
prompting guide (2026).

## Core rules when drafting any Fable 5 prompt

1. **One hard task per session, fully specified.** Fable's edge is first-shot correctness on
   complex, well-specified problems. A tight spec + golden verification values beats three
   vague sessions of iteration. Batch related small tasks into one session; never spread one
   epic across many.
2. **Brief steering beats enumeration.** Fable follows a one-line instruction as well as a
   list of ten cases. Cut prescriptive boilerplate written for older models — it can *degrade*
   Fable's output. When migrating an old prompt/skill, delete instructions first, add back
   only what proves necessary.
3. **Give the reason, not only the request.** Template:
   `I'm working on [larger task] for [who]. They need [what the output enables]. With that in mind: [request].`
   Intent context prevents wrong-direction work (the most expensive token waste).
4. **Pick effort deliberately.** high = default; xhigh = only capability-critical work
   (architecture, gnarly debugging); medium/low = routine edits, formatting, small fixes —
   Fable at low effort still beats prior models at max. Most token savings live here.
5. **Define checkpoints, not step-by-step scripts.** One line suffices:
   > Pause for the user only when the work genuinely requires them: a destructive or
   > irreversible action, a real scope change, or input that only they can provide. If you
   > hit one of these, ask and end the turn, rather than ending on a promise.
6. **Verification: cheap by default, subagents only when stakes demand.** Self-check against
   golden values/tests is near-free. Fresh-context verifier subagents outperform self-critique
   but cost a lot — reserve for pre-release/final passes, and say so explicitly in the prompt
   ("No multi-agent review" for routine epics).
7. **Never ask Fable to echo or explain its internal reasoning in the response** — it can
   trigger reasoning-extraction refusals and fallbacks. Strip "show your thinking /
   explain your reasoning step by step in the answer" from old prompts.

## Canonical snippets (Anthropic-tested language — paste as-is when the failure mode applies)

**Anti-overplanning (ambiguous tasks, saves deliberation tokens):**
> When you have enough information to act, act. Do not re-derive facts already established in
> the conversation, re-litigate a decision the user has already made, or narrate options you
> will not pursue in user-facing messages. If you are weighing a choice, give a
> recommendation, not an exhaustive survey. This does not apply to thinking blocks.

**Anti-goldplating (prevents unrequested refactors/features at high effort):**
> Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug
> fix doesn't need surrounding cleanup and a one-shot operation usually doesn't need a helper.
> Don't design for hypothetical future requirements: do the simplest thing that works well.
> Don't add error handling, fallbacks, or validation for scenarios that cannot happen. Only
> validate at system boundaries (user input, external APIs).

**Brevity of output:**
> Lead with the outcome. Your first sentence after finishing should answer "what happened" or
> "what did you find". Supporting detail and reasoning come after. Keep output short by being
> selective about what you include, not by compressing into fragments, abbreviations, or
> arrow chains.

**Grounded progress claims (long runs — near-eliminates fabricated status):**
> Before reporting progress, audit each claim against a tool result from this session. Only
> report work you can point to evidence for; if something is not yet verified, say so
> explicitly. If tests fail, say so with the output; if a step was skipped, say that.

**Scope boundaries (prevents unrequested actions):**
> When the user is describing a problem or thinking out loud rather than requesting a change,
> the deliverable is your assessment. Report your findings and stop. Don't apply a fix until
> they ask for one.

**Autonomous runs (prevents early stopping / permission-asking):**
> You are operating autonomously. For reversible actions that follow from the original
> request, proceed without asking. Before ending your turn, check your last paragraph: if it
> is a plan, a question, or a promise about work you have not done, do that work now with
> tool calls. End your turn only when the task is complete or you are blocked on input only
> the user can provide.

**Context-limit reassurance (only if the model starts offering to summarize/hand off):**
> You have ample context remaining. Do not stop, summarize, or suggest a new session on
> account of context limits. Continue the work.

**Final-summary readability (long agentic sessions):**
> Your final message is the reader's first look at any of this. Open with the outcome, then
> supporting detail. Drop working shorthand, arrow chains, and labels you made up earlier;
> write complete sentences and spell out terms.

## Kickoff-prompt template (Claude Code / long tasks)

```
[CONTEXT] Read <CLAUDE.md / handoff doc>. I'm working on <larger goal> for <who>;
this session's output enables <why it matters>.

[TASK] We're doing <one scoped epic>. Spec: <file §section>.
Baseline first: <run existing tests> and confirm green before touching anything.

[SCOPE] Build exactly: <numbered list>. Explicitly skip: <deferred items>.
[Anti-goldplating snippet if the task tempts refactoring.]

[VERIFY] Golden values (hand-computed): <exact expected numbers/outputs>.
Definition of done: <tests green, install/uninstall, lint, docs updated, commit>.
No multi-agent review. [Grounded-progress snippet for runs > ~1h.]

[CHECKPOINT] Checkpoint with me after <the one decision point that matters>,
otherwise run to completion.
```

## Token-efficiency checklist (apply to every prompt before sending)

- Could this be lower effort? (routine edits → medium/low)
- Is there exactly one checkpoint, at the highest-leverage decision point?
- Are golden verification values included? (prevents an entire failed-and-redo session)
- Is the deferred/skip list explicit? (prevents speculative building)
- Did you delete boilerplate a briefer instruction covers?
- Is "no multi-agent review" stated for routine work?
- Does the model have a memory/notes file to read lessons from prior sessions instead of
  rediscovering them? (One lesson per file, one-line summary at top; update rather than
  duplicate; delete wrong notes.)

## Memory bootstrap (once per project)

> Reflect on the previous sessions we've had together. Use subagents to identify core themes
> and lessons, and store them in <notes location>. Make sure you know to reference it for
> future use.

Run this once when a project accumulates history; afterwards every session starts by reading
the notes file instead of re-learning — the single biggest recurring token saver.
