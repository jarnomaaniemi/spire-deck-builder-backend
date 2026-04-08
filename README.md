# Spire Deck Builder

## Yleiskuva
Spire Deck Builder on FastAPI-pohjainen backend-sovellus, joka tarjoaa Slay the Spire -teemaiseen deck builderiin liittyvät API-toiminnot.

Projekti sisältää:
- REST API:n (`app/api.py`)
- GraphQL API:n (`/graphql`, toteutus `app/graphql_api.py`)
- SQLite-pohjaisen persistenssin (`app/db.py`)
- Kortti- ja hahmodatan JSON-tiedostoista (`data/*.json`)

## Asennus ja ajo

1. Luo virtuaaliympäristö:

```powershell
python -m venv venv
& venv\Scripts\Activate.ps1
```

2. Asenna riippuvuudet:

```powershell
pip install -r requirements.txt
```

3. Käynnistä sovellus:

```powershell
uvicorn main:app --reload
```

Tämän jälkeen:
- REST-dokumentaatio: `http://localhost:8000/docs`
- GraphQL-käyttöliittymä: `http://localhost:8000/graphql`

## API-yhteenveto

### REST
Julkiset endpointit:
- `POST /auth/register`
- `GET /auth/me`
- `GET /characters`
- `GET /characters/{char_id}/deck`
- `GET /search/cards`

Suojatut endpointit (header `X-API-Key`):
- `POST /deck/create`
- `GET /decks`
- `GET /deck/{pack_id}`
- `POST /deck/add`
- `DELETE /deck/{pack_id}/card/{card_id}`

### GraphQL
Endpoint: `POST /graphql` (GraphiQL UI samassa osoitteessa)

GraphQL tarjoaa vastaavat toiminnot kuin REST:
- Queryt: `characters`, `character_deck`, `search_cards`, `me`, `decks`, `deck`
- Mutationit: `register`, `create_deck`, `add_card_to_deck`, `remove_card_from_deck`

Huomio: GraphQL-schemassa on snake_case-kenttänimet (`auto_camel_case=False`).

## API-avain ja autentikointi
- API-avain luodaan `POST /auth/register` tai GraphQL `register`-mutaatiolla.
- Suojatut reitit vaativat `X-API-Key`-headerin.
- Avain validoidaan `users`-taulusta (`app/dependencies.py`).

### Validointiperiaatteet
- Header-validointi: suojatut endpointit käyttävät `require_api_key`-riippuvuutta.
- Runkojen validointi: `DeckCreateRequest` ja `DeckAddRequest` (Pydantic) varmistavat perusrakenteen.
- Domain-validointi: hahmo- ja kortti-ID:t tarkistetaan ennen operaatioita.
- Kanonisointi: käyttäjän syötteestä voidaan hyväksyä alias, joka resolvoidaan kanoniseen kortti-ID:hen.

### Tyypilliset virhetilanteet
- `403 Forbidden`: API-avain puuttuu tai on virheellinen.
- `404 Not Found`: tuntematon hahmo, pakka tai kortti.
- `422 Unprocessable Entity`: JSON-runko ei vastaa Pydantic-mallia.

Virhevastausten muoto noudattaa FastAPI:n `HTTPException`-rakennetta, esimerkiksi:

```json
{
  "detail": "Invalid or missing API key"
}
```

## Tietokantamalli (SQLite)
`app/db.py` luo taulut:

- `users`
  - `api_key TEXT PRIMARY KEY`
  - `created_at TEXT`

- `decks`
  - `pack_id TEXT PRIMARY KEY`
  - `api_key TEXT NOT NULL`
  - `character TEXT NOT NULL`
  - `deck_json TEXT NOT NULL`

## Turvallisuusmalli ja riskit

Nykyinen turvallisuusmalli:

- API-avaimet generoidaan UUID-muodossa.
- Suojatut endpointit vaativat avaimen jokaisessa pyynnössä.
- Dekkien luku/muokkaus sidotaan sekä `pack_id`:hen että `api_key`:hin.

