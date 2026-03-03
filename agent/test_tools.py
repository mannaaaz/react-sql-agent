from agent.tools import list_tables, describe_table, execute_sql

print(list_tables.run(""))
print(describe_table.run("customers"))
print(execute_sql.run("SELECT COUNT(*) FROM customers;"))