# Scraping News API

API en FastAPI que agrega noticias por país, lenguaje y rango de fechas usando fuentes RSS confiables.

## Stack
- Python 3.11+
- FastAPI + Uvicorn
- httpx + feedparser para descarga y parsing

## Configuración rápida
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La documentación interactiva quedará en `http://localhost:8000/docs`.

## Uso
Endpoint principal: `GET /news`

Parámetros:
- `q` (obligatorio): keyword para buscar las noticias.
- `page_size` (obligatorio): total de items a devolver en la página (1..100).
- `country` (opcional): códigos tipo `es-AR`, `es-ES`, `es-CO`, `es-MX`, `es-PE`, `es-CL`, `es-EC`, `es-VE`, `en-US` (alias `EEUU`, `USA`). Si se omite busca en todas las fuentes.
- `language`: forzar idioma (si se omite y no hay país, no se filtra por idioma).
- `period`: `day|week|month|year` para filtrar por rango relativo.
- `date_from` / `date_to`: rangos absolutos (ISO `YYYY-MM-DD`).
- `page`: página (1..n).

Cada noticia devuelve:
- `title`, `image_path` (cuando la fuente la expone), `source`, `link`, `date`, `country`, `language`.

Ejemplo:
```bash
curl "http://localhost:8000/news?q=elecciones&page_size=20&country=es-AR&period=week&page=1"
```

## Crawler con Scrapy (alto volumen)
- Se incluyó un proyecto `Scrapy` para pre-colectar noticias vía RSS en paralelo.
- Ejecuta el spider y guarda en `data/rss_news.jl` (JSONL):
```bash
PYTHONPATH=. scrapy crawl rss_all
```
- Configuración en `scrapy.cfg` y `crawler/settings.py` (concurrencia, timeouts, FEEDS). Ajusta `CONCURRENT_REQUESTS`/`DOWNLOAD_TIMEOUT` según necesidad. Los feeds usados son los mismos de `app/sources.py`.

## Notas sobre scraping
- Se usan fuentes RSS públicas para minimizar bloqueo por scraping.
- Si alguna fuente falla se devuelve en `warnings` pero no rompe la respuesta.
- El filtrado por fecha depende de que el feed exponga `published` o `updated`.

## Extender fuentes
Las fuentes están en `app/sources.py`. Agrega una nueva entrada `NewsSource` con:
- `country`: código `lang-CC`.
- `language`: código ISO 639-1.
- `feeds`: lista de endpoints RSS.
