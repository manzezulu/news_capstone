# Daily Dispatch: Django News Application

A news platform where independent journalists and publishers submit articles, editors review and approve them, and readers subscribe to publishers or journalists. Approved articles are emailed to subscribers and logged to the project's own REST endpoint. Built for the HyperionDev / Stellenbosch University capstone.

**Stack:** Python 3.12, Django 5.2 LTS, Django REST Framework (token auth), MariaDB, Bootstrap 5, `requests`.

## Features

- Custom user model with roles: **Reader**, **Editor**, **Journalist**. Each role maps to a Django group with specific permissions, assigned automatically.
- Readers subscribe to publishers and journalists. For non-readers the subscription relations are always cleared.
- Journalists write articles (independent or for a publisher) and newsletters.
- Editors review and approve articles from a review queue.
- On approval (Django `post_save` signal): email to subscribers, then a POST to `/api/approved/`, exactly once per article.
- REST API with token authentication and role-based authorisation.
- 31 automated unit tests (mocking email and the approval endpoint).

## Requirements analysis

**Functional:** registration/login; role-based groups and permissions; article, newsletter and publisher management; subscriptions; editor approval; email and API notification; REST API (list approved, list subscribed, retrieve, create, update, delete); token auth.

**Non-functional:** PEP 8 (flake8 clean), modular code with docstrings, defensive coding (validation, exception handling around email/HTTP), least-privilege access control, 3NF database, MariaDB, secrets via environment variables, automated tests.

## Design

- ERD: [docs/ERD.md](docs/ERD.md)
- Full build tutorial and design rationale: [docs/TUTORIAL.md](docs/TUTORIAL.md)
- UI plan: login/register; article list (with "My feed" for readers); article detail; my articles; new/edit/delete article; editor review queue; newsletter list/detail/forms; subscriptions page. Navigation links appear only when the user holds the matching permission.

**Design decisions**

1. The `role` field is the single source of truth; the group is derived from it (`post_save` on the user).
2. Groups and permissions are created after every `migrate` (`post_migrate`), including in the test database.
3. Approval uses **signals (Option 1)**. A `notified` flag prevents duplicate sends; email and HTTP errors are caught so approval never fails because of them.
4. `/api/approved/` is protected by a shared secret header (`X-Internal-Token`) because it is called by the server itself.
5. Shared queries live in `news/selectors.py` so the web app and API cannot disagree about "subscribed" content.
6. "Only editors approve" is enforced in the serializer, covering POST, PUT and PATCH.

## Setup

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`mysqlclient` needs the MariaDB client headers on Linux: `sudo apt install libmariadb-dev pkg-config build-essential`.

**Database (MariaDB)**

```sql
CREATE DATABASE news_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'news_user'@'localhost' IDENTIFIED BY 'ChangeMe123!';
GRANT ALL PRIVILEGES ON news_db.* TO 'news_user'@'localhost';
GRANT ALL PRIVILEGES ON `test\_news\_db`.* TO 'news_user'@'localhost';
FLUSH PRIVILEGES;
```

Settings read `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` from the environment (defaults match the SQL above; see `.env.example`). For a quick run without MariaDB set `USE_SQLITE=1`.

**Run**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo          # optional: users jane, edna, rita (password DemoPass123!) + a demo publisher
python manage.py runserver
```

Emails print to the terminal (console backend). Approved articles are written to `approved_articles.log`.

## Demo walkthrough

1. Log in as **rita** (reader): Subscriptions shows Daily Planet, already subscribed by the seed.
2. Log in as **jane** (journalist): New article, choose the publisher.
3. Log in as **edna** (editor): Review queue, then Approve.
4. The terminal shows the email to rita and `approved_articles.log` gets an entry.
5. As rita, "My feed" now lists the article.

## Roles

| Role | Permissions |
|---|---|
| Reader | view articles, view newsletters |
| Editor | view, update, delete articles and newsletters; approve articles |
| Journalist | create, view, update, delete articles and newsletters |

## REST API

Authenticate with `POST /api/token/` (`username`, `password`), then send `Authorization: Token <token>`.

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/token/` | anyone |
| GET | `/api/articles/` | authenticated, approved articles (`?pending=true` for editors) |
| GET | `/api/articles/subscribed/` | readers, their subscriptions only |
| GET | `/api/articles/<id>/` | authenticated |
| POST | `/api/articles/` | journalists |
| PUT / PATCH | `/api/articles/<id>/` | journalists (own), editors (any); only editors can set `approved` |
| DELETE | `/api/articles/<id>/` | journalists (own), editors (any) |
| GET / POST | `/api/newsletters/` | view: all; create: journalists |
| GET / PUT / DELETE | `/api/newsletters/<id>/` | per role |
| GET | `/api/publishers/`, `/api/me/` | authenticated |
| POST | `/api/approved/` | internal, requires `X-Internal-Token` |

## Tests and code style

```bash
python manage.py test news -v 2     # 31 tests
flake8 .                            # PEP 8 (config in setup.cfg)
```

Tests cover role/group assignment, token auth, per-role API access, subscribed-only retrieval, journalist create, editor approve/delete, newsletters, the approval signal (email recipients, single send, API failure tolerance) and web access control.

## Project structure

```
news_project/     settings, root URLs
news/
  models.py       Publisher, CustomUser, Article, Newsletter
  signals.py      role groups + approval notifications
  selectors.py    shared queries
  views.py forms.py urls.py      web front end
  serializers.py api_permissions.py api_views.py api_urls.py   REST API
  admin.py tests.py
  management/commands/seed_demo.py
  templates/news/ templates: templates/base.html, registration/
docs/             ERD and tutorial
```
