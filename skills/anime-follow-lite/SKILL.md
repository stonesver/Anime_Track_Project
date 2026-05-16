---
name: anime-follow-lite
description: Use when implementing the first, most lightweight version of AnimeCode's follow-anime feature, including searching an anime, adding or canceling a user's subscription, listing followed anime, and preserving a migration path to the full core system.
---

# Anime Follow Lite

Use this skill when the user asks to implement, revise, or review the first lightweight version of the AnimeCode follow-anime feature.

## Project Context

Read these project design files before making implementation decisions:

- `01-core-architecture-design.md`: full core system boundaries and deployment direction.
- `02-core-detailed-design.md`: domain models, especially `Anime`, `BotUser`, and `Subscription`.
- `03-openclaw-llm-plugin-design.md`: Tool API safety and OpenClaw permission boundaries.
- `05-agent-skills-query-layer-design.md`: lightweight Agent + Skills query layer and unified result schema.

The lightweight version must keep the same domain vocabulary as the full design so it can later migrate into the core system.

## Version Boundary

Implement only the smallest persistent follow-anime loop:

1. Search or resolve an anime candidate.
2. Create or restore a user's subscription.
3. Cancel, pause, or resume a subscription.
4. List a user's active subscriptions.
5. Return structured results suitable for QQ, CLI, Web, or Agent callers.

Do not implement these in the lightweight version unless the user explicitly expands scope:

- scheduled reminders or proactive QQ pushes
- qBittorrent, RSS rules, or download status
- OpenClaw direct database access
- batch subscribe or destructive bulk actions
- production deployment, worker processes, or container orchestration

## Minimal Data Contract

Use persistent storage. Prefer SQLite because the project design names SQLite as the MVP database.

Keep the first schema small but compatible with the full design:

- `anime`: `id`, `season`, `title_cn`, `title_jp`, `title_en`, `weekday`, `air_time`, `source`, `external_id`, `external_url`, `created_at`, `updated_at`
- `bot_user`: `id`, `platform`, `platform_user_id`, `display_name`, `timezone`, `created_at`, `updated_at`
- `subscription`: `id`, `user_id`, `anime_id`, `status`, `remind_enabled`, `remind_before_minutes`, `remind_channel`, `created_at`, `updated_at`

Required uniqueness:

- `bot_user`: unique by `(platform, platform_user_id)`
- `subscription`: unique by `(user_id, anime_id)`

For cancellation, prefer soft state changes:

- active subscription -> `status = "dropped"`
- re-follow existing dropped subscription -> restore `status = "active"`

## Tool / Service Surface

Expose deterministic functions or API endpoints with this shape. The exact framework can follow the existing codebase once code exists.

### `search_anime`

Purpose: find anime candidates before following.

Input:

```json
{
  "query": "番名或别名",
  "season": "current",
  "limit": 5
}
```

Output:

```json
{
  "ok": true,
  "items": [
    {
      "anime_id": 1,
      "title_cn": "示例番剧",
      "title_jp": null,
      "season": "2026-04",
      "weekday": 3,
      "air_time": "22:00",
      "confidence": 0.92
    }
  ]
}
```

### `create_subscription`

Purpose: add or restore one follow record for one user and one anime.

Input:

```json
{
  "platform": "qq",
  "platform_user_id": "123456",
  "anime_id": 1,
  "remind_before_minutes": 0,
  "remind_channel": "private"
}
```

Behavior:

- If the user does not exist, create it.
- If an active subscription already exists, return it without creating a duplicate.
- If a dropped subscription exists, restore it to active.
- If `anime_id` does not exist, return a structured `not_found` error.

### `cancel_subscription`

Purpose: cancel one follow record without deleting history.

Input:

```json
{
  "platform": "qq",
  "platform_user_id": "123456",
  "anime_id": 1
}
```

Behavior:

- If the subscription exists, set `status = "dropped"`.
- If it is already dropped, return success with an idempotent message.
- Do not delete rows.

### `get_user_subscriptions`

Purpose: list the user's followed anime.

Input:

```json
{
  "platform": "qq",
  "platform_user_id": "123456",
  "status": "active"
}
```

Output should include anime title, season, weekday, air time, status, and subscription id.

## Agent Safety Rules

- The Agent may call the service/tool functions; it must not write the database directly.
- Search and list operations are low risk.
- Single create/cancel operations are acceptable for V1.
- Batch operations, RSS creation, qB changes, and group-wide actions require a separate confirmation flow in later versions.
- Never expose `.env`, raw database credentials, qB credentials, server shell, or arbitrary file writes as skill capabilities.

## Implementation Procedure

1. Inspect the current repo and preserve existing architecture if code already exists.
2. If no code exists, scaffold the smallest app or module needed for the requested runtime.
3. Keep business logic in a service layer, not in bot command handlers or Agent prompts.
4. Keep user identity explicit: always pass `platform` and `platform_user_id`.
5. Normalize titles only for matching; preserve original titles for display.
6. Make subscribe and cancel idempotent.
7. Add focused tests for duplicate subscribe, restore dropped subscription, cancel missing subscription, and list filtering.
8. Document the exact commands used to run tests or local verification.

## Acceptance Criteria

The lightweight feature is done only when:

- A user can search an anime candidate.
- A user can follow the anime once without duplicates.
- A repeated follow returns the same active subscription.
- A canceled subscription is soft-dropped.
- Following again restores the dropped subscription.
- Listing active subscriptions hides dropped entries by default.
- The implementation has a clear path to the full `Anime`, `BotUser`, and `Subscription` models from the design docs.
