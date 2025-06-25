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
            channel_id BIGINT NOT NULL,
            duration INTERVAL NOT NULL,
            work_date DATE NOT NULL,
            work_time TIME NOT NULL
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

    def insert_clocked_time(self, username: str, hours: int, minutes: int, seconds: int, channel_id: int, timestamp: datetime):
        query = """
            INSERT INTO clocked_times (username, channel_id, duration, work_date, work_time)
            VALUES (%s, %s, %s, %s, %s)
        """
        date = timestamp.date()
        time_only = timestamp.time()
        duration = time(hour=hours, minute=minutes, second=seconds)
        params = (username, channel_id, duration, date, time_only)
        self.execute_write_query(query, params)

    def get_sales_by_channel_and_date(self, channel_id: int, start_date: datetime, end_date: datetime):
        query = """
            WITH user_sales_by_day AS (
                SELECT username, sale_date, SUM(price) AS total
                FROM sales
                WHERE channel_id = %s AND sale_date BETWEEN %s AND %s
                GROUP BY username, sale_date
            )
            SELECT DISTINCT ON (username) username, sale_date AS best_day
            FROM user_sales_by_day
            ORDER BY username, total DESC
        """
        params = (channel_id, start_date.date(), end_date.date())
        return self.execute_read_many_query(query, params)

    def get_clocked_time_by_channel_and_date(self, channel_id: int, start_date: datetime, end_date: datetime):
        query = """
            SELECT username, SUM(EXTRACT(EPOCH FROM duration)) as total_seconds
            FROM clocked_times
            WHERE channel_id = %s
            GROUP BY username
        """
        # Здесь clocked_times не имеет даты, так что фильтрация по времени не работает —
        # нужно будет учитывать это, если потребуется детализация.
        params = (channel_id,)
        return self.execute_read_many_query(query, params)
