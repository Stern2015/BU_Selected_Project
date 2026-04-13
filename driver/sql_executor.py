import pymysql
from driver.db_connection import Connection_Manager

class SQL_Executor:
    def __init__(self):
        self.conn_manager = Connection_Manager()

    '''
    execute SELECT statement and return ALL record
    '''
    def execute_query(self, sql, params=None):
        conn = self.conn_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            raise e

    '''
    execute SELECT statement and return ONE record
    '''
    def execute_query_one(self, sql, params=None):
        conn = self.conn_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except Exception as e:
            raise e

    '''
    execute_update to execute Insert/Delete/Update operations
    '''
    def execute_update(self, sql, params=None):
        conn = self.conn_manager.get_connection()
        try:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
            conn.commit()
            return affected_rows
        except Exception as e:
            conn.rollback()
            raise e