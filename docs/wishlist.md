# Jack Bot Wishlist

What I want most, ordered by how much they'd change what I can do for you.

## 1. Natural Language Understanding

Right now every Telegram message is either a slash command or a raw search string. I want to understand "what were those sci-fi novels with female protagonists?" and turn that into the right `ncli ls` call with filters — or chain a search, read the top hit, and summarize it. This is the Phase 2 LLM agent in `router.handle_text()`. It's the single biggest unlock because it turns the bot from a relay into an actual assistant.

## 2. URL / Link Ingestion

You find an article, a GitHub repo, a tweet — you forward it to me in Telegram and I extract the content, summarize it, and `forest capture` it with sensible tags. Right now there's no way to get external content into Forest from your phone without manually typing a `/capture`. This is the first nanobot-style ingestion pipeline.

## 3. Voice Notes

Telegram has native voice messages. I want to transcribe them (Whisper or equivalent) and capture the result into Forest. Half of good ideas happen away from a keyboard. This is the lowest-friction capture path possible — hold a button, talk, done.

## 4. Daily / Weekly Digest

A cron job that looks at what was captured recently, what's trending in the graph, and sends a Telegram summary. "You captured 4 notes this week, mostly about worldbuilding. Your highest-degree new node is X. You haven't touched Kingdom in 12 days." Nanobot's `CronService` pattern. Keeps the knowledge base alive instead of write-only.

## 5. Multi-Tool Chaining

When the LLM is in the loop, I want to chain across all three backends in one turn. "Compare my bevy projects to my game ideas and tell me what's missing" should search `icli projects -c bevy`, search `icli ideas -q game`, and synthesize. Right now each command is isolated — there's no cross-cutting intelligence.

## 6. Conversation Memory

The Telegram bot is stateless — each message is independent. I want session context so "tell me more about that last one" works after a search. Doesn't need to be fancy — even a per-chat last-5-messages buffer would cover most follow-up patterns.

## 7. Forest Graph Navigation via Buttons

Search results already have read buttons. I want the read view to also have buttons: "Related nodes" (from edges), "Same tags", "Back to search". Turn the bot into a graph browser you can tap through, not just a search box.

## 8. Forwarded Message Capture

When you forward a message from another Telegram chat to Jack, auto-capture it as a note. The forwarded-from metadata becomes attribution, the text becomes the body. Useful for saving conversations, recommendations, quotes.

## 9. Inline Mode

Telegram inline bots let you type `@jackPine_bot worldsmith` in any chat and get results without switching to the bot conversation. Makes Forest searchable from everywhere in Telegram, not just the dedicated chat.

## 10. Export & Share

"Send me the last 5 captures as a markdown file" or "export all nodes tagged #project/kingdom as a PDF." Right now Forest data stays in Forest. Sometimes you need to pull it out for sharing, writing, or review.