Tunnistetut rajoitteet ja riskit:

- API-avain tallennetaan SQLiteen sellaisenaan (ei hashattuna).
- Avaimilla ei ole vanhenemista tai rotaatiota.

Mahdolliset jatkoparannukset:

- API-avaimen hashattu tallennus.
- Avaimen vanheneminen ja uudelleenluonti.

## Teknisten valintojen perustelut (omatoiminen ongelmanratkaisu)

- REST + GraphQL rinnakkain:
  - REST tarjoaa yksinkertaiset endpointit ja OpenAPI-dokumentaation.
  - GraphQL mahdollistaa joustavamman kyselymallin samoihin toimintoihin.
- Alias-resoluutio korteille:
  - Käyttäjän syöte voi olla eri muodossa kuin datan kanoninen ID.
  - `resolve_card_id` vähentää virheitä ja parantaa käytettävyyttä.
- Moduulijako:
  - Eri vastuut (`api`, `db`, `loader`, `deck_logic`) pidetty erillään luettavuuden ja testattavuuden parantamiseksi.

## Testaus

Testit:
- `tests/test_loader.py`
- `tests/test_analysis.py`
- `tests/test_api.py`
- `tests/test_graphql.py`

Yhteinen testi-DB setup on tiedostossa `tests/conftest.py`.

Testauksen painopisteet:

- API-toiminnallisuus: autentikointi, pakan luonti ja muokkaus.
- Laskentalogiikka: damage/block-analytiikan oikeellisuus.
- Datalataus: JSON-aineistojen rakenne ja käytettävyys.
- GraphQL-pariteetti: samat ydintoiminnot kuin REST-rajapinnassa.

Testieristys:

- Testit käyttävät erillistä tietokantaa (`DECKS_DB_PATH=spiredb_test.db`).
- Testikannan tiedosto poistetaan testiajon alussa ja lopussa.

Aja testit:

```powershell
pytest
pytest -q
pytest -vv
pytest -k api
pytest -k graphql
```

## Jatkokehityskohteet

- Tarkempi syötteen validointi (esim. pakan sisällön lisäsäännöt).
- Laajempi virheviestien standardointi kaikkien endpointien välillä.
- Turvallisuusparannukset (avaimen hash, rotaatio, rate limiting).
- Suorituskykyoptimointi suuremmille datamäärille.
- Lisätestit harvinaisille reunaehdoille.

## Projektisuunnitelma

- Aihe: Slay the Spire -henkisen deck builderin backend-palvelu.
- Erityishuomio: Toteutetaan AI-avusteisesti.
- Käytettävä sovelluskehys: FastAPI (REST) + GraphQL-tuki.
- Käytetty tietovarasto:
  - JSON-tiedostot pelidatan lähteenä.
  - SQLite käyttäjien ja dekkien pysyvään tallennukseen.
- Lisäominaisuudet:
  - GraphQL-rajapinta RESTin rinnalla.
  - Dekkien analytiikka (adjusted DPT/BPT).
  - Korttialias-resoluutio käytettävyyden parantamiseen.

## Projektin rakenne

```text
spire-deck-builder/
|
+-- .github/
|   +-- copilot-instructions.md
|   +-- instructions/
|   |   +-- api.instructions.md
|   |   +-- tests.instructions.md
|   +-- prompts/
|       +-- add-endpoint.prompt.md
|
+-- app/
|   +-- api.py
|   +-- db.py
|   +-- deck_logic.py
|   +-- dependencies.py
|   +-- graphql_api.py
|   +-- loader.py
|   +-- init.py
|
+-- data/
|   +-- cards.json
|   +-- characters.json
|   +-- enchantments.json
|   +-- keywords.json
|   +-- modifiers.json
|   +-- orbs.json
|   +-- powers.json
|   +-- relics.json
|
+-- tests/
|   +-- conftest.py
|   +-- test_analysis.py
|   +-- test_api.py
|   +-- test_graphql.py
|   +-- test_loader.py
|
+-- main.py
+-- pytest.ini
+-- requirements.txt
+-- README.md
```
