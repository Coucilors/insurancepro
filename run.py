#!/usr/bin/env python3
"""
InsurancePro - Insurance Website with Email Campaign System
Run this script to start the application
"""

from app import app, init_db

if __name__ == '__main__':
    # Initialize database if needed
    init_db()
    
    print("="*60)
    print("InsurancePro Website Starting...")
    print("="*60)
    print("\nAccess the website at:")
    print("  Frontend: http://localhost:5000")
    print("  Admin:    http://localhost:5000/admin/login")
    print("\nDefault Admin Credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("\nPress CTRL+C to stop the server")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
