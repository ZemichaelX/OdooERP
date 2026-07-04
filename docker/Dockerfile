FROM odoo:19.0
# Custom addons are mounted via docker-compose (../addons -> /mnt/extra-addons).
USER root
# Ethiopic-script font so Amharic text renders in wkhtmltopdf reports
# (bilingual partner/employee names are a product feature; without a font
# they print as tofu boxes on every PDF).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-sil-abyssinica \
    && rm -rf /var/lib/apt/lists/*
USER odoo
