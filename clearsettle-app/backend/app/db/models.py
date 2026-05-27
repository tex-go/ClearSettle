"""
DEPRECATED — this file is shadowed by the app/db/models/ package.

Python's import system prefers a package (directory with __init__.py) over a
same-named module file.  Any import of `app.db.models` resolves to:
    app/db/models/__init__.py

which re-exports all ORM classes.  This file is retained only to avoid IDE
confusion; it should not be edited or imported directly.

To add a new model:
  1. Create  app/db/models/<model_name>.py
  2. Import it in  app/db/models/__init__.py
  3. Add a migration in  alembic/versions/
"""
