import Database from 'better-sqlite3'

let db: Database.Database | null = null

export function openDb(path = './db/pec.db'): Database.Database {
  if (!db) db = new Database(path, { readonly: true, fileMustExist: true })
  return db
}

/** 只读查询，统一返回行数组 */
export function all<T = unknown>(sql: string, params: unknown[] = []): T[] {
  return openDb().prepare(sql).all(...params) as T[]
}

export function one<T = unknown>(sql: string, params: unknown[] = []): T | undefined {
  return openDb().prepare(sql).get(...params) as T | undefined
}
