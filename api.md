# API Contract

## POST `/api/chat/{conversation_id}/message`

Send a guest message to the StayEase AI agent.

### Request Schema

Path parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation_id` | `string` | yes | Unique conversation ID. |

Body:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `message` | `string` | yes | Guest message text. |
| `guest_name` | `string` | no | Guest name if known. |

### Request Example

```http
POST /api/chat/conv-1001/message
Content-Type: application/json
```

```json
{
  "message": "I need a room in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests",
  "guest_name": "Nusrat Jahan"
}
```

### Response Schema

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | `string` | Conversation ID. |
| `reply` | `string` | Agent response for the guest. |
| `intent` | `string` | Detected intent: `search`, `details`, `book`, or `escalate`. |
| `tool_results` | `object` | Latest tool output, if a tool was used. |

### Response Example

```json
{
  "conversation_id": "conv-1001",
  "reply": "Hello Nusrat! I found 2 available stays in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests. Sea Breeze Villa is BDT 4,500 per night, and Ocean View Resort is BDT 6,200 per night.",
  "intent": "search",
  "tool_results": {
    "properties": [
      {
        "listing_id": "LST-001",
        "title": "Sea Breeze Villa",
        "location": "Cox's Bazar",
        "price_per_night": 4500,
        "currency": "BDT",
        "max_guests": 4,
        "rating": 4.8
      },
      {
        "listing_id": "LST-002",
        "title": "Ocean View Resort",
        "location": "Cox's Bazar",
        "price_per_night": 6200,
        "currency": "BDT",
        "max_guests": 6,
        "rating": 4.5
      }
    ]
  }
}
```

### Possible Error Responses

```json
{
  "detail": "Message is required."
}
```

Status code: `400 Bad Request`

```json
{
  "detail": "Conversation not found."
}
```

Status code: `404 Not Found`

```json
{
  "detail": "Agent service is temporarily unavailable."
}
```

Status code: `503 Service Unavailable`

## GET `/api/chat/{conversation_id}/history`

Get the full conversation history for a guest chat.

### Request Schema

Path parameters:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation_id` | `string` | yes | Unique conversation ID. |

### Request Example

```http
GET /api/chat/conv-1001/history
```

### Response Schema

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | `string` | Conversation ID. |
| `messages` | `array` | Stored chat messages. |

Each message:

| Field | Type | Description |
| --- | --- | --- |
| `role` | `string` | `guest`, `assistant`, or `tool`. |
| `content` | `string` | Message content. |
| `created_at` | `string` | ISO timestamp. |

### Response Example

```json
{
  "conversation_id": "conv-1001",
  "messages": [
    {
      "role": "guest",
      "content": "I need a room in Cox's Bazar from 2026-05-10 to 2026-05-12 for 2 guests",
      "created_at": "2026-04-27T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Hello Nusrat! I found 2 available stays in Cox's Bazar. Sea Breeze Villa is BDT 4,500 per night, and Ocean View Resort is BDT 6,200 per night.",
      "created_at": "2026-04-27T10:30:03Z"
    }
  ]
}
```

### Possible Error Responses

```json
{
  "detail": "Conversation not found."
}
```

Status code: `404 Not Found`

```json
{
  "detail": "Could not load conversation history."
}
```

Status code: `500 Internal Server Error`
