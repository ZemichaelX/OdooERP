# Pinned by DIGEST (R7): the 19.0 tag is rebuilt upstream continuously, and an
# unannounced rebuild silently changed core behaviour under us once already.
# Upgrading the image is a deliberate, tested change — bump this digest in its
# own PR and let the CI integration suite prove it.
FROM odoo:19.0@sha256:e415f9924395e7521245813135112f264b9222bcde3b1d3c2ee9ff073081540a
# Custom addons are mounted via docker-compose (../addons -> /mnt/extra-addons).
USER root
# Ethiopic-script font so Amharic text renders in wkhtmltopdf reports
# (bilingual partner/employee names are a product feature; without a font
# they print as tofu boxes on every PDF).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-sil-abyssinica \
    && rm -rf /var/lib/apt/lists/*
USER odoo
