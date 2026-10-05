    sequenceDiagram
    autonumber
    actor J as Journalist
    actor E as Editor
    participant W as Web App
    participant DB as Database
    participant S as Signal Handler
    participant M as Mail Server
    participant WH as /api/approved/
    actor R as Subscriber

    Note over J,R: Phase 1 — Journalist creates an article

    J->>W: GET /articles/new/
    W-->>J: Article form
    J->>W: POST title, content, publisher
    W->>W: form.instance.author = request.user
    W->>DB: INSERT Article (status=pending)
    DB-->>W: article_id
    W-->>J: Redirect to "My articles"

    Note over J,R: Phase 2 — Editor reviews and approves

    E->>W: GET /review/
    W->>DB: SELECT * FROM article WHERE approved=False
    DB-->>W: [pending articles]
    W-->>E: Review queue page

    E->>W: POST /review/{id}/approve/
    W->>DB: SELECT Article WHERE id={id}
    DB-->>W: article
    W->>DB: UPDATE Article SET approved=True
    DB-->>W: ok

    Note over W,S: post_save fires synchronously

    DB->>S: post_save(Article)
    activate S
    S->>S: if not approved or notified: return
    S->>DB: SELECT emails FROM users WHERE subscribed_journalists=author OR subscribed_publishers=publisher
    DB-->>S: [subscriber emails]

    S->>M: send_mass_mail(recipients, subject, body)
    activate M
    M-->>S: 3 emails sent
    deactivate M

    S->>WH: POST /api/approved/ (X-Internal-Token)
    activate WH
    WH->>WH: Validate token
    WH->>WH: Log payload to approved_articles.log
    WH-->>S: 201 Created
    deactivate WH

    S->>DB: UPDATE Article SET notified=True
    S-->>W: return
    deactivate S

    W-->>E: Redirect to review queue
    W-->>E: Toast: "Article approved and sent out."

    Note over J,R: Phase 3 — Subscriber receives notification

    M->>R: Email: "New article: ..."
    R->>W: Click link in email
    W->>DB: SELECT Article WHERE id={id}
    DB-->>W: article
    W-->>R: Article detail page


    sequenceDiagram
    autonumber
    actor R as Reader
    participant W as Web App
    participant DB as Database

    R->>W: GET /subscriptions/
    W->>DB: SELECT publishers, journalists
    W->>DB: SELECT current subscriptions for user
    DB-->>W: all + user's IDs
    W-->>R: Subscriptions page (buttons reflect state)

    R->>W: POST /subscriptions/publisher/{id}/toggle/
    W->>W: Check user.role == 'reader'
    W->>DB: SELECT subscribed_publishers WHERE user={id} AND publisher={id}
    alt Already subscribed
        W->>DB: DELETE from join table
        W-->>R: Toast "Unsubscribed from ..."
    else Not yet subscribed
        W->>DB: INSERT into join table
        W-->>R: Toast "Subscribed to ..."
    end

    R->>W: GET /articles/?feed=subscribed
    W->>W: user.role == 'reader' and feed == 'subscribed'
    W->>DB: SELECT approved articles WHERE<br/>author IN (subscribed_journalists)<br/>OR publisher IN (subscribed_publishers)
    DB-->>W: [articles]
    W-->>R: Personal feed page

    sequenceDiagram
    autonumber
    actor C as API Client
    participant T as /api/token/
    participant A as Article List View
    participant P as RolePermission
    participant DB as Database

    C->>T: POST {username, password}
    T->>DB: SELECT user WHERE username
    DB-->>T: user + hashed password
    T->>T: Verify password
    alt Valid credentials
        T->>DB: Get or create Token
        DB-->>T: token
        T-->>C: 200 {token: "abc123..."}
    else Invalid
        T-->>C: 400 Bad Request
    end

    Note over C,DB: Client stores token for subsequent requests

    C->>A: GET /api/articles/ (Authorization: Token abc123)
    A->>P: has_permission(request, view)
    P->>P: method_actions["GET"] = "view"
    P->>DB: user.has_perm("news.view_article")
    DB-->>P: True (Reader group has it)
    P-->>A: Allow

    A->>DB: SELECT approved articles
    DB-->>A: [articles]
    A-->>C: 200 [{...}, {...}]

    sequenceDiagram
    autonumber
    actor U as User
    participant W as Admin / Web
    participant DB as Database
    participant S as sync_role_group
    participant G as Group Table

    U->>W: Save user with role="journalist"
    W->>DB: UPDATE CustomUser SET role="journalist"
    DB-->>W: ok

    Note over DB,S: post_save fires

    DB->>S: post_save(CustomUser)
    activate S

    alt role != reader
        S->>DB: DELETE subscribed_publishers
        S->>DB: DELETE subscribed_journalists
    end

    S->>G: Remove user from Reader/Editor/Journalist groups
    G-->>S: ok
    S->>G: Add user to "Journalist" group
    G-->>S: ok
    deactivate S

    W-->>U: Saved. Permissions updated.


    sequenceDiagram
    autonumber
    actor E as Editor
    participant W as Web App
    participant S as Signal Handler
    participant M as Mail Server
    participant WH as Webhook
    participant DB as Database

    E->>W: POST /review/{id}/approve/
    W->>DB: UPDATE Article SET approved=True
    DB->>S: post_save fires
    activate S

    S->>M: send_mass_mail(...)
    activate M
    M--xS: SMTPException: connection refused
    deactivate M

    S->>S: except (SMTPException, OSError): log error, continue

    S->>WH: POST /api/approved/
    activate WH
    WH--xS: RequestException: timeout
    deactivate WH

    S->>S: except RequestException: log warning, continue

    S->>DB: UPDATE Article SET notified=True
    S-->>W: return (no exception raised)
    deactivate S

    W-->>E: 302 Redirect + Toast "Approved and sent out."
    Note over E,DB: Article is approved.<br/>Notifications failed silently.<br/>Errors visible in server logs.


    stateDiagram-v2
    [*] --> Draft: Journalist creates
    Draft --> Pending: Submitted for review
    Pending --> Approved: Editor approves
    Pending --> Rejected: Editor rejects (with reason)
    Rejected --> Pending: Journalist revises and resubmits
    Approved --> [*]: Published
    Rejected --> [*]: Abandoned

    note right of Approved
        Fires email + webhook
        exactly once via notified flag
    end note
