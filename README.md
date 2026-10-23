# Войти в IT

## Локальный запуск

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
plocal
```

Команда `plocal` запускает Flask на `http://127.0.0.1:5001` (порт 5000 занят macOS AirTunes). Остановить сервер: `Ctrl+C`. Другой порт можно выбрать так: `PORT=5050 plocal`.

## Подготовка Ubuntu/Debian-сервера

Проверьте, что DNS-запись домена `vhudoverdiev.ru` указывает на сервер. После отправки кода в GitHub клонируйте репозиторий на сервер и выполните:

```sh
bash deploy/setup_server.sh
```

Скрипт устанавливает Nginx, MariaDB и Python, создаёт отдельную базу `vhiti`, системного пользователя, systemd unit и сайт Nginx. Перед настройкой он сохраняет конфигурацию Nginx и список сервисов в `/root/vhiti-setup-backup-*`. Если Nginx уже настроен на этот домен, скрипт остановится и ничего не перезапишет. После HTTP-проверки создайте администратора командой, которую скрипт выведет, и подключите HTTPS:

```sh
certbot --nginx -d vhudoverdiev.ru
```

После запуска нового сайта и проверки домена удалите прежний проект командой `bash deploy/cleanup_legacy.sh`. Скрипт сначала проверяет новый `vhiti` и его HTTP-ответ; при ошибке старый сайт не трогает. Затем удаляет старый Gunicorn, Nginx-сайт `peredacha`, базу `peredacha`, каталог `/opt/peredacha` и старый сертификат `akvilon-peredacha.ru`. Снимок конфигурации Nginx/systemd сохраняется в root-only каталоге `/root/legacy-nginx-config-*`. Новая база отдельная: `vhiti`.

## Автоматический деплой из GitHub

Workflow `.github/workflows/deploy.yml` запускает `/opt/vhiti/deploy/release.sh` после каждого push в ветку `main`. В GitHub → Settings → Secrets and variables → Actions добавьте секреты:

- `SERVER_HOST` — IP сервера;
- `SERVER_USER` — SSH-пользователь с доступом к `/opt/vhiti`;
- `SERVER_SSH_KEY` — приватный SSH-ключ деплоя;
- `SERVER_KNOWN_HOSTS` — заранее проверенная строка host key сервера.

Не добавляйте приватный ключ, пароль, `.env` или данные БД в Git. После первичной настройки проверьте на сервере SSH-доступ к публичному репозиторию GitHub и права на перезапуск `vhiti`.
