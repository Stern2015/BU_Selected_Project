"""
Vendor Service Quick Reference
Simple examples for all vendor service functions
"""

from services.vendor_service import VendorService

# Initialize vendor service
vendor_service = VendorService()

# ============================================================
# REQUIRED FUNCTIONS (7 core functions)
# ============================================================

def example_get_all_vendors():
    """Example 1: Get all vendors list"""
    vendors = vendor_service.get_all_vendors()
    print("All Vendors:")
    for vendor in vendors:
        print(f"  ID: {vendor[0]}, Name: {vendor[1]}, Location: {vendor[2]}, Rating: {vendor[4]}")


def example_onboard_new_vendor():
    """Example 2: Onboard new vendor"""
    result = vendor_service.onboard_new_vendor(
        user_id='u5',
        business_name='Premium Electronics',
        geographical_presence='Chicago'
    )
    print(f"Onboard Result: {result}")


def example_get_vendor_by_id():
    """Example 3: Get single vendor details"""
    vendor = vendor_service.get_vendor_by_id('u2')
    if vendor:
        print(f"Vendor Details:")
        print(f"  Business Name: {vendor['business_name']}")
        print(f"  Location: {vendor['geographical_presence']}")
        print(f"  Average Rating: {vendor['average_rating']}")
        print(f"  Status: {vendor['status']}")
    else:
        print("Vendor not found")


def example_update_vendor_info():
    """Example 4: Update vendor information"""
    result = vendor_service.update_vendor_info(
        vendor_id='u2',
        business_name='Updated Store Name',
        geographical_presence='Updated Location'
    )
    print(f"Update Result: {result}")


def example_get_vendor_products():
    """Example 5: Get all vendor products"""
    products = vendor_service.get_vendor_products('u2')
    print(f"Vendor Products ({len(products)} total):")
    for product in products:
        print(f"  Product: {product[1]}, Price: ${product[3]}, Stock: {product[4]}")


def example_get_vendor_average_rating():
    """Example 6: Get vendor average rating"""
    avg_rating = vendor_service.get_vendor_average_rating('u2')
    print(f"Vendor Average Rating: {avg_rating}")


def example_get_vendor_orders():
    """Example 7: Get vendor orders (optional)"""
    orders = vendor_service.get_vendor_orders('u2')
    print(f"Vendor Orders ({len(orders)} total):")
    for order in orders:
        print(f"  Order ID: {order[0]}, Product: {order[7]}, Quantity: {order[2]}")


# ============================================================
# BONUS UTILITY FUNCTIONS
# ============================================================

def example_get_vendor_stats():
    """Get comprehensive vendor statistics"""
    stats = vendor_service.get_vendor_stats('u2')
    if stats:
        print("Vendor Statistics:")
        print(f"  Total Products: {stats['total_products']}")
        print(f"  Active Products: {stats['active_products']}")
        print(f"  Average Rating: {stats['average_rating']}")
        print(f"  Status: {stats['status']}")


def example_update_vendor_rating():
    """Update vendor rating"""
    result = vendor_service.update_vendor_rating('u2', 4.8)
    print(f"Rating Update Result: {result}")


def example_deactivate_vendor():
    """Deactivate vendor"""
    result = vendor_service.deactivate_vendor('u2')
    print(f"Deactivation Result: {result}")


def example_activate_vendor():
    """Activate vendor"""
    result = vendor_service.activate_vendor('u2')
    print(f"Activation Result: {result}")


# ============================================================
# COMPLETE WORKFLOW EXAMPLE
# ============================================================

def complete_vendor_workflow():
    """Complete workflow: onboard, update, and retrieve vendor information"""
    
    print("=" * 60)
    print("COMPLETE VENDOR WORKFLOW EXAMPLE")
    print("=" * 60)
    
    # Step 1: Onboard new vendor
    print("\n[Step 1] Onboarding new vendor...")
    onboard_result = vendor_service.onboard_new_vendor(
        user_id='u6',
        business_name='Organic Goods Store',
        geographical_presence='Portland'
    )
    
    if not onboard_result['success']:
        print(f"Error: {onboard_result['message']}")
        return
    
    vendor_id = onboard_result['vendor_id']
    print(f"✓ Vendor created: {vendor_id}")
    
    # Step 2: Retrieve vendor details
    print(f"\n[Step 2] Retrieving vendor details...")
    vendor = vendor_service.get_vendor_by_id(vendor_id)
    if vendor:
        print(f"✓ Store Name: {vendor['business_name']}")
        print(f"✓ Location: {vendor['geographical_presence']}")
        print(f"✓ Status: {vendor['status']}")
    
    # Step 3: Update vendor information
    print(f"\n[Step 3] Updating vendor information...")
    update_result = vendor_service.update_vendor_info(
        vendor_id=vendor_id,
        business_name='Premium Organic Goods',
        geographical_presence='Seattle'
    )
    print(f"✓ Update Status: {update_result['message']}")
    
    # Step 4: Get vendor statistics
    print(f"\n[Step 4] Retrieving vendor statistics...")
    stats = vendor_service.get_vendor_stats(vendor_id)
    if stats:
        print(f"✓ Total Products: {stats['total_products']}")
        print(f"✓ Active Products: {stats['active_products']}")
        print(f"✓ Average Rating: {stats['average_rating']}")
    
    # Step 5: Get vendor products
    print(f"\n[Step 5] Retrieving vendor products...")
    products = vendor_service.get_vendor_products(vendor_id)
    print(f"✓ Total Products: {len(products)}")
    
    # Step 6: Update vendor rating
    print(f"\n[Step 6] Updating vendor rating...")
    rating_result = vendor_service.update_vendor_rating(vendor_id, 4.7)
    print(f"✓ {rating_result['message']}")
    
    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == '__main__':
    # Run complete workflow example
    complete_vendor_workflow()
    
    # Uncomment individual examples to test
    # example_get_all_vendors()
    # example_onboard_new_vendor()
    # example_get_vendor_by_id()
    # example_update_vendor_info()
    # example_get_vendor_products()
    # example_get_vendor_average_rating()
    # example_get_vendor_orders()
    # example_get_vendor_stats()
    # example_update_vendor_rating()
    # example_deactivate_vendor()
    # example_activate_vendor()
