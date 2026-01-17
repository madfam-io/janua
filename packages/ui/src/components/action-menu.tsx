'use client'

import * as React from 'react'
import { MoreHorizontal, type LucideIcon } from 'lucide-react'
import { Button } from './button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './dropdown-menu'
import { cn } from '../lib/utils'

/**
 * Action Menu - A reusable dropdown menu for row/item actions
 * 
 * @example
 * <ActionMenu
 *   label="User Actions"
 *   actions={[
 *     { label: 'Edit', icon: Pencil, onClick: () => {} },
 *     { label: 'Delete', icon: Trash2, onClick: () => {}, variant: 'destructive' },
 *   ]}
 * />
 */

export interface ActionItem {
  label: string
  icon?: LucideIcon
  onClick: () => void
  variant?: 'default' | 'destructive'
  disabled?: boolean
  hidden?: boolean
}

export interface ActionGroup {
  items: ActionItem[]
}

export interface ActionMenuProps {
  /** Label shown at the top of the menu */
  label?: string
  /** Array of action items or groups (separated by dividers) */
  actions: (ActionItem | ActionGroup)[]
  /** Custom trigger element */
  trigger?: React.ReactNode
  /** Alignment of the dropdown */
  align?: 'start' | 'center' | 'end'
  /** Additional class name for the trigger button */
  className?: string
  /** Accessible label for screen readers */
  srLabel?: string
}

function isActionGroup(item: ActionItem | ActionGroup): item is ActionGroup {
  return 'items' in item
}

export function ActionMenu({
  label = 'Actions',
  actions,
  trigger,
  align = 'end',
  className,
  srLabel = 'Open menu',
}: ActionMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {trigger || (
          <Button variant="ghost" className={cn('h-8 w-8 p-0', className)}>
            <span className="sr-only">{srLabel}</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align}>
        {label && <DropdownMenuLabel>{label}</DropdownMenuLabel>}
        {actions.map((item, index) => {
          if (isActionGroup(item)) {
            return (
              <React.Fragment key={index}>
                {index > 0 && <DropdownMenuSeparator />}
                {item.items
                  .filter((action) => !action.hidden)
                  .map((action, actionIndex) => (
                    <ActionMenuItem key={actionIndex} action={action} />
                  ))}
              </React.Fragment>
            )
          }

          if (item.hidden) return null

          return <ActionMenuItem key={index} action={item} />
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function ActionMenuItem({ action }: { action: ActionItem }) {
  const Icon = action.icon

  return (
    <DropdownMenuItem
      onClick={action.onClick}
      disabled={action.disabled}
      className={cn(action.variant === 'destructive' && 'text-destructive')}
    >
      {Icon && <Icon className="mr-2 h-4 w-4" />}
      {action.label}
    </DropdownMenuItem>
  )
}

export { ActionMenuItem }
