from datetime import datetime, time
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

    def init_db(self):
        create_sales_table = """
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            channel_id BIGINT NOT NULL,
            price INTEGER NOT NULL,
            sale_date DATE NOT NULL,
            sale_time TIME NOT NULL
        );
        """

        create_clocked_table = """
        CREATE TABLE IF NOT EXISTS clocked_times (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            duration TIME NOT NULL
        );
        """

        self.execute_write_query(create_sales_table)
        self.execute_write_query(create_clocked_table)

    def insert_sale(self, username: str, channel_id: int, price: int, timestamp: datetime):
        query = """
            INSERT INTO sales (username, channel_id, price, sale_date, sale_time)
            VALUES (%s, %s, %s, %s, %s)
        """
        date = timestamp.date()
        time_only = timestamp.time()
        params = (username, channel_id, price, date, time_only)
        self.execute_write_query(query, params)

    def insert_clocked_time(self, username: str, hours: int, minutes: int, seconds: int):
        query = """
            INSERT INTO clocked_times (username, duration)
            VALUES (%s, %s)
        """
        duration = time(hour=hours, minute=minutes, second=seconds)
        params = (username, duration)
        self.execute_write_query(query, params)
