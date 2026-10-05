# Entity Relationship Diagram

```mermaid
erDiagram
    CUSTOMUSER ||--o{ ARTICLE : "authors"
    CUSTOMUSER ||--o{ NEWSLETTER : "authors"
    PUBLISHER ||--o{ ARTICLE : "has (optional)"
    PUBLISHER }o--o{ CUSTOMUSER : "editors"
    PUBLISHER }o--o{ CUSTOMUSER : "journalists"
    CUSTOMUSER }o--o{ PUBLISHER : "subscribed_publishers"
    CUSTOMUSER }o--o{ CUSTOMUSER : "subscribed_journalists"
    NEWSLETTER }o--o{ ARTICLE : "contains"

    CUSTOMUSER { int id PK
        string username
        string email
        string role }
    PUBLISHER { int id PK
        string name
        text description }
    ARTICLE { int id PK
        string title
        text content
        int author_id FK
        int publisher_id FK "nullable"
        datetime created_at
        bool approved
        bool notified }
    NEWSLETTER { int id PK
        string title
        text description
        int author_id FK
        datetime created_at }
```

Normalised to 3NF: every many-to-many relationship is held in its own join table, publisher data lives only in `Publisher`, and an article's independent/publisher status is derived from `publisher IS NULL`.
