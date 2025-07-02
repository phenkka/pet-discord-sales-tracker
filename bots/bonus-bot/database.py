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

    def get_sales_by_channel_and_date(self, user_id: int, start_date, end_date):
        sales_query = """
            SELECT SUM(price) as total_sales
            FROM sales
            WHERE user_id = %s AND sale_date BETWEEN %s AND %s
        """
        params = (user_id, start_date, end_date)
        sales_data = self.execute_read_one_query(sales_query, params)
        return sales_data[0] if sales_data else 0

    def get_sales_by_user_accounts(self, user_id: int, start_date, end_date):
        query = """
            SELECT account_id, SUM(price) as total_sales
            FROM sales
            WHERE user_id = %s AND sale_date BETWEEN %s AND %s
            GROUP BY account_id
        """
        params = (user_id, start_date, end_date)
        return self.execute_read_many_query(query, params)

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

    def get_weekly_sales_by_channels_for_period(self, channel_ids, start_date, end_date):
        query = """
            SELECT username, SUM(price) as total_sales
            FROM sales
            WHERE channel_id = ANY(%s) AND sale_date BETWEEN %s AND %s
            GROUP BY username
            ORDER BY total_sales DESC
        """
        params = (channel_ids, start_date, end_date)
        return self.execute_read_many_query(query, params)