# Overview
This is a REST API for logging classical music concert attendance. 
Designed to capture the full complexity of classical music concerts, from core details like venue, orchestra, and conductor, to nuances like guest conductors and featured soloists.

It is intended to serve as a backend for future web and mobile clients.

# Features

## Classical Music Modeling
Concerts are structured as Performances containing an ordered set list of Works.

Each set list entry supports its own conductor and featured performers, separate from the top-level performance, letting you track a guest conductor who leads only specific pieces or a soloist who only plays one piece.

Performers are categorized by type (Orchestra, Ensemble, Conductor, Solo, Chorus).

Venues store a formatted address and website, and link to an [OpenStreetMap](https://www.openstreetmap.org/) entity.

<img src="screenshots/data_model.png" width="700" alt="Data model diagram">

# Technical Details
This API was built with [Python](https://www.python.org/) and [FastAPI](https://fastapi.tiangolo.com/), served by [Uvicorn](https://www.uvicorn.org/).

## Libraries
[PostgreSQL](https://www.postgresql.org/) for the database.
<br>
[SQLAlchemy](https://www.sqlalchemy.org/) for database access via its ORM.
<br>
[psycopg2](https://www.psycopg.org/) to connect SQLAlchemy to PostgreSQL.
<br>
[Alembic](https://alembic.sqlalchemy.org/) for database migrations.
<br>
[Pydantic](https://docs.pydantic.dev/) for validating requests sent to the API and serializing responses.
<br>
[pytest](https://pytest.org/) for automated testing, with [HTTPX](https://www.python-httpx.org/) driving FastAPI's test client against an in-memory [SQLite](https://www.sqlite.org/) database.
<br>
[Docker](https://www.docker.com/) with Compose for self-hosting.

## External APIs
[MusicBrainz](https://musicbrainz.org/) for metadata enrichment for performers and conductors.
<br>
[OpenOpus](https://openopus.org/) for metadata enrichment for composers and works.
<br>
[OpenStreetMap](https://www.openstreetmap.org/) for choosing and linking to venues.
