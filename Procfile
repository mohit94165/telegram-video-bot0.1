web: gunicorn bot:flask_app
worker: python -c "from bot import application; import asyncio; asyncio.run(application.run_polling())"
