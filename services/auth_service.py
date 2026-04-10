"""
Auth Service
Handles business logic related to authentication
"""

from driver.sql_executor import SQL_Executor
from dao.UserDAO import UserDAO
import hashlib

# Role Bitmasks
ROLE_CUSTOMER = 1
ROLE_VENDOR = 2
ROLE_ADMIN = 4

class User:
    def __init__(self, id, username, password, phone_number, role):
        self.id = id
        self.username = username
        self.password = password
        self.phone_number = phone_number
        self.role = role
    
    def get_user_name(self):
        return self.username
    
    def get_phone_number(self):
        return self.phone_number
    
    def get_role(self):
        return self.role
    
    def is_admin(self):
        return self.role & ROLE_CUSTOMER
    
    def is_vendor(self):
        return self.role & ROLE_VENDOR


class Auth_Service:
    def __init__(self):
        self.sql_executor = SQL_Executor()

    def verify_user_account(self, username, password):
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        userdao = UserDAO()
        result = userdao.get_user_by_username(username)
        if result:
            if result[2] == password_hash:
                return True
        return False
    
    def get_user_info(self, username):
        userdao = UserDAO()
        result = userdao.get_user_by_username(username)
        if result:
            user = User(result[0], result[1], result[2], result[3], result[4])
            return user
        
        return None
    
    @staticmethod
    def check_vendor_role(user):
        """
        Check if user has vendor role
        
        Args:
            user (dict): User object/dictionary with 'role' key
        
        Returns:
            bool: True if user has vendor role, False otherwise
        """
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_VENDOR)
    
    @staticmethod
    def check_admin_role(user):
        """
        Check if user has admin role
        
        Args:
            user (dict): User object/dictionary with 'role' key
        
        Returns:
            bool: True if user has admin role, False otherwise
        """
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_ADMIN)
    
    @staticmethod
    def check_customer_role(user):
        """
        Check if user has customer role
        
        Args:
            user (dict): User object/dictionary with 'role' key
        
        Returns:
            bool: True if user has customer role, False otherwise
        """
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & ROLE_CUSTOMER)
    
    @staticmethod
    def has_role(user, role_flag):
        """
        Generic role checker
        
        Args:
            user (dict): User object/dictionary with 'role' key
            role_flag (int): Role bitmask to check
        
        Returns:
            bool: True if user has the specified role, False otherwise
        """
        if not user:
            return False
        
        role = user.get('role', 0)
        return bool(role & role_flag)
        
