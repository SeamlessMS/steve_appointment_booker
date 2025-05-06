#!/usr/bin/env python3
"""
Steve Appointment Booker - Test Runner
This script runs all tests for the system.
"""

import os
import sys
import argparse
import logging
from importlib import import_module

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_runner")

# Add the parent directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

def run_test(test_name):
    """Run a specific test by name"""
    try:
        # Dynamically import and run the test
        module_name = f"tests.test_{test_name}"
        module = import_module(module_name)
        
        # Look for main test function
        if hasattr(module, f"test_{test_name}"):
            test_func = getattr(module, f"test_{test_name}")
        elif hasattr(module, "main"):
            test_func = module.main
        else:
            # Try to find any test_* function
            test_funcs = [f for f in dir(module) if f.startswith("test_") and callable(getattr(module, f))]
            if test_funcs:
                test_func = getattr(module, test_funcs[0])
            else:
                logger.error(f"No test function found in {module_name}")
                return False
        
        logger.info(f"Running {test_name} test...")
        result = test_func()
        return result is None or result
    except ImportError:
        logger.error(f"Test module {module_name} not found")
        return False
    except Exception as e:
        logger.error(f"Error running {test_name} test: {str(e)}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Steve Appointment Booker Test Runner')
    parser.add_argument('--test', type=str, help='Specific test to run (system, conversation, conversation_flow)')
    parser.add_argument('--phone', type=str, help='Phone number to use for test calls (format: 1234567890)')
    args = parser.parse_args()
    
    # If a phone number is provided, set an environment variable for test scripts
    if args.phone:
        os.environ['TEST_PHONE'] = args.phone
        logger.info(f"Using phone number: {args.phone} for tests")
    
    # If a specific test is requested, run only that test
    if args.test:
        success = run_test(args.test)
        sys.exit(0 if success else 1)
    
    # Otherwise run all tests
    logger.info("Running all tests...")
    
    # List of tests to run
    tests = [
        "system",
        "conversation_flow",
        # Add more tests here as they are added
    ]
    
    # Run each test
    results = {}
    for test in tests:
        logger.info(f"\n========== Running {test} test ==========")
        results[test] = run_test(test)
    
    # Print summary
    logger.info("\n========== Test Results ==========")
    for test, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test}: {status}")
    
    # Exit with appropriate status code
    if all(results.values()):
        logger.info("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.warning("\n⚠️ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 