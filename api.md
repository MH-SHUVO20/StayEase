# API Contract

This file describes the two API endpoints needed for the StayEase chat system. The backend is expected to receive the guest message, call the LangGraph agent, save the conversation, and return the assistant response.

## POST `/api/chat/{conversation_id}/message`

This endpoint sends one guest message to the agent.

### Request Schema

Path parameter:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation_id` | `string` | yes | Id of the current conversation. |

Body:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `message` | `string` | yes | Message written by the guest. |
| `guest_name` | `string` | no | Guest name if it is already known. |

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
| `conversation_id` | `string` | Id of the current conversation. |
| `reply` | `string` | Final message returned by the agent. |
| `intent` | `string` | Detected intent such as `search`, `details`, `book`, or `escalate`. |
| `tool_results` | `object` | Data returned by a tool, if any tool was used. |

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

Status code: `400 Bad Request`

```json
{
  "detail": "Message is required."
}
```

Status code: `404 Not Found`

```json
{
  "detail": "Conversation not found."
}
```

Status code: `503 Service Unavailable`

```json
{
  "detail": "Agent service is temporarily unavailable."
}
```

## GET `/api/chat/{conversation_id}/history`

This endpoint returns the saved message history of one conversation.

### Request Schema

Path parameter:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation_id` | `string` | yes | Id of the current conversation. |

### Request Example

```http
GET /api/chat/conv-1001/history
```

### Response Schema

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | `string` | Id of the current conversation. |
| `messages` | `array` | List of saved messages. |

Message object:

| Field | Type | Description |
| --- | --- | --- |
| `role` | `string` | `guest`, `assistant`, or `tool`. |
| `content` | `string` | Text content of the message. |
| `created_at` | `string` | Time when the message was saved. |

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

Status code: `404 Not Found`

```json
{
  "detail": "Conversation not found."
}
```

Status code: `500 Internal Server Error`

```json
{
  "detail": "Could not load conversation history."
}
```
