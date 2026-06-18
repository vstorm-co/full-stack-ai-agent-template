# Using Message Ratings

Users can rate AI assistant responses to provide feedback on answer quality.
This feedback helps improve the AI and gives administrators insight into response quality.

## Rating Messages

### Like/Dislike

Each AI assistant message displays two buttons:

- **Like (👍)** — Click to indicate the response was helpful
- **Dislike (👎)** — Click to indicate the response had issues

### Toggle Behavior

- Clicking the same button again **removes** your rating
- Clicking the opposite button **changes** your rating (like → dislike or vice versa)
- Only assistant messages can be rated (not your own messages)

### Adding Feedback

When you dislike a response, a dialog appears asking **"What went wrong?"**

You can optionally provide a comment (up to 2000 characters) explaining the issue.
This feedback is valuable for understanding why responses weren't helpful.

Common reasons to dislike:

- Incorrect or hallucinated information
- Response didn't address the question
- Too verbose or too brief
- Poor formatting or structure

## Rating Counts

Each message shows the total number of likes and dislikes from all users.
Your own rating is highlighted (green for like, red for dislike).

## For Administrators

### Ratings Dashboard

Navigate to **Admin → Response Ratings** (or `/admin/ratings`) to access the analytics dashboard.

#### Summary Statistics

- **Total ratings** — All ratings across the system
- **Likes** — Count of positive ratings
- **Dislikes** — Count of negative ratings
- **Average** — Overall satisfaction score (-1.0 to 1.0)

#### Ratings Chart

A bar chart shows ratings over time (default: last 30 days).
Green bars represent likes, red bars represent dislikes.

Use the **Days** dropdown to adjust the time window (7, 30, 90, or 365 days).

### Filtering Ratings

Use the filter dropdowns to narrow down results:

| Filter | Options |
|--------|---------|
| Rating type | All / Likes Only / Dislikes Only |
| Comments | All / With comments only |

### Ratings Table

The table shows individual ratings with:

- **Date** — When the rating was submitted
- **Rating** — 👍 Like or 👎 Dislike
- **Comment** — Feedback text (if provided)
- **Message** — Preview of the rated response
- **User** — Who submitted the rating
- **Actions** — Link to view the full conversation

### Exporting Data

Export ratings for external analysis:

- **JSON** — Full structured data, suitable for scripts and analysis tools
- **CSV** — Spreadsheet-compatible format for Excel or Google Sheets

Exports respect the current filters (e.g., export only dislikes with comments).

### Viewing Conversations

Click **"View conversation"** on any rating to open the chat interface with that conversation loaded.
This is useful for understanding the context of a rating.

## Admin Conversations Page

Navigate to **Admin → All Conversations** (or `/admin/conversations`) to view all user conversations.

This page provides:

- Searchable list of all conversations
- Filter by user email or username
- Filter by date range (preset or custom)
- Quick links to view conversation details

## Direct Conversation Links

You can share a direct link to a specific conversation by adding the `id` parameter to the chat URL:

```
http://localhost:3000/chat?id=550e8400-e29b-41d4-a716-446655440000
```

This is useful for:

- Sharing conversation context with team members
- Bookmarking important conversations
- Linking from external tools or documentation

Click **"View conversation"** from any rating or the admin conversations list to open a direct link.

## API Access

For programmatic access to ratings data, use the admin API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/ratings` | GET | List ratings with pagination and filters |
| `/admin/ratings/summary` | GET | Aggregate statistics |
| `/admin/ratings/export` | GET | Export ratings (JSON/CSV) |
| `/admin/conversations` | GET | List all conversations |

All admin endpoints require admin authentication via JWT token.
