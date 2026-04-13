-- Shop module database table structure
-- This file contains table structures for products, tags, vendors, etc.

-- If tables exist, drop them first (for development environment only)
DROP TABLE IF EXISTS Rating;
DROP TABLE IF EXISTS Tagging;
DROP TABLE IF EXISTS Tag;
DROP TABLE IF EXISTS Product;
DROP TABLE IF EXISTS Category;
DROP TABLE IF EXISTS Vendor;
DROP TABLE IF EXISTS Customer;
DROP TABLE IF EXISTS UserAccount;

-- UserAccount table
CREATE TABLE UserAccount (
    User_ID INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(50),
    PasswordHash VARCHAR(255),
    Phone_Number VARCHAR(32),
    Role_Bits INT
);

-- Vendor table
CREATE TABLE Vendor (
    Vendor_ID VARCHAR(50) PRIMARY KEY,
    Store_Name VARCHAR(255) NOT NULL,
    Location VARCHAR(255),
    Status ENUM('Active', 'Inactive') DEFAULT 'Active',
    Rating DECIMAL(3, 2) DEFAULT 0.00,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Updated_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Customer table
CREATE TABLE Customer (
    User_ID VARCHAR(50) PRIMARY KEY,
    Phone_number VARCHAR(50),
    Nick_name VARCHAR(255),
    Address VARCHAR(255),
    Order_History TEXT
);

-- Rating table (customer rates vendor)
CREATE TABLE Rating (
    Customer_ID VARCHAR(50),
    Vendor_ID VARCHAR(50),
    Score INT,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Customer_ID, Vendor_ID)
);

-- Category table (product categories)
CREATE TABLE Category (
    Category_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL UNIQUE,
    Description TEXT,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product table
CREATE TABLE Product (
    Product_ID VARCHAR(50) PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Description TEXT,
    Price DECIMAL(10, 2) NOT NULL,
    Stock INT NOT NULL DEFAULT 0,
    Category VARCHAR(100),
    Image_URL VARCHAR(500),
    Vendor_ID VARCHAR(50) NOT NULL,
    Status ENUM('Active', 'Inactive', 'OutOfStock') DEFAULT 'Active',
    Rating DECIMAL(3, 2) DEFAULT 0.00,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Updated_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (Vendor_ID) REFERENCES Vendor(Vendor_ID),
    INDEX idx_vendor_status (Vendor_ID, Status),
    INDEX idx_category (Category),
    INDEX idx_status (Status)
);

-- Tag table
CREATE TABLE Tag (
    Tag_ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL UNIQUE,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (Name)
);

-- Tagging table (product-tag association, maximum 3 tags per product)
CREATE TABLE Tagging (
    Product_ID VARCHAR(50),
    Tag_ID INT,
    Position TINYINT CHECK (Position BETWEEN 1 AND 3),
    PRIMARY KEY (Product_ID, Tag_ID),
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID) ON DELETE CASCADE,
    FOREIGN KEY (Tag_ID) REFERENCES Tag(Tag_ID) ON DELETE CASCADE,
    INDEX idx_product (Product_ID),
    INDEX idx_tag (Tag_ID),
    UNIQUE KEY unique_product_position (Product_ID, Position)
);

