Проект разбит на несколько файлов:
1. bot.py - основная логика бота. "фронтенд"
2. gpt.py - модуль, который полностью отвечает за взаимодействие с GPT
3. db.py - взаимодействие с БД
4. poetry. - зависимости проекта
5. requirements.txt - файл, который делает вид, что хранит зависимости. Его автоматически сгенерировал poetry, так что ему лучше не доверять

Функцию отладки как таковую я не добавил, но все равно при любой ошибке связанной с запросом, бот будет отправлять ее код. В коде могут зачастую встречаться очень упоротые и нелогичные решения, до делалось все наспех, потом еще подгонять это под ТЗ практикума пришлось... В общем имеем что имеем