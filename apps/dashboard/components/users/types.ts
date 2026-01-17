// User types for the data table

export type UserStatus = 'active' | 'inactive' | 'banned' | 'pending'
export type UserRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  status: UserStatus
  role: UserRole
  mfaEnabled: boolean
  lastSignIn: string | null
  createdAt: string
  sessionsCount: number
  authMethods: string[]
}

export type UserActionType =
  | 'reset_password'
  | 'ban'
  | 'unban'
  | 'view_sessions'
  | 'delete'
  | 'change_role'

export interface UserAction {
  type: UserActionType
  userId: string
  userName?: string
}
