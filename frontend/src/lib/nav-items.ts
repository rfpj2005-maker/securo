import {
  ArrowLeftRight,
  BarChart3,
  Building2,
  Landmark,
  PiggyBank,
  Receipt,
  Repeat,
  SlidersHorizontal,
  Split,
  Tag,
  Target,
  Upload,
  Users,
  Wallet,
} from 'lucide-react'
// Relative, not aliased: this file is pulled into the test project,
// which compiles without the `@/*` path mapping (see tsconfig.node.json).
import type { ModuleId } from './modules'

/**
 * Sidebar destinations. Lives outside `app-layout.tsx` so the filtering
 * below can be tested without mounting the whole layout.
 *
 * Every link carries the module it belongs to. That is what makes the
 * "a personal workspace shows exactly what it always showed" guarantee
 * checkable rather than aspirational.
 */
export type NavItem =
  | { type: 'link'; key: string; path: string; icon: React.ElementType; module: ModuleId }
  | { type: 'separator'; labelKey: string }
  | {
      type: 'group'
      key: string
      icon: React.ElementType
      items: { key: string; path: string; icon: React.ElementType; module: ModuleId }[]
    }

export const navItems: NavItem[] = [
  // The dashboard ("Painel") is now reachable by clicking the Securo
  // logo + name in the sidebar header — no dedicated menu item to keep
  // the sidebar focused on the main destinations. Everything money-related
  // lives under one collapsible "Finanças" group instead of flat sections,
  // so the sidebar reads as one financial-control area, not several.
  {
    type: 'group',
    key: 'finances',
    icon: Wallet,
    items: [
      { key: 'transactions', path: '/transactions', icon: ArrowLeftRight, module: 'transactions' },
      { key: 'invoices', path: '/invoices', icon: Receipt, module: 'invoices' },
      { key: 'accounts', path: '/accounts', icon: Building2, module: 'accounts' },
      { key: 'import', path: '/import', icon: Upload, module: 'import' },
      { key: 'reports', path: '/reports', icon: BarChart3, module: 'reports' },
      { key: 'assets', path: '/assets', icon: Landmark, module: 'assets' },
      { key: 'budgets', path: '/budgets', icon: PiggyBank, module: 'budgets' },
      { key: 'goals', path: '/goals', icon: Target, module: 'goals' },
      { key: 'recurring', path: '/recurring', icon: Repeat, module: 'recurring' },
      { key: 'categories', path: '/categories', icon: Tag, module: 'categories' },
      { key: 'payees', path: '/payees', icon: Users, module: 'payees' },
      { key: 'splitGroups', path: '/groups', icon: Split, module: 'split_groups' },
      { key: 'rules', path: '/rules', icon: SlidersHorizontal, module: 'rules' },
    ],
  },
]

/**
 * Drop links whose module is off, drop group children whose module is
 * off (and the whole group once it has no children left), then drop any
 * section header left with nothing under it. Without the second pass,
 * hiding a section's only link leaves a floating heading.
 */
export function visibleNavItems(
  items: NavItem[],
  hasModule: (id: ModuleId) => boolean,
): NavItem[] {
  const kept = items
    .map((item) => {
      if (item.type === 'group') {
        const children = item.items.filter((child) => hasModule(child.module))
        return children.length > 0 ? { ...item, items: children } : null
      }
      return item
    })
    .filter((item): item is NavItem => item !== null)
    .filter((item) => item.type !== 'link' || hasModule(item.module))
  return kept.filter((item, index) => {
    if (item.type !== 'separator') return true
    // Links always follow their own header, so the item right after a
    // header is either one of its links or the next header.
    const next = kept[index + 1]
    return next !== undefined && next.type === 'link'
  })
}