-- Insert sample categories
INSERT INTO Category (Name, Description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Furniture', 'Home and office furniture'),
('Clothing', 'Apparel and fashion items'),
('Books', 'Books and publications'),
('General', 'General products');

-- Create view: product details (including tags)
CREATE VIEW Product_Detail AS
SELECT
    p.*,
    v.Store_Name,
    v.Location AS Vendor_Location,
    v.Status AS Vendor_Status,
    GROUP_CONCAT(t.Name ORDER BY tg.Position SEPARATOR ', ') AS Tags,
    COUNT(t.Tag_ID) AS Tag_Count
FROM Product p
LEFT JOIN Vendor v ON p.Vendor_ID = v.Vendor_ID
LEFT JOIN Tagging tg ON p.Product_ID = tg.Product_ID
LEFT JOIN Tag t ON tg.Tag_ID = t.Tag_ID
GROUP BY p.Product_ID;

-- Create stored procedure: add product with tags
DELIMITER //
CREATE PROCEDURE AddProductWithTags(
    IN p_product_id VARCHAR(50),
    IN p_name VARCHAR(255),
    IN p_description TEXT,
    IN p_price DECIMAL(10, 2),
    IN p_stock INT,
    IN p_category VARCHAR(100),
    IN p_image_url VARCHAR(500),
    IN p_vendor_id VARCHAR(50),
    IN p_tags TEXT  -- Comma-separated tag names
)
BEGIN
    DECLARE tag_name VARCHAR(100);
    DECLARE tag_id INT;
    DECLARE position_counter INT DEFAULT 1;
    DECLARE tag_list TEXT;
    DECLARE start_pos INT DEFAULT 1;
    DECLARE comma_pos INT;

    -- Insert product
    INSERT INTO Product (Product_ID, Name, Description, Price, Stock, Category, Image_URL, Vendor_ID)
    VALUES (p_product_id, p_name, p_description, p_price, p_stock, p_category, p_image_url, p_vendor_id);

    -- Process tags
    IF p_tags IS NOT NULL AND p_tags != '' THEN
        SET tag_list = p_tags;

        WHILE position_counter <= 3 AND LENGTH(tag_list) > 0 DO
            SET comma_pos = LOCATE(',', tag_list);

            IF comma_pos > 0 THEN
                SET tag_name = TRIM(SUBSTRING(tag_list, 1, comma_pos - 1));
                SET tag_list = SUBSTRING(tag_list, comma_pos + 1);
            ELSE
                SET tag_name = TRIM(tag_list);
                SET tag_list = '';
            END IF;

            IF tag_name != '' THEN
                -- Ensure tag exists
                INSERT IGNORE INTO Tag (Name) VALUES (tag_name);

                -- Get tag ID
                SELECT Tag_ID INTO tag_id FROM Tag WHERE Name = tag_name;

                -- Associate tag to product
                INSERT INTO Tagging (Product_ID, Tag_ID, Position)
                VALUES (p_product_id, tag_id, position_counter)
                ON DUPLICATE KEY UPDATE Position = position_counter;

                SET position_counter = position_counter + 1;
            END IF;
        END WHILE;
    END IF;
END//
DELIMITER ;

-- Create function: check if product belongs to vendor
DELIMITER //
CREATE FUNCTION CheckProductOwnership(
    p_product_id VARCHAR(50),
    p_vendor_id VARCHAR(50)
) RETURNS BOOLEAN
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE owner_id VARCHAR(50);

    SELECT Vendor_ID INTO owner_id
    FROM Product
    WHERE Product_ID = p_product_id;

    RETURN owner_id = p_vendor_id;
END//
DELIMITER ;

-- Create trigger: auto-update product status to OutOfStock when stock is 0
DELIMITER //
CREATE TRIGGER UpdateProductStatusOnStockChange
AFTER UPDATE ON Product
FOR EACH ROW
BEGIN
    IF NEW.Stock = 0 AND NEW.Status != 'Inactive' THEN
        UPDATE Product SET Status = 'OutOfStock' WHERE Product_ID = NEW.Product_ID;
    ELSEIF NEW.Stock > 0 AND OLD.Stock = 0 AND NEW.Status = 'OutOfStock' THEN
        UPDATE Product SET Status = 'Active' WHERE Product_ID = NEW.Product_ID;
    END IF;
END//
DELIMITER ;

-- Create indexes to optimize query performance
CREATE INDEX idx_product_search ON Product(Name, Category, Status);
CREATE INDEX idx_vendor_product ON Product(Vendor_ID, Status, Created_At);


USE bu_selected;

CREATE TABLE IF NOT EXISTS `Order` (
    Order_ID      VARCHAR(36)    PRIMARY KEY,
    Customer_ID   VARCHAR(50)    NOT NULL,
    Order_Date    DATETIME       NOT NULL,
    Status        VARCHAR(20)    DEFAULT 'Pending',
    Total_Payment DECIMAL(10,2)  NOT NULL,
    FOREIGN KEY (Customer_ID) REFERENCES Customer(User_ID)
);

CREATE TABLE IF NOT EXISTS `Transaction` (
    Transaction_ID VARCHAR(36)   PRIMARY KEY,
    Order_ID       VARCHAR(36)   NOT NULL,
    Vendor_ID      VARCHAR(50)   NOT NULL,
    Payment_Amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (Order_ID)  REFERENCES `Order`(Order_ID),
    FOREIGN KEY (Vendor_ID) REFERENCES Vendor(Vendor_ID)
);

CREATE TABLE IF NOT EXISTS Order_Items (
    Transaction_ID VARCHAR(36)   NOT NULL,
    Product_ID     VARCHAR(50)   NOT NULL,
    Quantity       INT           NOT NULL,
    Price          DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (Transaction_ID, Product_ID),
    FOREIGN KEY (Transaction_ID) REFERENCES `Transaction`(Transaction_ID),
    FOREIGN KEY (Product_ID)     REFERENCES Product(Product_ID)
);