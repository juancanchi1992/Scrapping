from __future__ import annotations

# Manual HTML sources deshabilitados para evitar ruido fuera de los feeds RSS
# y acotar el scraping sólo a las fuentes pedidas.
MANUAL_SOURCES = {}


def manual_sources_for_country(country: str):
    return MANUAL_SOURCES.get(country, [])
