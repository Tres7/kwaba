FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

WORKDIR /app

RUN useradd --create-home --uid 10001 --user-group app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN DJANGO_SECRET_KEY=collectstatic-build-only POSTGRES_PASSWORD=collectstatic-build-only python manage.py collectstatic --noinput \
    && mkdir -p mediafiles prive && chown app:app mediafiles prive

USER 10001:10001

EXPOSE 8000

# API by default. The consumer, the relay and the migrations use the same image with another command.
# Render provides PORT; WEB_CONCURRENCY sets the number of Gunicorn workers.
# FORWARDED_ALLOW_IPS: addresses of the proxies whose X-Forwarded-* headers Gunicorn accepts (by default none
# but the machine itself). Behind Render's proxy, whose address varies, set "*" in the service's environment,
# with DJANGO_NUM_PROXIES=1.
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --access-logfile - --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS}\""]
