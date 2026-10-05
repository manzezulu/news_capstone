"""Seed the database with South African demo content.

Usage:
    python manage.py seed_demo            # idempotent - skips what exists
    python manage.py seed_demo --reset    # wipes demo data first, then reseeds

All users share the same password (see PASSWORD below).
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from news.models import Article, Newsletter, Publisher

User = get_user_model()

PASSWORD = 'Mzanzi2026!'


# ---------------------------------------------------------------------------
# Users — two per role
# ---------------------------------------------------------------------------
USERS = [
    # Readers
    ('manzezulu', 'manzezulu@example.co.za', 'reader', 'Manzezulu', 'Dlamini'),
    ('rain',      'rain@example.co.za',      'reader', 'Rain',      'Mokoena'),

    # Journalists
    ('kwenza',    'kwenza@example.co.za',    'journalist', 'Kwenza',   'Ndlovu'),
    ('themba',    'themba@example.co.za',    'journalist', 'Themba',   'Sithole'),

    # Editors
    ('mkhwanazi', 'mkhwanazi@example.co.za', 'editor', 'Sipho',    'Mkhwanazi'),
    ('simphiwe',  'simphiwe@example.co.za',  'editor', 'Simphiwe', 'Khumalo'),
]


# ---------------------------------------------------------------------------
# Publishers — SA-flavoured mastheads
# ---------------------------------------------------------------------------
PUBLISHERS = [
    {
        'name': 'The Cape Chronicle',
        'description': 'A Cape Town daily covering the Mother City and the Western Cape.',
        'editors': ['mkhwanazi'],
        'journalists': ['kwenza', 'themba'],
    },
    {
        'name': 'Highveld Herald',
        'description': 'Johannesburg-based reporting on Gauteng business, politics, and culture.',
        'editors': ['simphiwe'],
        'journalists': ['kwenza'],
    },
    {
        'name': 'KZN Coastal Times',
        'description': 'Durban and KwaZulu-Natal storytelling — from the harbour to the Drakensberg.',
        'editors': ['mkhwanazi', 'simphiwe'],
        'journalists': ['themba'],
    },
]


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------
ARTICLES = [
    {
        'title': 'Taxi Associations Trial Cashless Payments Across Soweto Routes',
        'content': (
            'Three of Soweto\u2019s largest taxi associations have begun a six-month pilot '
            'for cashless fare collection on the busiest routes between Orlando, Dobsonville, '
            'and the Johannesburg CBD.\n\n'
            'Commuters now tap a preloaded card or scan a QR code at the door. The associations '
            'say the system cuts queue times, reduces armed robbery risk, and gives drivers a '
            'verifiable daily record of earnings.\n\n'
            '\u201cWe have been talking about this for years,\u201d said a route marshal at Baragwanath '
            'rank. \u201cNow we are actually doing it.\u201d\n\n'
            'The pilot covers roughly 40,000 daily passengers. If it holds, the association says '
            'it will roll out to 200 vehicles by next winter.'
        ),
        'author': 'kwenza',
        'publisher': 'Highveld Herald',
        'approved': True,
    },
    {
        'title': 'Table Mountain Fynbos Recovery Project Passes First Milestone',
        'content': (
            'A five-year effort to regrow native fynbos on fire-scarred slopes above Cape Town '
            'has reached its first planting milestone, with volunteers and SANParks rangers '
            'putting more than 12,000 endemic seedlings into the ground this season.\n\n'
            'The species list reads like a botanist\u2019s wish list: king proteas, silver trees, '
            'buchu, and several ericas found nowhere else on Earth.\n\n'
            'Fire is not the enemy here \u2014 it is part of the cycle. The trick, rangers say, is '
            'making sure the mountain burns at the right intervals, and that invasives do not '
            'win the race afterwards.'
        ),
        'author': 'kwenza',
        'publisher': 'The Cape Chronicle',
        'approved': True,
    },
    {
        'title': 'Durban Harbour Expansion Sparks Debate Over Local Fishing Grounds',
        'content': (
            'The long-awaited expansion of Durban Harbour has entered its environmental '
            'assessment phase, and small-scale fishers are asking hard questions about what '
            'dredging will do to the prawn and sardine runs they depend on.\n\n'
            'Port authorities argue the expansion is essential for container traffic and jobs. '
            'Fisher co-operatives want a co-managed marine protected zone as compensation.\n\n'
            'Public comment closes at the end of next month.'
        ),
        'author': 'themba',
        'publisher': 'KZN Coastal Times',
        'approved': True,
    },
    {
        'title': 'How Stellenbosch Wine Farms Are Adapting to Warmer Seasons',
        'content': (
            'Winemakers in the Cape Winelands are quietly rewriting decades-old playbooks.\n\n'
            'Earlier harvests, new varietals from Portugal and southern Italy, and shade nets '
            'are all part of the response to warmer, drier summers. Some estates are moving '
            'vineyards uphill in search of cooler nights.\n\n'
            '\u201cWe cannot fight the climate,\u201d one cellar master said. \u201cWe can only '
            'read it faster than our neighbours.\u201d'
        ),
        'author': 'themba',
        'publisher': None,   # independent
        'approved': True,
    },
    {
        'title': 'Joburg Inner-City Rooftop Gardens Feed 900 Households',
        'content': (
            'An unlikely food network has taken root on the rooftops of Braamfontein and '
            'Hillbrow: 22 gardens, run by residents and a handful of NGOs, that together now '
            'supply fresh vegetables to nearly 900 households.\n\n'
            'Spinach, kale, tomatoes, and herbs grow in repurposed crates. Grey water from '
            'nearby buildings is filtered and reused.\n\n'
            'The project started as a lockdown workaround. It has become permanent infrastructure.'
        ),
        'author': 'kwenza',
        'publisher': None,   # independent
        'approved': True,
    },
    {
        'title': 'South Africa\u2019s First Grid-Scale Battery Storage Site Comes Online',
        'content': (
            'A 300 MWh battery installation in the Northern Cape has begun feeding power '
            'into the national grid, marking the country\u2019s first grid-scale storage project.\n\n'
            'The site stores surplus solar power generated during the day and releases it '
            'during the evening peak, easing pressure on Eskom\u2019s ageing coal fleet.\n\n'
            'Two more sites are under construction and expected online within eighteen months.'
        ),
        'author': 'themba',
        'publisher': 'Highveld Herald',
        'approved': True,
    },
    {
        'title': 'A Pending Story: Cape Flats Cycling Clubs Seek Municipal Support',
        'content': (
            'Cycling clubs across the Cape Flats are asking the city for safer routes and '
            'shared storage facilities.\n\n'
            'This article is deliberately left unapproved so it shows up in the review queue '
            'for editors to practise approving, rejecting, or editing.'
        ),
        'author': 'kwenza',
        'publisher': 'The Cape Chronicle',
        'approved': False,
    },
    {
        'title': 'A Pending Story: Durban Poets Launch Mobile Reading Room',
        'content': (
            'A retrofitted minibus has become a roving reading room in Durban North, '
            'stocked with donated poetry, novels, and children\u2019s books.\n\n'
            'Left unapproved so editors can exercise the review workflow.'
        ),
        'author': 'themba',
        'publisher': 'KZN Coastal Times',
        'approved': False,
    },
]


# ---------------------------------------------------------------------------
# Newsletters
# ---------------------------------------------------------------------------
NEWSLETTERS = [
    {
        'title': 'The Weekly Dispatch',
        'description': 'A Sunday roundup of the week\u2019s best stories from across our titles.',
        'author': 'kwenza',
    },
    {
        'title': 'The Coastal Report',
        'description': 'Durban and KZN stories — harbour, hills, and hinterland.',
        'author': 'themba',
    },
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------
class Command(BaseCommand):
    help = 'Seed the database with South African demo content.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo data before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting demo data…')
            Article.objects.filter(
                title__in=[a['title'] for a in ARTICLES]
            ).delete()
            Newsletter.objects.filter(
                title__in=[n['title'] for n in NEWSLETTERS]
            ).delete()
            Publisher.objects.filter(
                name__in=[p['name'] for p in PUBLISHERS]
            ).delete()
            User.objects.filter(
                username__in=[u[0] for u in USERS]
            ).delete()

        users = self._make_users()
        publishers = self._make_publishers(users)
        self._make_articles(users, publishers)
        self._make_newsletters(users, publishers)
        self._subscribe_readers(users, publishers)

        self.stdout.write(self.style.SUCCESS('\nDemo data ready.'))
        self.stdout.write(f'  Shared password: {PASSWORD}\n')
        self.stdout.write('  Readers')
        self.stdout.write('    manzezulu  (Manzezulu Dlamini)')
        self.stdout.write('    rain       (Rain Mokoena)')
        self.stdout.write('  Journalists')
        self.stdout.write('    kwenza     (Kwenza Ndlovu)')
        self.stdout.write('    themba     (Themba Sithole)')
        self.stdout.write('  Editors')
        self.stdout.write('    mkhwanazi  (Sipho Mkhwanazi)')
        self.stdout.write('    simphiwe   (Simphiwe Khumalo)')

    # -- helpers ------------------------------------------------------------
    def _make_users(self):
        users = {}
        for username, email, role, first, last in USERS:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'role': role},
            )
            user.email = email
            user.role = role
            user.first_name = first
            user.last_name = last
            user.set_password(PASSWORD)
            user.save()
            users[username] = user
        return users

    def _make_publishers(self, users):
        publishers = {}
        for spec in PUBLISHERS:
            publisher, _ = Publisher.objects.get_or_create(
                name=spec['name'],
                defaults={'description': spec['description']},
            )
            publisher.description = spec['description']
            publisher.save()
            publisher.editors.set([users[u] for u in spec['editors']])
            publisher.journalists.set([users[u] for u in spec['journalists']])
            publishers[spec['name']] = publisher
        return publishers

    def _make_articles(self, users, publishers):
        for spec in ARTICLES:
            Article.objects.update_or_create(
                title=spec['title'],
                defaults={
                    'content': spec['content'],
                    'author': users[spec['author']],
                    'publisher': publishers.get(spec['publisher']),
                    'approved': spec['approved'],
                    'notified': True,   # never re-fire the approval signal
                },
            )

    def _make_newsletters(self, users, publishers):
        for spec in NEWSLETTERS:
            newsletter, _ = Newsletter.objects.get_or_create(
                title=spec['title'],
                defaults={
                    'description': spec['description'],
                    'author': users[spec['author']],
                },
            )
            newsletter.description = spec['description']
            newsletter.save()
            approved = Article.objects.filter(approved=True)
            # Give each newsletter its own flavour: Kwenza's gets Cape/Highveld,
            # Themba's gets KZN + independent.
            if spec['author'] == 'kwenza':
                approved = approved.filter(publisher__in=[
                    publishers['The Cape Chronicle'],
                    publishers['Highveld Herald'],
                ])
            else:
                approved = approved.filter(publisher__in=[
                    publishers['KZN Coastal Times'],
                ]) | approved.filter(publisher__isnull=True)
            newsletter.articles.set(approved)

    def _subscribe_readers(self, users, publishers):
        # Manzezulu follows The Cape Chronicle + Kwenza.
        users['manzezulu'].subscribed_publishers.set([
            publishers['The Cape Chronicle'],
        ])
        users['manzezulu'].subscribed_journalists.set([
            users['kwenza'],
        ])

        # Rain follows KZN Coastal Times + Themba.
        users['rain'].subscribed_publishers.set([
            publishers['KZN Coastal Times'],
        ])
        users['rain'].subscribed_journalists.set([
            users['themba'],
        ])