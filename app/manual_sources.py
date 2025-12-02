from __future__ import annotations

# Static HTML sources without RSS to widen coverage per country.
# Only include high-signal pages that allow scraping.
MANUAL_SOURCES = {
    "es-ES": [
        "https://eurydice.eacea.ec.europa.eu/es/eurypedia/spain/educacion-superior",
        "https://www.unesco.org/es/higher-education",
        "https://administracion.gob.es/pag_Home/Tu-espacio-europeo/derechos-obligaciones/ciudadanos/educacion/sistema-educativo/superior.html",
        "https://www.aecid.es/educacion-superior",
        "https://www.educacionfpydeportes.gob.es/mc/redie-eurydice/sistemas-educativos/educacion-superior.html",
        # Additional high-signal pages for ES
        "https://www.losandes.com.ar/sociedad/repensar-la-universidad-los-desafios-que-hoy-redefinen-la-educacion-superior-n5970958",
        "https://www.uned.es/universidad/inicio/en/",
        "https://www.mondragon.edu/",
        "https://web.ub.edu/es/inicio",
        "https://www.urjc.es/",
        "https://intef.es/",
        "https://www.unia.es/",
        "https://www.ufv.es/",
        "https://www.ubu.es/inicio",
        "https://www.um.es/",
        "https://ice.ua.es/es/instituto-de-ciencias-de-la-educacion.html",
        "https://educacionprivada.org/",
        "https://www.espaciosdeeducacionsuperior.es/24/11/2025/revision-ultimos-informes-internacionales-universidad-en-linea/",
        "http://www.unizar.es/",
        "https://www.uma.es/",
        "https://www.ciencia.gob.es/en/",
        "https://www.crue.org/",
        "https://www.us.es/",
    ],
}


def manual_sources_for_country(country: str):
    return MANUAL_SOURCES.get(country, [])
