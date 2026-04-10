from dao.BaseDAO import BaseDAO

class UserDAO(BaseDAO):
    def __init__(self):
        super.__init__()

    def get_user_by_username(self, username):
        sql = "SELECT User_ID, Username, Password, Role FROM USER_ACCOUNT WHERE Username = %s"
        params = (username,)
        result = self.executor.execute_query_one(sql, params)
        return result