BOT_NAME = "crawler"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

ROBOTSTXT_OBEY = True

# Concurrency tuned for RSS fetching (adjust as needed).
CONCURRENT_REQUESTS = 32
DOWNLOAD_TIMEOUT = 15
RETRY_ENABLED = True
RETRY_TIMES = 2
LOG_LEVEL = "INFO"

# Default feed export (can override via CLI -O/-o).
FEEDS = {
    "data/rss_news.jl": {
        "format": "jsonlines",
        "encoding": "utf8",
        "overwrite": True,
    }
}
