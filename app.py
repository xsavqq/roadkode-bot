# Точка входа для хостингов, которые запускают app.py по умолчанию.
# Сам бот по-прежнему живёт в main.py.

import asyncio

from main import main


if __name__ == "__main__":
    asyncio.run(main())
