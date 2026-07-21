"""Chorale generation: Roman numerals -> four-part SATB -> MusicXML.

The inverse of ``app.analyzer``. Implements the rule spec in
``docs/PARTWRITING-RULES.md`` -- that document is the source of truth; this
package is deliberately free of any FastAPI/HTTP dependency so it can be
tested and reused standalone (see ``docs/IMPLEMENTATION-PLAN.md``).
"""
