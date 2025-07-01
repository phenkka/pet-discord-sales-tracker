from datetime import datetime
from psycopg2 import pool


class Database:
    def __init__(self, minconn, maxconn, dbname, user, password, host, port):
        self.connection_pool = pool.SimpleConnectionPool(
            minconn,
            maxconn,
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

    def get_connection(self):
        return self.connection_pool.getconn()

    def release_connection(self, conn):
        self.connection_pool.putconn(conn)

    def close_all_connections(self):
        self.connection_pool.closeall()

    def execute_read_one_query(self, query, params=None):
        conn = self.get_connection()
        result = None
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    result = cursor.fetchone()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.release_connection(conn)
        return result

    def execute_read_many_query(self, query, params=None):
        conn = self.get_connection()
        result = None
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    result = cursor.fetchall()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.release_connection(conn)
        return result

    def execute_write_query(self, query, params=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.release_connection(conn)

    def add_channel_owner(self, channel_id, username, update_chat_id, group_number):
        query = """
            INSERT INTO channel_owners (channel_id, username, update_chat_id, group_number)
            VALUES (%s, %s, %s, %s)
        """
        params = (channel_id, username, update_chat_id, group_number)
        self.execute_write_query(query, params)

    def delete_channel_owner(self, channel_id):
        query = """
            DELETE FROM channel_owners WHERE channel_id = %s
        """
        params = (channel_id,)
        self.execute_write_query(query, params)