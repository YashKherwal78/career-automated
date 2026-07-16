import psycopg
import os
from dotenv import load_dotenv
load_dotenv("/Users/yashkherwal/Downloads/hrmailfiles/.env")

conn = psycopg.connect(os.getenv("DATABASE_URL"))
cur = conn.execute("SELECT t.typname, e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid;")
from collections import defaultdict
enums = defaultdict(list)
for r in cur.fetchall():
    enums[r[0]].append(r[1])
for k, v in enums.items():
    print(f"{k}: {v}")
