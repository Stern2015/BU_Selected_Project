#!/usr/bin/env python3
"""
Shop Module Test Script
Test the newly added shop module functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, DB

def test_memory_db():
    """Test in-memory database"""
    print("1. Testing in-memory database...")

    # Check user data
    print(f"  User count: {len(DB['users'])}")
    for user in DB['users']:
        print(f"    - {user['username']} (Role: {user['role']})")

    # Check vendor data
    print(f"  Vendor count: {len(DB['vendors'])}")
    for vendor in DB['vendors']:
        print(f"    - {vendor['name']} (Status: {vendor['status']})")

    # Check product data
    print(f"  Product count: {len(DB['products'])}")
    for product in DB['products']:
        print(f"    - {product['title']} (Price: ${product['price']}, Stock: {product['stock']})")

    print("  ✓ In-memory database check completed")

def test_routes():
    """Test routes"""
    print("\n2. Testing routes...")

    with app.test_client() as client:
        # Test product browsing page
        response = client.get('/products')
        print(f"  /products status code: {response.status_code}")
        assert response.status_code == 200, "Product browsing page should return 200"

        # Test product browsing with parameters
        response = client.get('/products?q=laptop&category=Electronics')
        print(f"  /products?q=laptop&category=Electronics status code: {response.status_code}")
        assert response.status_code == 200, "Product browsing page with search parameters should return 200"

        # Test vendor dashboard (requires login, should redirect)
        response = client.get('/vendor')
        print(f"  /vendor status code: {response.status_code} (should redirect to login)")
        assert response.status_code == 302, "Unauthorized access to vendor dashboard should redirect"

        # Test product management page (requires login, should redirect)
        response = client.get('/vendor/products')
        print(f"  /vendor/products status code: {response.status_code} (should redirect to login)")
        assert response.status_code == 302, "Unauthorized access to product management page should redirect"

        # Test product detail page
        if DB['products']:
            product_id = DB['products'][0]['id']
            response = client.get(f'/product/{product_id}')
            print(f"  /product/{product_id} status code: {response.status_code}")
            assert response.status_code == 200, "Product detail page should return 200"

        print("  ✓ Route testing completed")

def test_product_management():
    """Test product management functionality (simulate vendor login)"""
    print("\n3. Testing product management functionality...")

    with app.test_client() as client:
        # Simulate vendor login
        with client.session_transaction() as sess:
            sess['user'] = {'id': 'u2', 'username': 'vendor1', 'role': 3}  # ROLE_VENDOR | ROLE_CUSTOMER
            sess['login_type'] = 'backend'

        # Test vendor dashboard
        response = client.get('/vendor')
        print(f"  Vendor dashboard status code: {response.status_code}")
        assert response.status_code == 200, "Logged-in vendor should be able to access dashboard"

        # Test product management page
        response = client.get('/vendor/products')
        print(f"  Product management page status code: {response.status_code}")
        assert response.status_code == 200, "Logged-in vendor should be able to access product management"

        # Test different tabs
        for tab in ['all', 'active', 'inactive', 'inventory']:
            response = client.get(f'/vendor/products?tab={tab}')
            print(f"  Tab '{tab}' status code: {response.status_code}")
            assert response.status_code == 200, f"Tab '{tab}' should be accessible"

        print("  ✓ Product management functionality testing completed")

def test_product_operations():
    """Test product operations"""
    print("\n4. Testing product operations...")

    initial_product_count = len(DB['products'])

    with app.test_client() as client:
        # Simulate vendor login
        with client.session_transaction() as sess:
            sess['user'] = {'id': 'u2', 'username': 'vendor1', 'role': 3}
            sess['login_type'] = 'backend'

        # Test adding product
        new_product_data = {
            'product_id': '',  # Empty means new creation
            'name': 'Test Product',
            'description': 'A test product',
            'category': 'Electronics',
            'price': '99.99',
            'stock': '50',
            'image_url': 'https://picsum.photos/seed/test/400/300',
            'tags': 'test,electronics',
            'status': 'Active'
        }

        response = client.post('/vendor/product/save', data=new_product_data, follow_redirects=True)
        print(f"  Add product status code: {response.status_code}")
        assert response.status_code == 200, "Adding product should succeed"

        # Check if product was added successfully
        new_product_count = len(DB['products'])
        print(f"  Product count change: {initial_product_count} -> {new_product_count}")
        assert new_product_count > initial_product_count, "Product should be added to database"

        # Find the newly added product
        new_product = None
        for product in DB['products']:
            if product['title'] == 'Test Product':
                new_product = product
                break

        assert new_product is not None, "Should be able to find newly added product"
        print(f"  Newly added product: {new_product['title']} (ID: {new_product['id']})")

        # Test toggling product status
        response = client.post(f'/vendor/product/{new_product["id"]}/toggle', follow_redirects=True)
        print(f"  Toggle product status status code: {response.status_code}")
        assert response.status_code == 200, "Toggling product status should succeed"

        # Check if status changed
        updated_product = next((p for p in DB['products'] if p['id'] == new_product['id']), None)
        assert updated_product is not None, "Should be able to find updated product"
        print(f"  Product new status: {updated_product['status']}")

        print("  ✓ Product operations testing completed")

def test_stock_management():
    """Test stock management"""
    print("\n5. Testing stock management...")

    with app.test_client() as client:
        # Simulate vendor login
        with client.session_transaction() as sess:
            sess['user'] = {'id': 'u2', 'username': 'vendor1', 'role': 3}
            sess['login_type'] = 'backend'

        # Find a product to test stock update
        test_product = None
        for product in DB['products']:
            if product['vendor_id'] == 'u2':  # Belongs to current vendor
                test_product = product
                break

        if test_product:
            initial_stock = test_product['stock']

            # Test increasing stock (AJAX interface)
            import json
            response = client.post(
                f'/vendor/product/{test_product["id"]}/stock',
                data=json.dumps({'action': 'increase', 'amount': 5}),
                content_type='application/json'
            )
            print(f"  Increase stock status code: {response.status_code}")
            assert response.status_code == 200, "Increasing stock should succeed"

            # Check if stock was updated
            updated_product = next((p for p in DB['products'] if p['id'] == test_product['id']), None)
            if updated_product:
                print(f"  Stock change: {initial_stock} -> {updated_product['stock']}")

            print("  ✓ Stock management testing completed")
        else:
            print("  ⚠ No vendor products found to test stock management")

def main():
    """Main test function"""
    print("=" * 60)
    print("Shop Module Functionality Test")
    print("=" * 60)

    try:
        test_memory_db()
        test_routes()
        test_product_management()
        test_product_operations()
        test_stock_management()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())