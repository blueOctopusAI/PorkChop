---
title: "We Built a Tool That Reads Congressional Bills So Staffers Don't Have To"
slug: "porkchop-reads-the-bills"
date: "2026-02-24"
author: "Blue Octopus Technology"
category: "Engineering"
tags: ["PorkChop", "Open Source", "Government", "AI Tools", "Python"]
excerpt: "A congressional staffer gets a 1,500-page bill dropped on his desk the night before a vote. No human can read that in time. So we built something that does."
image: "/images/porkchop-logo.png"
featured: true
draft: false
---

It's 9 PM on a Tuesday in Washington. A 1,500-page spending bill just landed on a staffer's desk. The vote is tomorrow morning. Buried somewhere in those pages are 285 spending items totaling $192 billion, 891 legal references to other laws, 94 deadlines, and 117 government entities with new responsibilities.

Nobody is reading all of that by morning. Nobody ever does.

This is the reality for congressional staff. Not occasionally — routinely. Massive omnibus bills get dropped with hours to spare, and the people advising elected officials on how to vote are left skimming, guessing, and relying on summaries written by the same people who want the bill to pass.

We built PorkChop to fix that.

## Where This Came From

Tim's brother is chief of staff for Congressman Thomas Massie. He described the problem in plain terms: bills arrive late, they're enormous, and the formatting is a mess. Raw text from the Government Publishing Office is littered with printer codes, XML file paths, page numbers jammed into the middle of sentences, and timestamps from whatever computer last touched the file.

That's before you even get to the content. The actual legislative text is dense, cross-referenced, and deliberately structured to be hard to parse quickly. A single section might reference four other laws, create three new deadlines, and allocate $2 billion — all in one paragraph.

The original prototype was a regex script built in December 2024. It could pull dollar amounts and legal references out of raw text. Useful, but limited. In February 2026, we rebuilt it from the ground up into a full product — Python backend, Next.js frontend, database, API, AI analysis, and a scoring system that flags the spending most likely to be pork.

## What PorkChop Actually Does

You give it a bill number. It fetches the full text from Congress.gov, cleans up the formatting garbage, breaks the bill into logical sections, and extracts every fact it can find.

Here's what it pulled from H.R. 10515 — the Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025. That's the bill that included Tropical Storm Helene disaster relief for Western North Carolina.

- **37,261 lines** of raw government text, cleaned down to **29,525** (21% was formatting noise)
- **207 sections** identified by legislative structure — divisions, titles, subtitles
- **285 funding items** totaling **$192 billion**, each tagged with its purpose and recipient when detectable
- **891 legal references** — US Code citations, Public Laws, named Acts
- **94 deadlines** — every "not later than" paired with who's responsible and what they have to do
- **117 entities** — every Department, Office, Bureau, and Agency mentioned

That's the regex layer. It runs in seconds, costs nothing, and catches the structured data that follows predictable patterns.

The AI layer goes deeper. It reads each section and writes a plain English summary. It identifies what the money is actually for, who gets it, and what new authorities are being created. You can ask it questions about the bill in natural language — "What does this bill do for veterans?" or "How much goes to FEMA?" — and get answers grounded in the actual text.

## The Pork Scoring

This is the part people remember.

Every spending item gets scored from 0 to 100 on how likely it is to be pork barrel spending. The scoring looks at a handful of signals that have historically marked earmarks:

**Geographic specificity.** If a line item mentions a specific county, city, or district, it scores higher. Legitimate federal spending tends to be national in scope. Spending earmarked for one congressman's district tends not to be.

**Named beneficiaries.** Money directed to a specific university, hospital, museum, or foundation scores higher than money directed to a federal agency. "The Department of Education" is a normal recipient. "The University of [Congressman's State]" is a flag.

**Unrelatedness.** If a spending item has nothing to do with the bill's stated purpose — say, a highway project tucked into a disaster relief bill — the score goes up.

**Open-ended availability.** Money marked "until expended" with no fiscal year limit gets a bump. It's a pattern associated with spending that's meant to fly under the radar.

**Small specific amounts.** A $5 million line item in a $192 billion bill is proportionally tiny. Tiny, specific items are more likely to be earmarks added as favors than core provisions of the legislation.

On H.R. 10515, the average pork score was 6.8 out of 100 — meaning most spending was clearly related to the bill's purpose. The maximum was 40. That's a bill doing roughly what it says on the label, with a few items worth a closer look.

The heuristic scoring is free and fast. For items that score above the threshold, an optional AI layer applies deeper analysis using the actual criteria from Citizens Against Government Waste's Pig Book — the gold standard for earmark identification.

## How It Works (Without the Jargon)

Four steps, each building on the last.

**Clean.** Strip out the printer codes, XML paths, timestamps, and page numbers that the Government Publishing Office embeds in every document. This is the digital equivalent of removing the staples and Post-it notes before you can read the actual paper.

**Chunk.** Split the bill into logical sections based on its legislative structure — divisions, titles, subtitles. Each chunk represents one coherent piece of the bill, not an arbitrary page break.

**Extract.** Run pattern matching across every chunk to pull out dollar amounts, legal references, deadlines, responsible entities, and duties. Five different strategies work together to figure out what each dollar amount is actually for.

**Score.** Run every spending item through the pork detector. Flag the ones that look like earmarks, geographic carve-outs, or unrelated riders.

The AI analysis is optional and runs on top of this. It uses Claude for semantic understanding — the kind of reading comprehension that regex can't do. But the core pipeline works without any AI at all. Regex is free, fast, and reliable for structured data. AI adds the interpretation layer.

## Why This Isn't a $50,000 Enterprise Product

The companies that sell legislative intelligence tools to Congress — FiscalNote, Plural Policy, Quorum — charge enterprise pricing. We're talking five and six figures annually. Their products are good. They're also inaccessible to anyone who isn't a well-funded lobbying firm or a congressional office with budget to spare.

PorkChop is open source, free, and MIT licensed. Bill text is public record — US government documents carry no copyright. The Congress.gov API key is free. The only cost is the AI analysis, and that's optional. Users bring their own API keys, stored in their browser only. We never see them.

The web frontend lets you enter any bill number and get results. Bills that have already been processed are cached for everyone. The whole thing runs on SQLite — no server to maintain, no database to administer.

We didn't build this to compete with enterprise legislative intelligence. We built it because a staffer needed to read a bill by morning, and the tools that could help him cost more than his salary.

## Try It

PorkChop is on GitHub. Clone it, process a bill, see what falls out.

The Python CLI handles the backend processing. The Next.js frontend gives you a dashboard, spending tables, pork analysis, version comparison, and AI chat. There's even an MCP server with 12 tools if you want to plug bill data directly into your own AI workflow.

Eighty-nine tests. Real data from real bills. Documentation that assumes you've never seen a congressional bill before — because most people haven't.

**GitHub:** [github.com/BlueOctopusTechnology/PorkChop](https://github.com/BlueOctopusTechnology/PorkChop)

The tagline is "AI that reads the bills so you don't have to." But the more accurate version might be: it reads the bills so the people voting on them can actually know what's inside.

*Blue Octopus Technology builds software for people who have real problems and no patience for enterprise sales calls. [See what we build](/services).*
