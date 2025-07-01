from datetime import datetime
from psycopg2 import pool
from collections import defaultdict


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

    def get_sales_by_channel_and_date(self, channel_id: int, start_date, end_date):
        sales_query = """
            SELECT username, SUM(price) as total_sales
            FROM sales
            WHERE channel_id = %s AND sale_date BETWEEN %s AND %s
            GROUP BY username
            ORDER BY total_sales DESC
        """
        max_day_query = """
            SELECT sale_date, SUM(price) AS total_sales
            FROM sales
            WHERE channel_id = %s AND sale_date BETWEEN %s AND %s
            GROUP BY sale_date
            ORDER BY total_sales DESC
            LIMIT 1
        """
        params = (channel_id, start_date, end_date)

        sales_data = self.execute_read_many_query(sales_query, params)
        max_sales_day = self.execute_read_one_query(max_day_query, params)

        return {
            "sales_by_user": sales_data,
            "top_sales_day": max_sales_day
        }

    def get_group_channels(self):
        query = """
            SELECT group_number, channel_id
            FROM channel_owners
        """
        result = self.execute_read_many_query(query)
        groups = defaultdict(list)
        if result:
            for group_number, channel_id in result:
                groups[str(group_number)].append(channel_id)
        return groups

    def get_update_channels(self):
        query = """
            SELECT DISTINCT group_number, update_chat_id
            FROM channel_owners
        """
        result = self.execute_read_many_query(query)
        updates = {}
        if result:
            for group_number, update_chat_id in result:
                updates[str(group_number)] = update_chat_id
        return updates