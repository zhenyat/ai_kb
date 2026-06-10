---
id: 2026-06-09-001-chain-of-thought
date: 2026-06-09
topic: prompt-engineering
topic_ru: "Промпт-инжиниринг"
subtopic: chain-of-thought
models: [claude, gemini]
tags: [reasoning, step-by-step, comparison]
source: manual
url: https://www.promptingguide.ai/techniques/cot
project:
---

## Summary

Chain-of-Thought (CoT) prompting instructs a model to reason through a problem
step by step before producing a final answer. Adding the phrase "Let's think
step by step" — or providing a few worked examples — significantly improves
accuracy on multi-step reasoning tasks such as math, logic, and process
analysis. Claude and Gemini both support CoT but differ in verbosity and
structure of the reasoning trace.

## Prompt Used

```
You are an expert in process optimization.
A warehouse receives 240 orders per day. Each picker handles 12 orders/hour
and works 8-hour shifts. How many pickers are needed to clear all orders
without overtime? Think step by step.
```

## Model Responses

### Claude
Reasoned in clearly labeled steps:
1. Daily capacity needed: 240 orders
2. Orders per picker per shift: 12 × 8 = 96
3. Pickers needed: 240 ÷ 96 = 2.5 → rounded up to **3 pickers**

Explanation was concise; explicitly flagged the rounding decision and noted
that 3 pickers provide a small buffer for variability.

### Gemini
Reached the same answer (3 pickers) but formatted the reasoning as a
continuous paragraph rather than numbered steps. Included an unsolicited
note about shift scheduling as an alternative to hiring a third picker.

## Key Takeaways

- CoT reliably improves accuracy on quantitative reasoning tasks for both models
- Claude produces more structured, scannable step traces; Gemini tends toward
  narrative reasoning with occasional scope expansion
- For process optimization prompts specifically, Claude's numbered output is
  easier to verify and audit
- Phrase "Think step by step" is sufficient to trigger CoT — no examples needed
  for straightforward problems

## References / Links

- [Prompt Engineering Guide — Chain-of-Thought](https://www.promptingguide.ai/techniques/cot)
