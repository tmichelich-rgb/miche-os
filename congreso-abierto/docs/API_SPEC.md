# Congreso Abierto — API Specification v0.1.0

Base URL: `http://localhost:3000/api/v1`
Documentation: `http://localhost:3000/api/docs` (Swagger UI)

---

## Legislators

### GET /legislators
List legislators with pagination and filters.

**Query Parameters:**
| Param      | Type    | Default | Description                     |
|------------|---------|---------|---------------------------------|
| page       | number  | 1       | Page number                     |
| limit      | number  | 20      | Items per page (max 100)        |
| blockId    | string  | -       | Filter by block ID              |
| provinceId | string  | -       | Filter by province ID           |
| search     | string  | -       | Search by name (case insensitive) |
| isActive   | boolean | true    | Filter by active status         |

**Response:** `{ data: Legislator[], meta: { total, page, limit, totalPages } }`

### GET /legislators/:id
Get legislator profile with KPIs, commissions, recent bills, and votes.

**Response:** Full Legislator object with nested relations.

### GET /legislators/:id/metrics
Get computed metrics for a legislator.

**Query Parameters:**
| Param  | Type   | Description              |
|--------|--------|--------------------------|
| period | string | Filter by period (e.g. "2024") |

**Response:** `LegislatorMetric[]`

### GET /legislators/:id/activity
Get legislator activity timeline (bills, votes, attendance).

**Query Parameters:** page, limit

**Response:** `{ bills, votes, attendances }`

---

## Bills

### GET /bills
List bills with pagination and filters.

**Query Parameters:**
| Param    | Type       | Description                |
|----------|------------|----------------------------|
| page     | number     | Page number                |
| limit    | number     | Items per page             |
| status   | BillStatus | Filter by status           |
| type     | BillType   | Filter by type             |
| search   | string     | Search title or expediente |
| authorId | string     | Filter by author legislator|
| period   | string     | Filter by period           |

**Response:** `{ data: Bill[], meta: PaginationMeta }`

### GET /bills/:id
Get bill details with authors, movements, and source references.

**Response:** Full Bill with relations.

---

## Feed

### GET /feed
Get feed posts (auto-generated parliamentary events).

**Query Parameters:**
| Param      | Type         | Description               |
|------------|--------------|---------------------------|
| page       | number       | Page number               |
| limit      | number       | Items per page            |
| type       | FeedPostType | BILL_CREATED, BILL_MOVEMENT, VOTE_RESULT, ATTENDANCE_RECORD |
| blockId    | string       | Filter by block           |
| provinceId | string       | Filter by province        |
| tags       | string       | Comma-separated tags      |

**Response:** `{ data: FeedPost[], meta: PaginationMeta }`

### GET /feed/:id
Get single feed post with details.

---

## Comments

### GET /comments/post/:feedPostId
Get comments for a feed post (threaded).

**Query Parameters:** page, limit

### POST /comments
Create a comment.

**Body:** `{ body: string, feedPostId: string, userId: string, parentId?: string }`

### DELETE /comments/:id
Soft-delete (hide) a comment. Requires userId in body for ownership check.

### POST /comments/:id/report
Report a comment.

**Body:** `{ userId: string, reason: ReportReason, details?: string }`

---

## Reactions

### GET /reactions/post/:feedPostId
Get reaction counts by type for a feed post.

**Response:** `{ feedPostId, counts: Record<ReactionType, number>, total }`

### POST /reactions/toggle
Toggle a reaction (add or remove).

**Body:** `{ feedPostId: string, userId: string, type: ReactionType }`

**Response:** `{ action: "added" | "removed", type }`

---

## Search

### GET /search
Search across legislators and bills via Meilisearch.

**Query Parameters:**
| Param | Type   | Description                    |
|-------|--------|--------------------------------|
| q     | string | Search query (required)        |
| index | string | Specific index to search       |
| limit | number | Max results per index          |

### POST /search/reindex
Trigger full reindex of all data.

---

## Enums

### BillStatus
PRESENTED, IN_COMMITTEE, WITH_OPINION, APPROVED_COMMITTEE, FLOOR_VOTE, APPROVED_CHAMBER, SENT_TO_OTHER_CHAMBER, APPROVED, REJECTED, WITHDRAWN, EXPIRED, ARCHIVED

### BillType
PROJECT, RESOLUTION, DECLARATION, COMMUNICATION, OTHER

### FeedPostType
BILL_CREATED, BILL_MOVEMENT, VOTE_RESULT, ATTENDANCE_RECORD

### ReactionType
INFORMATIVE, IMPORTANT, CONCERNING, POSITIVE

### ReportReason
SPAM, HARASSMENT, MISINFORMATION, DOXXING, THREAT, OFF_TOPIC, OTHER
