from django.test.runner import DiscoverRunner


class KeepDatabaseRunner(DiscoverRunner):
    """Django's test runner, but it always keeps the test database.

    Supabase's connection pooler can keep a connection to `test_postgres` open, so
    Django can't drop that database when the tests end. Keeping it (the same as
    `--keepdb`) lets a plain `python manage.py test` run without a "delete the test
    database?" prompt or a teardown error. Each test still runs in its own
    transaction that is rolled back, so no test data is left behind.
    """

    def __init__(self, *args, keepdb=True, **kwargs):
        super().__init__(*args, keepdb=True, **kwargs)
