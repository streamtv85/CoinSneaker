import sqlite3
import logging
from os import path, makedirs
from coinsneaker.configmanager import config

DB_NAME = 'main.db'
cursor = None
logger = logging.getLogger('bot-service.dbmanager')
db_folder = path.join(path.dirname(path.abspath(__file__)), config.get('dbFolder'))
logger.info("db folder: " + db_folder)
if not path.exists(db_folder):
    logger.debug("creating folder: " + db_folder)
    makedirs(db_folder, exist_ok=True)
db_path = path.join(db_folder, DB_NAME)

def sqlite_decorator(func):
    def new_function(*args, **kwargs):
        global cursor, db_path
        try:
            # Creates or opens a database file with a SQLite3 DB
            logger.debug("connect to the '" + str(db_path) + "' database")
            db = sqlite3.connect(db_path)
            cursor = db.cursor()
            result = func(*args, **kwargs)
            logger.debug("commit changes to the database")
            db.commit()
        except Exception as e:
            # Roll back any change if something goes wrong
            logger.debug("rollback changes from the database")
            db.rollback()
            raise e
        finally:
            logger.debug("Close the db connection")
            db.close()
            cursor = None
        return result

    return new_function


@sqlite_decorator
def drop_db():
    logger.debug("Drop 'chats' table")
    cursor.execute('''DROP TABLE IF EXISTS chats''')


@sqlite_decorator
def init_db():
    logger.debug("Create 'chats' table if not exists")
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id integer NOT NULL UNIQUE)''')


@sqlite_decorator
def add_chat(chat_id):
    logger.debug("add or update id: " + str(chat_id) + " to the 'chats' table")
    cursor.execute('''INSERT OR REPLACE INTO chats(id)
                      VALUES(?)''', (chat_id,))


@sqlite_decorator
def delete_chat(chat_id):
    logger.debug("delete id: " + str(chat_id) + "from 'chats' table")
    cursor.execute('''DELETE FROM chats WHERE id = ? ''', (chat_id,))


@sqlite_decorator
def get_all_chats():
    logger.debug("get all rows from 'chats' table")
    cursor.execute('''SELECT id FROM chats''')
    return [i[0] for i in cursor.fetchall()]


# print('drop db')
# drop_db()
logger.info('SQLIte library version: {0}'.format(sqlite3.sqlite_version))
logger.info('init the db, create a table if not exists')
init_db()

if __name__ == "__main__":
    result = get_all_chats()
    if result:
        logger.info('Existing subscribers in the db:')
        logger.info(result)
# print('add chat with id 1')
# add_chat(1)
# print('add chat with id 2')
# add_chat(2)
# print('print list of all chats')
# result = get_all_chats()
# print(result)
# for row in result:
#     print('id: {0}'.format(row))
# print('delete chat no 2')
# delete_chat(2)
# print('now print list of chats. should be only one')
# result = get_all_chats()
# for row in result:
#     print('id: {0}'.format(row))
