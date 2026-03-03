from werkzeug.security import generate_password_hash

print("admin:", generate_password_hash("admin123"))
print("manager:", generate_password_hash("manager123"))
print("employee1:", generate_password_hash("employee123"))
print("employee2:", generate_password_hash("employee123"))
