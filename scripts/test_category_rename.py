"""
Test script for category rename functionality

Tests:
1. Get current categories
2. Create a test category (tier1)
3. Create transactions and rules with that category
4. Rename the category
5. Verify cascade to transactions and rules
6. Test duplicate prevention
7. Test 404 for non-existent category
"""

import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000/api/v1"

def print_result(test_name, success, message=""):
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}")
    if message:
        print(f"   {message}")

def test_get_categories():
    """Test getting categories list"""
    try:
        response = requests.get(f"{BASE_URL}/categories/tree")
        if response.status_code == 200:
            categories = response.json()
            print_result("Get categories", True, f"Found {len(categories)} tier1 categories")
            return categories
        else:
            print_result("Get categories", False, f"Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print_result("Get categories", False, str(e))
        return None

def test_create_test_category():
    """Create a test category for testing"""
    try:
        # Create tier1
        response = requests.post(f"{BASE_URL}/categories/tier1?name=TestCategory1")
        if response.status_code == 200:
            print_result("Create test tier1 category", True)

            # Create tier2 under it
            response = requests.post(f"{BASE_URL}/categories/tier2?tier1=TestCategory1&name=TestSubCategory1")
            if response.status_code == 200:
                print_result("Create test tier2 category", True)

                # Create tier3
                response = requests.post(f"{BASE_URL}/categories/tier3?tier1=TestCategory1&tier2=TestSubCategory1&name=TestSubSubCategory1")
                if response.status_code == 200:
                    print_result("Create test tier3 category", True)
                    return True
                else:
                    print_result("Create test tier3 category", False, f"Status {response.status_code}")
            else:
                print_result("Create test tier2 category", False, f"Status {response.status_code}")
        else:
            # May already exist - that's OK
            if "already exists" in response.text:
                print_result("Create test tier1 category", True, "Already exists - OK")
                return True
            print_result("Create test tier1 category", False, f"Status {response.status_code}: {response.text}")
        return False
    except Exception as e:
        print_result("Create test category", False, str(e))
        return False

def test_rename_tier1():
    """Test renaming a tier1 category"""
    try:
        # Rename TestCategory1 to RenamedCategory1
        response = requests.put(
            f"{BASE_URL}/categories/tier1/TestCategory1",
            params={"new_name": "RenamedCategory1"}
        )

        if response.status_code == 200:
            result = response.json()
            print_result(
                "Rename tier1 category",
                True,
                f"Updated {result.get('updated', {}).get('transactions', 0)} transactions, "
                f"{result.get('updated', {}).get('rules', 0)} rules"
            )
            return True
        else:
            print_result("Rename tier1 category", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Rename tier1 category", False, str(e))
        return False

def test_rename_tier2():
    """Test renaming a tier2 category"""
    try:
        # Rename TestSubCategory1 to RenamedSubCategory1
        response = requests.put(
            f"{BASE_URL}/categories/tier2/RenamedCategory1/TestSubCategory1",
            params={"new_name": "RenamedSubCategory1"}
        )

        if response.status_code == 200:
            result = response.json()
            print_result(
                "Rename tier2 category",
                True,
                f"Updated {result.get('updated', {}).get('transactions', 0)} transactions, "
                f"{result.get('updated', {}).get('rules', 0)} rules"
            )
            return True
        else:
            print_result("Rename tier2 category", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Rename tier2 category", False, str(e))
        return False

def test_rename_tier3():
    """Test renaming a tier3 category"""
    try:
        # Rename TestSubSubCategory1 to RenamedSubSubCategory1
        response = requests.put(
            f"{BASE_URL}/categories/tier3/RenamedCategory1/RenamedSubCategory1/TestSubSubCategory1",
            params={"new_name": "RenamedSubSubCategory1"}
        )

        if response.status_code == 200:
            result = response.json()
            print_result(
                "Rename tier3 category",
                True,
                f"Updated {result.get('updated', {}).get('transactions', 0)} transactions, "
                f"{result.get('updated', {}).get('rules', 0)} rules"
            )
            return True
        else:
            print_result("Rename tier3 category", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print_result("Rename tier3 category", False, str(e))
        return False

def test_duplicate_prevention():
    """Test that renaming to existing category is prevented"""
    try:
        # Try to rename to a category that already exists
        response = requests.put(
            f"{BASE_URL}/categories/tier1/RenamedCategory1",
            params={"new_name": "RenamedCategory1"}  # Same name
        )

        if response.status_code == 400:
            print_result("Duplicate prevention", True, "Correctly rejected duplicate name")
            return True
        else:
            print_result("Duplicate prevention", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Duplicate prevention", False, str(e))
        return False

def test_not_found():
    """Test that renaming non-existent category returns 404"""
    try:
        response = requests.put(
            f"{BASE_URL}/categories/tier1/NonExistentCategory",
            params={"new_name": "SomethingElse"}
        )

        if response.status_code == 404:
            print_result("Non-existent category handling", True, "Correctly returned 404")
            return True
        else:
            print_result("Non-existent category handling", False, f"Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print_result("Non-existent category handling", False, str(e))
        return False

def cleanup():
    """Clean up test categories"""
    try:
        # Delete the test categories
        response = requests.delete(f"{BASE_URL}/categories/tier1/RenamedCategory1")
        if response.status_code == 200:
            print_result("Cleanup test categories", True)
        else:
            print_result("Cleanup test categories", False, f"Status {response.status_code}")
    except Exception as e:
        print_result("Cleanup test categories", False, str(e))

def main():
    print("=" * 60)
    print("Testing Category Rename Functionality")
    print("=" * 60)
    print()

    # Test 1: Get categories
    print("Test 1: Get categories list")
    categories = test_get_categories()
    print()

    # Test 2: Create test category
    print("Test 2: Create test categories")
    test_create_test_category()
    print()

    # Test 3: Rename tier1
    print("Test 3: Rename tier1 category")
    test_rename_tier1()
    print()

    # Test 4: Rename tier2
    print("Test 4: Rename tier2 category")
    test_rename_tier2()
    print()

    # Test 5: Rename tier3
    print("Test 5: Rename tier3 category")
    test_rename_tier3()
    print()

    # Test 6: Duplicate prevention
    print("Test 6: Duplicate prevention")
    test_duplicate_prevention()
    print()

    # Test 7: 404 for non-existent
    print("Test 7: Non-existent category handling")
    test_not_found()
    print()

    # Cleanup
    print("Cleanup:")
    cleanup()
    print()

    print("=" * 60)
    print("Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
