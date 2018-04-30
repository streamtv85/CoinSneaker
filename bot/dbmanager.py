import sqlite3

DB_NAME = 'main.db'
cursor = None


def sqlite_decorator(func):
    def new_function(*args, **kwargs):
        global cursor
        try:
            # Creates or opens a database file with a SQLite3 DB
            db = sqlite3.connect(DB_NAME)
            cursor = db.cursor()
            result = func(*args, **kwargs)
            db.commit()
        except Exception as e:
            # Roll back any change if something goes wrong
            db.rollback()
            raise e
        finally:
            # Close the db connection
            db.close()
            cursor = None
        return result

    return new_function


@sqlite_decorator
def drop_db():
    # Create table
    cursor.execute('''DROP TABLE IF EXISTS chats''')


@sqlite_decorator
def init_db():
    # Create table
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id integer NOT NULL UNIQUE, name text)''')


@sqlite_decorator
def add_chat(chat_id, chat_name):
    cursor.execute('''INSERT OR REPLACE INTO chats(id, name)
                      VALUES(?,?)''', (chat_id, chat_name))


@sqlite_decorator
def delete_chat(chat_id):
    cursor.execute('''DELETE FROM chats WHERE id = ? ''', (chat_id,))


@sqlite_decorator
def get_all_chats():
    cursor.execute('''SELECT id, name FROM chats''')
    return cursor.fetchall()


# print('drop db')
# drop_db()
print('SQLIte library version: {0}'.format(sqlite3.sqlite_version))
print('init the db, create a table if not exists')
init_db()
result = get_all_chats()
if result:
    print('print list of all chats in the db:')
    for row in result:
        print('id: {0}, name: {1}'.format(row[0], row[1]))
# print('add chat with id 1')
# add_chat(1, 'Коровник:)))')
# print('add chat with id 2')
# add_chat(2, 'name 2')
# print('print list of all chats')
# result = get_all_chats()
# for row in result:
#     print('id: {0}, name: {1}'.format(row[0], row[1]))
# print('delete chat no 2')
# delete_chat(2)
# print('now print list of chats. should be only one')
# result = get_all_chats()
# for row in result:
#     print('id: {0}, name: {1}'.format(row[0], row[1]))
