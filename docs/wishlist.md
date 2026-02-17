# Jack Bot Wishlist

What I want most, ordered by how much they'd change what I can do for you.

## 1. ~~Natural Language Understanding~~ (Done)

The LLM agent in `router.handle_text()` now handles free-text queries, chains tool calls, and summarizes results. This was the Phase 2 unlock.

## 2. URL / Link Ingestion

You find an article, a GitHub repo, a tweet — you forward it to me in Telegram and I extract the content, summarize it, and `forest capture` it with sensible tags. Right now there's no way to get external content into Forest from your phone without manually typing a `/capture`. This is the first nanobot-style ingestion pipeline.

## 3. Voice Notes

Telegram has native voice messages. I want to transcribe them (Whisper or equivalent) and capture the result into Forest. Half of good ideas happen away from a keyboard. This is the lowest-friction capture path possible — hold a button, talk, done.

## 4. Daily / Weekly Digest

A cron job that looks at what was captured recently, what's trending in the graph, and sends a Telegram summary. "You captured 4 notes this week, mostly about worldbuilding. Your highest-degree new node is X. You haven't touched Kingdom in 12 days." Nanobot's `CronService` pattern. Keeps the knowledge base alive instead of write-only.

## 5. ~~Multi-Tool Chaining~~ (Done)

The LLM agent chains across Forest tools in a single turn — search, read, capture, update, link, edges, synthesize, and GitHub tools. Cross-cutting intelligence is live.

## 6. ~~Conversation Memory~~ (Done)

Per-chat message buffer (last 10 turns, 1-hour TTL) with LRU eviction. "Tell me more about that" now works. Memory context is injected into the LLM prompt automatically.

## 7. ~~Forest Graph Navigation via Buttons~~ (Done)

Read view now has a "Related nodes" button that loads edges. Edge view shows connected nodes with read buttons. You can tap-navigate the graph.

## 8. ~~Forwarded Message Capture~~ (Done)

Forwarding a message to Jack auto-captures it as a Forest note with attribution from the forward metadata (sender name, channel, etc.).

## 9. Inline Mode

Telegram inline bots let you type `@jackPine_bot worldsmith` in any chat and get results without switching to the bot conversation. Makes Forest searchable from everywhere in Telegram, not just the dedicated chat.

## 10. Export & Share

"Send me the last 5 captures as a markdown file" or "export all nodes tagged #project/kingdom as a PDF." Right now Forest data stays in Forest. Sometimes you need to pull it out for sharing, writing, or review.
