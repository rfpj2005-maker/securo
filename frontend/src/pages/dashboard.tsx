import { useState, useEffect, useMemo, useRef } from 'react'
import { getAccountName, formatAccountMask } from '@/lib/account-utils'
import { currentMonth, shiftMonth, monthLastDay, monthLabel, monthRange } from '@/lib/month-utils'
import { localDateString } from '@/lib/date-utils'
import { useTranslation } from 'react-i18next'
import { useDisplayLocale, useDateLocale } from '@/hooks/use-display-locale'
import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { dashboard, transactions, budgets, categories as categoriesApi, categoryGroups as categoryGroupsApi, accounts as accountsApi, goals as goalsApi, groups as groupsApi, payees as payeesApi, rules as rulesApi } from '@/lib/api'
import { invalidateFinancialQueries } from '@/lib/invalidate-queries'
import { toast } from 'sonner'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { ProjectedTransactionBadge } from '@/components/projected-transaction-badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { MonthPicker } from '@/components/ui/monthpicker'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { CheckCircle2, CalendarIcon, Clock, Paperclip, Target, ArrowUpDown, HelpCircle, EyeClosed, AlertTriangle, Lightbulb, TrendingUp, TrendingDown } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ICON_MAP } from '@/lib/category-icons'
import { PageHeader } from '@/components/page-header'
import { CategoryIcon } from '@/components/category-icon'
import { AccountIcon, getAccountTypeConfig } from '@/components/account-icon'
import { TransactionDrillDown, type DrillDownFilter } from '@/components/transaction-drill-down'
import { TransactionDialog, extractApiError, type TransactionSavePayload } from '@/components/transaction-dialog'
import { RuleDialog, type RuleDialogInitialData } from '@/components/rule-dialog'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import { useIsMobile } from '@/hooks/use-mobile'
import { useAuth } from '@/contexts/auth-context'
import { useWorkspace } from '@/contexts/workspace-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { resolveDateFnsLocale } from '@/lib/date-fns-locale'
import type { Rule, Transaction, Account } from '@/types'
import { formatCurrency } from '@/lib/format'
import { shouldShowPendingBadge } from '@/lib/transaction-status'

function formatDate(dateStr: string, locale = 'pt-BR') {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(locale)
}

// Mirrors accounts.tsx's local helper — days between today and a
// YYYY-MM-DD due date, used for the credit card "vence em N dias" hint.
function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(dateStr + 'T00:00:00')
  return Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

// Ported from account-detail.tsx's local helper of the same name — the
// [start, end] of the billing cycle containing `reference`. Without a
// statement_close_day (Pluggy often doesn't expose it) there's no cycle
// boundary to compute, so it falls back to "last month through today".
function creditCardCycleBoundaries(
  closeDay: number | null | undefined,
  reference: Date,
): { start: string; end: string } {
  if (!closeDay) {
    const y = reference.getFullYear()
    const m = reference.getMonth()
    return {
      start: format(new Date(y, m - 1, 1), 'yyyy-MM-dd'),
      end: format(reference, 'yyyy-MM-dd'),
    }
  }
  const ref0 = new Date(reference)
  ref0.setHours(0, 0, 0, 0)
  const y = ref0.getFullYear()
  const m = ref0.getMonth()
  const clamp = (yy: number, mm: number) => Math.min(closeDay, daysInMonth(yy, mm))
  const thisMonthClose = new Date(y, m, clamp(y, m))
  let nextClose: Date
  if (thisMonthClose.getTime() > ref0.getTime()) {
    nextClose = thisMonthClose
  } else {
    const nextY = m === 11 ? y + 1 : y
    const nextM = m === 11 ? 0 : m + 1
    nextClose = new Date(nextY, nextM, clamp(nextY, nextM))
  }
  const end = new Date(nextClose)
  end.setDate(end.getDate() - 1)
  const prevY = nextClose.getMonth() === 0 ? nextClose.getFullYear() - 1 : nextClose.getFullYear()
  const prevM = nextClose.getMonth() === 0 ? 11 : nextClose.getMonth() - 1
  const start = new Date(prevY, prevM, clamp(prevY, prevM))
  return { start: format(start, 'yyyy-MM-dd'), end: format(end, 'yyyy-MM-dd') }
}

function parseHashtags(notes: string | null): string[] {
  if (!notes) return []
  const matches = notes.match(/#[\w\u00C0-\u017E-]+/g)
  return matches ?? []
}

const MONTH_REGEX = /^\d{4}-\d{2}$/
const MONTH_STRING_LENGTH = 7

function parseMonthFromParams(params: URLSearchParams): string | null {
  const monthParam = params.get('month')
  if (monthParam && MONTH_REGEX.test(monthParam)) {
    return monthParam
  }

  const fromParam = params.get('from')
  if (fromParam && fromParam.length >= MONTH_STRING_LENGTH) {
    const parsedMonth = fromParam.substring(0, MONTH_STRING_LENGTH)
    if (MONTH_REGEX.test(parsedMonth)) {
      return parsedMonth
    }
  }

  return null
}


export default function DashboardPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { mask, privacyMode, MASK } = usePrivacyMode()
  const isMobile = useIsMobile()
  const { user } = useAuth()
  const { hasModule, isLoading: workspaceLoading } = useWorkspace()
  const userCurrency = user?.preferences?.currency_display ?? 'USD'
  const displayName = user?.preferences?.display_name || ''
  const locale = useDisplayLocale()
  const dateLocale = useDateLocale()

  const greeting = (() => {
    const hour = new Date().getHours()
    const key = hour < 12 ? 'greetingMorning' : hour < 18 ? 'greetingAfternoon' : 'greetingEvening'
    const base = t(`dashboard.${key}`)
    return displayName ? `${base}, ${displayName}` : base
  })()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedMonth, setSelectedMonth] = useState<string>(() => {
    return parseMonthFromParams(searchParams) ?? currentMonth()
  })
  const [drillDown, setDrillDown] = useState<DrillDownFilter | null>(null)

  const prevSearchRef = useRef<string | null>(null)

  // Sync state from URL when navigating (e.g. back/forward button)
  useEffect(() => {
    const search = searchParams.toString()
    if (prevSearchRef.current === search) return
    const isInitial = prevSearchRef.current === null
    prevSearchRef.current = search

    const parsedMonth = parseMonthFromParams(searchParams)
    if (parsedMonth) {
      setSelectedMonth(parsedMonth)
    } else if (!isInitial) {
      setSelectedMonth(currentMonth())
    }
  }, [searchParams])

  // Sync selectedMonth back to URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (selectedMonth) {
      params.set('month', selectedMonth)
      params.delete('from')
      params.delete('to')
    } else {
      params.delete('month')
    }

    setSearchParams(params, { replace: true })
  }, [selectedMonth, setSearchParams])
  const [editingTx, setEditingTx] = useState<Transaction | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [createRuleOpen, setCreateRuleOpen] = useState(false)
  const [createRuleInitialData, setCreateRuleInitialData] = useState<RuleDialogInitialData | undefined>(undefined)
  const queryClient = useQueryClient()
  const [headerCalOpen, setHeaderCalOpen] = useState(false)
  const [hoveredDay, setHoveredDay] = useState<number | null>(null)
  const dateFnsLocale = resolveDateFnsLocale(i18n.resolvedLanguage ?? i18n.language)
  const { from: monthStart, to: monthEnd } = monthRange(selectedMonth)
  const monthParam = monthStart
  const uiLocale = i18n.resolvedLanguage ?? i18n.language
  const monthLabelStr = monthLabel(selectedMonth, uiLocale)

  const handleMonthChange = (newMonth: string) => {
    setSelectedMonth(newMonth)
}

  // Active Collection filter (issue #105): scope dashboard cards to its
  // accounts. undefined when "All accounts".
  const { activeAccountIds, activeWalletIds } = useCollectionFilter()
  const acctIds = activeAccountIds ?? undefined
  const walletIds = activeWalletIds ?? undefined
  // A wallet-only collection (active, but with zero accounts) has no account
  // data — skip the account-only cards so they render empty instead of
  // silently falling back to "all accounts".
  const noAccounts = activeAccountIds !== null && activeAccountIds.length === 0

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['dashboard', 'summary', selectedMonth, activeAccountIds, activeWalletIds],
    queryFn: () => dashboard.summary(monthParam, undefined, acctIds, walletIds),
  })

  const { data: spending, isLoading: spendingLoading } = useQuery({
    queryKey: ['dashboard', 'spending', selectedMonth, activeAccountIds],
    queryFn: () => dashboard.spendingByCategory(monthParam, acctIds),
    enabled: !noAccounts,
  })

  const prevMonth = shiftMonth(selectedMonth, -1)

  const { data: balanceHistory, isLoading: balanceHistoryLoading } = useQuery({
    queryKey: ['dashboard', 'balance-history', selectedMonth, activeAccountIds],
    queryFn: () => dashboard.balanceHistory(monthParam, acctIds),
    enabled: !noAccounts,
  })

  const { data: currentMonthTxs, isLoading: currentTxLoading } = useQuery({
    queryKey: ['transactions', 'cumulative', selectedMonth, activeAccountIds],
    queryFn: () => transactions.list({
      from: monthStart,
      to: monthEnd,
      limit: 500,
      exclude_transfers: true,
      account_ids: acctIds,
    }),
    enabled: !noAccounts,
  })

  // Resolve group_id → name for the badge on split transactions.
  const { data: allGroups } = useQuery({
    queryKey: ['groups', 'all'],
    queryFn: () => groupsApi.list(true),
    staleTime: 60_000,
  })
  const groupNameById = useMemo(() => {
    const map = new Map<string, string>()
    for (const g of allGroups ?? []) map.set(g.id, g.name)
    return map
  }, [allGroups])

  const { data: projectedTxs, isLoading: projectedTxLoading } = useQuery({
    queryKey: ['dashboard', 'projected-transactions', selectedMonth],
    queryFn: () => dashboard.projectedTransactions({ month: monthParam }),
  })

  const { data: budgetComparison } = useQuery({
    queryKey: ['budgets', 'comparison', selectedMonth],
    queryFn: () => budgets.comparison(monthParam),
  })

  const { data: categoriesList } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })

  const { data: categoryGroupsList } = useQuery({
    queryKey: ['categoryGroups'],
    queryFn: categoryGroupsApi.list,
  })

  const { data: accountsList } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.list(),
  })

  // Top-of-page snapshot: a hand-picked set of accounts in a fixed order,
  // per the user's own priority list — not "all accounts" (that's the
  // Contas card further down). 'loan' is the Maçonaria financing, tracked
  // as a manual credit_card account with future-dated "Parcela N/20" rows
  // instead of real provider bills, so its due date comes from the next
  // unpaid installment transaction rather than account.next_due_date.
  const LOAN_ACCOUNT_ID = '7cf3d34e-4470-42e5-8fb3-d452b6fd9b8b'
  const TOP_ACCOUNTS_ORDER: { id: string; kind: 'balance' | 'card' | 'loan' }[] = [
    { id: '1b54a3c8-dcdb-4b40-9abf-5917cf480c39', kind: 'balance' }, // Nu Pagamentos — conta corrente
    { id: '0a310719-a59b-4c0b-9c06-f9101e15f9d5', kind: 'balance' }, // Banco Santander — conta corrente
    { id: 'c34fa75b-b4f7-4bc7-a7eb-d7d6ee38841d', kind: 'card' }, // platinum (Nubank)
    { id: 'ed6346ae-78dc-42b5-b5cd-dd835ec731b1', kind: 'card' }, // Santander •••• 2310
    { id: '4207a13d-21dc-4876-8bab-27a43da49fa2', kind: 'card' }, // Mercado Pago (cartão)
    { id: 'dea0e6e3-ab07-4f62-bebc-332845f496d1', kind: 'balance' }, // Carteira
    { id: LOAN_ACCOUNT_ID, kind: 'loan' }, // Empréstimo Maçonaria
  ]
  const topAccountRows = TOP_ACCOUNTS_ORDER
    .map((row) => {
      const acc = accountsList?.find((a) => a.id === row.id)
      return acc ? { ...row, account: acc } : null
    })
    .filter((row): row is { id: string; kind: 'balance' | 'card' | 'loan'; account: Account } => row !== null)

  const { data: nextInstallment } = useQuery({
    queryKey: ['transactions', 'next-installment', LOAN_ACCOUNT_ID],
    queryFn: () =>
      transactions.list({
        account_id: LOAN_ACCOUNT_ID,
        from: localDateString(),
        sort_by: 'date',
        sort_dir: 'asc',
        limit: 1,
      }),
    enabled: topAccountRows.some((r) => r.id === LOAN_ACCOUNT_ID),
  })
  const nextInstallmentTx = nextInstallment?.items[0] ?? null

  // The card rows' "próxima fatura" is NOT account.current_balance (that's
  // total debt, incl. installment purchases due on later cycles) — it's
  // either the next real bill from the provider's bills feed, or, when
  // that bill hasn't closed yet, the running total of unbilled charges for
  // the in-progress cycle (mirrors account-detail.tsx's "Total da fatura").
  const cardRows = topAccountRows.filter((r) => r.kind === 'card')
  const today = localDateString()

  const billsQueries = useQueries({
    queries: cardRows.map((r) => ({
      queryKey: ['accounts', r.id, 'bills', 'dashboard-top'],
      queryFn: () => accountsApi.bills(r.id, 3),
    })),
  })

  const cycleQueries = useQueries({
    queries: cardRows.map((r, i) => {
      const bills = [...(billsQueries[i]?.data ?? [])].sort((a, b) => a.due_date.localeCompare(b.due_date))
      const upcomingBill = bills.find((b) => b.due_date >= today)
      const { start, end } = creditCardCycleBoundaries(r.account.statement_close_day, new Date())
      return {
        queryKey: ['accounts', r.id, 'summary', 'unbilled-cycle', start, end],
        queryFn: () => accountsApi.summary(r.id, start, end, undefined, true),
        enabled: !upcomingBill,
      }
    }),
  })

  const nextBillByAccountId = useMemo(() => {
    const map = new Map<string, { amount: number; currency: string; dueDate: string | null }>()
    cardRows.forEach((r, i) => {
      const bills = [...(billsQueries[i]?.data ?? [])].sort((a, b) => a.due_date.localeCompare(b.due_date))
      const upcomingBill = bills.find((b) => b.due_date >= today)
      if (upcomingBill) {
        map.set(r.id, { amount: upcomingBill.total_amount, currency: r.account.currency, dueDate: upcomingBill.due_date })
      } else {
        const cycleSummary = cycleQueries[i]?.data
        map.set(r.id, {
          amount: cycleSummary ? Number(cycleSummary.monthly_expenses_primary ?? cycleSummary.monthly_expenses) : 0,
          currency: r.account.currency,
          dueDate: r.account.next_due_date,
        })
      }
    })
    return map
  }, [cardRows, billsQueries, cycleQueries, today])

  const { data: payeesList } = useQuery({
    queryKey: ['payees'],
    queryFn: payeesApi.list,
  })

  const { data: goalsSummary } = useQuery({
    queryKey: ['goals', 'summary'],
    queryFn: () => goalsApi.summary(3),
  })

  // Lightweight, rule-based suggestions computed entirely from data already
  // on this page — no extra API calls. Ranked high → low so the most
  // urgent thing (overspending, negative balance) surfaces first.
  type Suggestion = {
    id: string
    severity: 'high' | 'medium' | 'low'
    icon: typeof AlertTriangle
    title: string
    description: string
    to?: string
  }
  const suggestions = useMemo<Suggestion[]>(() => {
    const items: Suggestion[] = []
    if (!summary) return items

    if (summary.monthly_income > 0 && summary.monthly_expenses > summary.monthly_income) {
      const overBy = summary.monthly_expenses - summary.monthly_income
      items.push({
        id: 'expenses-over-income',
        severity: 'high',
        icon: TrendingDown,
        title: t('dashboard.suggestions.expensesOverIncomeTitle'),
        description: t('dashboard.suggestions.expensesOverIncomeDesc', { amount: mask(formatCurrency(overBy, userCurrency, locale)) }),
        to: '/reports',
      })
    }

    for (const acc of accountsList ?? []) {
      if (!acc.is_closed && acc.current_balance < 0 && acc.type !== 'credit_card') {
        items.push({
          id: `negative-balance-${acc.id}`,
          severity: 'high',
          icon: AlertTriangle,
          title: t('dashboard.suggestions.negativeBalanceTitle'),
          description: t('dashboard.suggestions.negativeBalanceDesc', {
            account: getAccountName(acc),
            amount: mask(formatCurrency(acc.current_balance, acc.currency, locale)),
          }),
          to: `/accounts/${acc.id}`,
        })
      }
    }

    if (summary.pending_categorization > 0) {
      items.push({
        id: 'pending-categorization',
        severity: 'medium',
        icon: Lightbulb,
        title: t('dashboard.suggestions.pendingCategorizationTitle', { count: summary.pending_categorization }),
        description: t('dashboard.suggestions.pendingCategorizationDesc', { amount: mask(formatCurrency(summary.pending_categorization_amount, userCurrency, locale)) }),
        to: '/transactions?uncategorized=true',
      })
    }

    for (const b of budgetComparison ?? []) {
      if (b.budget_amount && b.percentage_used != null && b.percentage_used > 100) {
        items.push({
          id: `budget-over-${b.category_id}`,
          severity: b.percentage_used > 150 ? 'high' : 'medium',
          icon: TrendingUp,
          title: t('dashboard.suggestions.budgetOverTitle', { category: b.category_name }),
          description: t('dashboard.suggestions.budgetOverDesc', { pct: Math.round(b.percentage_used) }),
          to: '/budgets',
        })
      } else if (b.budget_amount && b.prev_month_amount > 0 && b.actual_amount > b.prev_month_amount * 1.3) {
        const pct = Math.round(((b.actual_amount - b.prev_month_amount) / b.prev_month_amount) * 100)
        items.push({
          id: `spend-spike-${b.category_id}`,
          severity: 'low',
          icon: TrendingUp,
          title: t('dashboard.suggestions.spendSpikeTitle', { category: b.category_name }),
          description: t('dashboard.suggestions.spendSpikeDesc', { pct }),
          to: '/reports',
        })
      }
    }

    for (const g of goalsSummary ?? []) {
      if (g.on_track === 'behind' || g.on_track === 'overdue') {
        items.push({
          id: `goal-${g.id}`,
          severity: g.on_track === 'overdue' ? 'high' : 'low',
          icon: Target,
          title: t('dashboard.suggestions.goalBehindTitle', { goal: g.name }),
          description: t('dashboard.suggestions.goalBehindDesc'),
          to: '/goals',
        })
      }
    }

    const order = { high: 0, medium: 1, low: 2 }
    return items.sort((a, b) => order[a.severity] - order[b.severity]).slice(0, 5)
  }, [summary, accountsList, budgetComparison, goalsSummary, userCurrency, locale, mask, t])

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: TransactionSavePayload & { id: string }) =>
      transactions.update(id, data),
    onSuccess: () => {
      invalidateFinancialQueries(queryClient)
      setDialogOpen(false)
      setEditingTx(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => transactions.delete(id),
    onSuccess: () => {
      invalidateFinancialQueries(queryClient)
      setDialogOpen(false)
      setEditingTx(null)
    },
  })

  const unlinkTransferMutation = useMutation({
    mutationFn: (pairId: string) => transactions.unlinkTransfer(pairId),
    onSuccess: () => {
      invalidateFinancialQueries(queryClient)
      setDialogOpen(false)
      setEditingTx(null)
    },
  })

  const createRuleMutation = useMutation({
    mutationFn: (data: Omit<Rule, 'id' | 'user_id'>) => rulesApi.create(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      setCreateRuleOpen(false)
      setCreateRuleInitialData(undefined)
      const applied = result.applied_count ?? 0
      if (applied > 0) {
        invalidateFinancialQueries(queryClient)
        queryClient.invalidateQueries({ queryKey: ['payees'] })
        toast.success(t('rules.createdAndApplied', { count: applied }))
      } else {
        toast.success(t('rules.created'))
      }
    },
    onError: (error: unknown) => {
      const err = error as { response?: { status?: number } }
      if (err?.response?.status === 409) {
        toast.error(t('rules.duplicateName'))
      } else {
        toast.error(t('common.error'))
      }
    },
  })

  const handleCreateRuleFromTransaction = (tx: Transaction) => {
    const conditions = [
      { field: 'description', op: 'contains', value: tx.description },
    ]
    if (tx.payee_id) {
      conditions.push({ field: 'payee_id', op: 'equals', value: tx.payee_id })
    }
    const actions = tx.category_id
      ? [{ op: 'set_category', value: tx.category_id }]
      : [{ op: 'set_category', value: '' }]
    const tags = parseHashtags(tx.notes)
    if (tags.length > 0) {
      actions.push({ op: 'append_notes', value: tags.join(' ') })
    }
    setCreateRuleInitialData({ conditions, actions })
    setCreateRuleOpen(true)
  }


  const cumulativeData = useMemo(() => {
    if (!balanceHistory) return []
    const daysInMonth = monthLastDay(selectedMonth)
    const result: { day: number; current: number | null; previous: number }[] = []
    let lastPrevBalance = 0
    for (let day = 1; day <= daysInMonth; day++) {
      const cur = balanceHistory.current.find(d => d.day === day)
      const prev = balanceHistory.previous.find(d => d.day === day)
      if (prev?.balance != null) {
        lastPrevBalance = prev.balance
      }
      result.push({
        day,
        current: cur?.balance ?? null,
        previous: prev?.balance ?? lastPrevBalance,
      })
    }
    return result
  }, [balanceHistory, selectedMonth])

  const lastCurrentPoint = [...cumulativeData].reverse().find(d => d.current !== null)
  const lastDay = lastCurrentPoint?.day ?? 0
  const currentStartBalance = balanceHistory?.current.find(d => d.day === 1)?.balance ?? 0
  const currentLatestBalance = lastCurrentPoint?.current ?? 0
  const monthVariation = currentLatestBalance - currentStartBalance

  const totalBalance = summary?.total_balance_primary ?? Object.values(summary?.total_balance ?? {}).reduce((a, b) => a + Number(b), 0)

  // Uncategorized data
  const uncategorizedCount = summary?.pending_categorization ?? 0
  const uncategorizedAmount = summary?.pending_categorization_amount ?? 0

  const [catSortDesc, setCatSortDesc] = useState(true)

  // Merged category bars data
  const mergedCategories = useMemo(() => {
    if (!spending) return []
    const budgetMap = new Map<string, (typeof budgetComparison extends (infer T)[] | undefined ? T : never)>()
    if (budgetComparison) {
      for (const b of budgetComparison) {
        budgetMap.set(b.category_id, b)
      }
    }
    return spending
      .filter(s => s.category_id !== null)
      .map(s => {
        const budget = s.category_id ? budgetMap.get(s.category_id) : undefined
        const actual = s.total
        const prevAmount = budget ? Number(budget.prev_month_amount) : 0
        let momPct: number | null = null
        if (prevAmount > 0) {
          momPct = ((actual - prevAmount) / prevAmount) * 100
        } else if (actual > 0) {
          momPct = 100
        }
        return {
          category_id: s.category_id!,
          category_name: s.category_name,
          category_icon: s.category_icon,
          category_color: s.category_color,
          actual,
          budget_amount: budget ? Number(budget.budget_amount) : null,
          percentage_used: budget?.percentage_used ?? null,
          momPct,
        }
      })
      .sort((a, b) => catSortDesc ? b.actual - a.actual : a.actual - b.actual)
  }, [spending, budgetComparison, catSortDesc])

  const [txPage, setTxPage] = useState(1)
  const [txSortDesc, setTxSortDesc] = useState(true)
  useEffect(() => setTxPage(1), [selectedMonth])

  type DisplayRow = {
    key: string
    description: string
    date: string
    type: 'debit' | 'credit'
    amount: number
    amountPrimary: number | null
    currency: string
    categoryIcon: string | null
    categoryName: string | null
    categoryColor: string | null
    accountId: string | null
    isProjected: boolean
    attachmentCount: number
    isShared: boolean
    parentTotal: number | null
    // Owner-side: this user's share of a split they own. Null when
    // they're not in the split, or when share == amount (would be a
    // redundant secondary line).
    ownerShare: number | null
    groupId: string | null
    parentOwnerName: string | null
    groupName: string | null
    isIgnored: boolean
    installmentNumber: number | null
    totalInstallments: number | null
    showPendingBadge: boolean
  }

  const [txPerPage, setTxPerPage] = useState<number>(() => {
    try {
      const stored = localStorage.getItem('securo.dashboard.pageSize')
      return stored ? Number(stored) : 10
    } catch {
      return 10
    }
  })
  const allDisplayRows = useMemo(() => {
    const rows: DisplayRow[] = []
    for (const tx of currentMonthTxs?.items ?? []) {
      const isShared = !!tx.is_shared
      const displayAmount =
        isShared && tx.viewer_share != null ? Number(tx.viewer_share) : Number(tx.amount)
      const groupId = tx.group_id ?? null
      // Owner-side share: backend populates viewer_share for owners
      // who participate in their own split. Suppress when it equals
      // the parent amount (sole-member case = no useful info).
      const ownerShareRaw =
        !isShared && tx.viewer_share != null ? Number(tx.viewer_share) : null
      const ownerShare =
        ownerShareRaw != null && Math.abs(ownerShareRaw) !== Math.abs(Number(tx.amount))
          ? ownerShareRaw
          : null
      rows.push({
        key: tx.id,
        description: tx.description,
        date: tx.date,
        type: tx.type,
        amount: displayAmount,
        amountPrimary: tx.amount_primary != null ? Number(tx.amount_primary) : null,
        currency: tx.currency,
        categoryIcon: tx.category?.icon ?? null,
        categoryName: tx.category?.name ?? null,
        categoryColor: tx.category?.color ?? null,
        accountId: tx.account_id ?? null,
        isProjected: false,
        attachmentCount: tx.attachment_count ?? 0,
        isShared,
        parentTotal: isShared ? Number(tx.amount) : null,
        ownerShare,
        groupId,
        parentOwnerName: isShared ? tx.parent_owner_name ?? null : null,
        groupName: groupId ? groupNameById.get(groupId) ?? null : null,
        isIgnored: tx.is_ignored,
        installmentNumber: tx.installment_number,
        totalInstallments: tx.total_installments,
        showPendingBadge: shouldShowPendingBadge(tx),
      })
    }
    for (const pt of projectedTxs ?? []) {
      rows.push({
        key: `proj-${pt.recurring_id}-${pt.date}`,
        description: pt.description,
        date: pt.date,
        type: pt.type,
        amount: pt.amount,
        amountPrimary: pt.amount_primary ?? null,
        currency: pt.currency,
        categoryIcon: pt.category_icon,
        categoryName: pt.category_name,
        categoryColor: pt.category_color ?? null,
        accountId: pt.account_id,
        isProjected: true,
        attachmentCount: 0,
        isShared: false,
        parentTotal: null,
        ownerShare: null,
        groupId: null,
        parentOwnerName: null,
        groupName: null,
        isIgnored: false,
        installmentNumber: null,
        totalInstallments: null,
        showPendingBadge: false,
      })
    }
    rows.sort((a, b) => txSortDesc ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date))
    return rows
  }, [currentMonthTxs, projectedTxs, txSortDesc, groupNameById])

  const txTotalPages = Math.ceil(allDisplayRows.length / txPerPage)
  const pagedRows = allDisplayRows.slice((txPage - 1) * txPerPage, txPage * txPerPage)
  const txListLoading = currentTxLoading || projectedTxLoading

  // The Dashboard is the one page every member always lands on — unlike
  // every other page in the app, it was never wrapped in ModuleRoute, so
  // a member whose owner hid the `transactions` module (WorkspaceMemberHiddenModule)
  // still saw full workspace financials here even though the nav link
  // itself was correctly hidden. The API now backs this up with a real
  // 403 (require_module in workspace_context.py), but the UI should
  // never even ask for data this member isn't meant to see.
  if (!workspaceLoading && !hasModule('transactions')) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-2 px-4">
        <p className="text-lg font-medium">{t('dashboard.noAccessTitle')}</p>
        <p className="text-sm text-muted-foreground max-w-sm">{t('dashboard.noAccessDescription')}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <PageHeader
        section={greeting}
        title={monthLabel(selectedMonth, uiLocale).replace(/^\w/, c => c.toUpperCase())}
        action={
          <div className="flex items-center gap-1">
            <button
              className="h-8 w-8 flex items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:border-border hover:text-foreground transition-all text-base"
              onClick={() => handleMonthChange(shiftMonth(selectedMonth, -1))}
            >&#8249;</button>
            <Popover open={headerCalOpen} onOpenChange={setHeaderCalOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-2 border border-border rounded-lg px-3 py-1.5 text-sm bg-card text-foreground hover:bg-muted/50 transition-all cursor-pointer min-w-[180px]"
                >
                  <CalendarIcon className="size-3.5 text-muted-foreground" />
                  {monthLabel(selectedMonth, uiLocale).replace(/^\w/, c => c.toUpperCase())}
                </button>
              </PopoverTrigger>
              <PopoverContent align="center" className="w-auto p-0">
                <MonthPicker
                  locale={dateFnsLocale}
                  selectedMonth={new Date(`${selectedMonth}-01T00:00:00`)}
                  onMonthSelect={(date) => {
                    if (!date) return
                    const newMonth = format(date, 'yyyy-MM')
                    setSelectedMonth(newMonth)
                    setHeaderCalOpen(false)
                  }}
                />
              </PopoverContent>
            </Popover>
            <button
              className="h-8 w-8 flex items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:border-border hover:text-foreground transition-all text-base"
              onClick={() => handleMonthChange(shiftMonth(selectedMonth, 1))}
            >&#8250;</button>
          </div>
        }
      />

      {/* Top snapshot: a fixed, hand-picked account order (not the full
          account list — see the Contas card below for that). */}
      {topAccountRows.length > 0 && (
        <div className="bg-card rounded-xl border border-border shadow-sm mb-5">
          <div className="divide-y divide-border">
            {topAccountRows.map(({ id, kind, account: acc }) => {
              const cfg = getAccountTypeConfig(acc.type)
              const accountMask = formatAccountMask(acc)

              if (kind === 'loan') {
                const installmentMatch = nextInstallmentTx?.description.match(/(\d+)\/(\d+)/)
                return (
                  <Link key={id} to={`/accounts/${acc.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-muted/50 transition-colors">
                    <AccountIcon account={acc} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground truncate">{getAccountName(acc)}</p>
                      <p className="text-xs text-muted-foreground">
                        {t('dashboard.nextInstallment', { defaultValue: 'Próxima parcela' })}
                        {installmentMatch && <> · {installmentMatch[0]}</>}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      {nextInstallmentTx ? (
                        <>
                          <p className="text-sm font-semibold tabular-nums text-rose-500">
                            {mask(formatCurrency(Number(nextInstallmentTx.amount), nextInstallmentTx.currency, locale))}
                          </p>
                          <p className="text-[10px] text-muted-foreground tabular-nums">
                            {formatDate(nextInstallmentTx.date, locale)}
                          </p>
                        </>
                      ) : (
                        <p className="text-xs text-muted-foreground">{t('dashboard.noInstallments', { defaultValue: 'Sem parcelas futuras' })}</p>
                      )}
                    </div>
                  </Link>
                )
              }

              const isCC = kind === 'card'
              const nextBill = isCC ? nextBillByAccountId.get(id) : null
              const bal = isCC ? (nextBill?.amount ?? 0) : Number(acc.current_balance)
              const dueDate = isCC ? nextBill?.dueDate ?? null : null
              const dueIn = dueDate ? daysUntil(dueDate) : null
              const dueText =
                dueIn == null ? null
                  : dueIn < 0 ? t('accounts.overdue')
                  : dueIn === 0 ? t('accounts.dueToday')
                  : t('accounts.dueIn', { count: dueIn })
              const dueClass = dueIn != null && dueIn <= 3 ? 'text-amber-600' : 'text-muted-foreground'
              return (
                <Link key={id} to={`/accounts/${acc.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-muted/50 transition-colors">
                  <AccountIcon account={acc} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground truncate">{getAccountName(acc)}</p>
                    <p className="text-xs text-muted-foreground">
                      {isCC ? t('dashboard.nextCardBill', { defaultValue: 'Próxima fatura' }) : t(cfg.label)}
                      {accountMask && <> · <span className="tabular-nums">{accountMask}</span></>}
                      {dueText && <> · <span className={dueClass}>{dueText}</span></>}
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className={`text-sm font-semibold tabular-nums ${(isCC ? bal > 0 : bal < 0) ? 'text-rose-500' : 'text-foreground'}`}>
                      {mask(formatCurrency(bal, nextBill?.currency ?? acc.currency, locale))}
                    </p>
                    {isCC && acc.available_credit != null && (
                      <p className="text-[10px] text-muted-foreground tabular-nums">
                        {t('accounts.availableCredit')}: {mask(formatCurrency(Number(acc.available_credit), acc.currency, locale))}
                      </p>
                    )}
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* Hero Card: Uncategorized CTA */}
      <div className="bg-card rounded-xl border border-border shadow-sm mb-5">
        <div className="px-5 py-4 flex flex-col items-center justify-center text-center">
          {summaryLoading ? (
            <Skeleton className="h-16 w-16 rounded-full" />
          ) : uncategorizedCount > 0 ? (
            <div
              className="cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => setDrillDown({
                title: t('dashboard.drillDownUncategorized'),
                uncategorized: true,
              })}
            >
              <div className={`w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold text-white mx-auto mb-2 ${
                uncategorizedCount >= 20 ? 'bg-amber-500' : 'bg-amber-400'
              }`}>
                {uncategorizedCount}
              </div>
              <p className="text-sm font-medium text-foreground">
                {t('dashboard.uncategorizedCta', { count: uncategorizedCount })}
              </p>
              {uncategorizedAmount > 0 && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {mask(t('dashboard.uncategorizedTotal', { amount: formatCurrency(uncategorizedAmount, userCurrency, locale) }))}
                </p>
              )}
              <p className="text-sm font-semibold text-amber-600 mt-2 hover:underline">
                {t('dashboard.categorizeNow')} &rarr;
              </p>
            </div>
          ) : (
            <div>
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-1.5" />
              <p className="text-sm font-semibold text-foreground">{t('dashboard.allCategorized')}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{t('dashboard.allCategorizedDesc')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Charts: Category Spending Bars + Balance Flow */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5" style={{ gridAutoRows: 'minmax(380px, auto)' }}>
        {/* Category Spending Bars */}
        <div className="bg-card rounded-xl border border-border shadow-sm flex flex-col max-h-[420px]">
          <div className="px-5 py-4 border-b border-border shrink-0 flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">{t('dashboard.spendingByCategory')}</p>
            <button
              onClick={() => setCatSortDesc(v => !v)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <ArrowUpDown size={13} />
              {catSortDesc ? t('dashboard.sortHighest') : t('dashboard.sortLowest')}
            </button>
          </div>
          <div className="p-3 overflow-y-auto flex-1">
            {spendingLoading ? (
              <div className="space-y-3 p-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : mergedCategories.length > 0 ? (
              <div className="space-y-1.5">
                {mergedCategories.map((item) => {
                  const hasBudget = item.budget_amount != null && item.budget_amount > 0
                  const pct = item.percentage_used
                  const barColor = hasBudget
                    ? pct! > 100 ? 'bg-rose-500' : pct! >= 80 ? 'bg-amber-400' : 'bg-emerald-500'
                    : 'bg-muted-foreground/20'

                  return (
                    <div
                      key={item.category_id}
                      className="rounded-lg px-3 py-2.5 hover:bg-muted/50 transition-colors cursor-pointer"
                      onClick={() => setDrillDown({
                        title: t('dashboard.drillDownCategory', { category: item.category_name, month: monthLabelStr }),
                        category_id: item.category_id,
                        type: 'debit',
                        from: monthStart,
                        to: monthEnd,
                      })}
                    >
                      <div className="flex items-center gap-3">
                        <CategoryIcon icon={item.category_icon} color={item.category_color} size="lg" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="text-sm font-semibold text-foreground truncate">{item.category_name}</span>
                            <div className="flex items-center gap-2 shrink-0">
                              <span className="text-sm font-bold tabular-nums text-foreground">{mask(formatCurrency(item.actual, userCurrency, locale))}</span>
                              {item.momPct !== null && (
                                <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold tabular-nums ${
                                  item.momPct > 0 ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-400' : item.momPct < 0 ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400' : 'bg-muted text-muted-foreground'
                                }`}>
                                  {item.momPct > 0 ? '\u2191' : item.momPct < 0 ? '\u2193' : '='}{Math.abs(item.momPct).toFixed(0)}%
                                </span>
                              )}
                            </div>
                          </div>
                          {hasBudget && (
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-1.5 bg-muted/60 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all ${barColor}`}
                                  style={{ width: `${Math.min(pct!, 100)}%` }}
                                />
                              </div>
                              <span className={`text-[11px] tabular-nums font-medium shrink-0 ${
                                pct! > 100 ? 'text-rose-500' : pct! >= 80 ? 'text-amber-500' : 'text-muted-foreground'
                              }`}>
                                {mask(t('dashboard.ofBudget', { budget: formatCurrency(item.budget_amount!, userCurrency, locale) }))}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm text-center py-12">{t('dashboard.noData')}</p>
            )}
          </div>
        </div>

        {/* Cumulative Spending Comparison */}
        <div className="bg-card rounded-xl border border-border shadow-sm max-h-[420px] flex flex-col">
          <div className="px-5 pt-5 pb-3 shrink-0">
            <div className="flex items-start justify-between mb-0.5">
              <div>
                <p className="text-base font-bold text-foreground">{t('dashboard.balanceFlow')}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {new Date(`${selectedMonth}-01T00:00:00`).toLocaleDateString(dateLocale)} → {new Date(`${selectedMonth}-${String(lastCurrentPoint?.day ?? monthLastDay(selectedMonth)).padStart(2, '0')}T00:00:00`).toLocaleDateString(dateLocale)}
                </p>
              </div>
              {!balanceHistoryLoading && lastCurrentPoint && (
                <span className={`text-lg font-bold tabular-nums ${monthVariation >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                  {mask(`${monthVariation > 0 ? '+' : ''}${formatCurrency(monthVariation, userCurrency, locale)}`)}
                </span>
              )}
            </div>
          </div>
          <div className="px-1 pb-4 flex-1 min-h-0">
            {balanceHistoryLoading ? (
              <Skeleton className="h-full w-full" />
            ) : cumulativeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={cumulativeData}
                  margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                  className="cursor-pointer"
                  onMouseMove={(state) => {
                    const idx = state?.activeTooltipIndex
                    if (typeof idx === 'number') {
                      const point = cumulativeData[idx]
                      if (point) setHoveredDay(point.day)
                    }
                  }}
                  onMouseLeave={() => setHoveredDay(null)}
                  onClick={(_state) => {
                    // Access activePayload from the underlying native event target chart state
                    const chartState = _state as unknown as { activePayload?: Array<{ payload: { day: number } }> }
                    const payload = chartState?.activePayload ?? []
                    if (payload[0]) {
                      const day = String(payload[0].payload.day).padStart(2, '0')
                      const dateStr = `${selectedMonth}-${day}`
                      setDrillDown({
                        title: t('dashboard.drillDownDay', { date: new Date(dateStr + 'T00:00:00').toLocaleDateString(dateLocale) }),
                        from: dateStr,
                        to: dateStr,
                      })
                    }
                  }}
                >
                  <defs>
                    <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.18} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    axisLine={false}
                    tickLine={false}
                    interval={3}
                  />
                  <YAxis
                    tickFormatter={(v) => {
                      if (privacyMode) return ''
                      if (v === 0) return '0'
                      return formatCurrency(v, userCurrency, locale).replace(/,00$/, '').replace(/\.00$/, '')
                    }}
                    tick={{ fontSize: 10, fill: 'var(--muted-foreground)' }}
                    axisLine={false}
                    tickLine={false}
                    width={56}
                    tickCount={5}
                    domain={[
                      (dataMin: number) => dataMin < 0 ? Math.floor(dataMin / 100) * 100 : 0,
                      (dataMax: number) => Math.ceil(dataMax / 100) * 100,
                    ]}
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      value !== null ? (privacyMode ? MASK : formatCurrency(Number(value), userCurrency, locale)) : '\u2014',
                      name === 'current' ? monthLabel(selectedMonth, uiLocale).split(' ')[0] : monthLabel(prevMonth, uiLocale).split(' ')[0],
                    ]}
                    labelFormatter={(day) => t('dashboard.day', { day })}
                    contentStyle={{
                      background: 'var(--card)',
                      color: 'var(--foreground)',
                      border: '1px solid var(--border)',
                      borderRadius: '0.75rem',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="current"
                    stroke="#10B981"
                    strokeWidth={2}
                    fill="url(#cumGrad)"
                    dot={false}
                    activeDot={{ r: 3, fill: '#10B981' }}
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="previous"
                    stroke="#94A3B8"
                    strokeWidth={2}
                    strokeDasharray="5 3"
                    dot={false}
                    activeDot={{ r: 3, fill: '#94A3B8' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm text-center py-12">{t('dashboard.noData')}</p>
            )}
          </div>
          {!balanceHistoryLoading && lastCurrentPoint && (() => {
            const footerDay = hoveredDay ?? lastDay
            const footerPrev = balanceHistory?.previous.find(d => d.day === footerDay)?.balance ?? 0
            const footerCurrent = cumulativeData.find(d => d.day === footerDay)?.current ?? totalBalance
            const footerPct = footerPrev !== 0 ? ((footerCurrent - footerPrev) / Math.abs(footerPrev)) * 100 : null
            if (footerPrev === 0 || footerPct === null) return null
            return (
              <div className="px-5 pb-4 pt-0 shrink-0">
                <p className="text-xs text-muted-foreground">
                  {t('dashboard.balanceFlowVsPrev', {
                    month: monthLabel(prevMonth, uiLocale).split(' ')[0],
                    day: footerDay,
                    amount: mask(formatCurrency(footerPrev, userCurrency, locale)),
                    delta: `${footerPct >= 0 ? '+' : ''}${footerPct.toFixed(1)}%`,
                  })}
                  {' '}
                  <span className={footerPct >= 0 ? 'text-emerald-600' : 'text-rose-500'}>
                    {footerPct >= 0 ? '\u25B2' : '\u25BC'}
                  </span>
                </p>
              </div>
            )
          })()}
        </div>
      </div>

      {/* Financial control suggestions — rule-based, computed from data already on this page */}
      {suggestions.length > 0 && (
        <div className="bg-card rounded-xl border border-border shadow-sm mb-5">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <Lightbulb size={15} className="text-amber-500" />
            <p className="text-sm font-semibold text-foreground">{t('dashboard.suggestions.title')}</p>
          </div>
          <div className="divide-y divide-border">
            {suggestions.map((s) => {
              const severityColor = s.severity === 'high' ? 'text-rose-500 bg-rose-50 dark:bg-rose-950/30' : s.severity === 'medium' ? 'text-amber-600 bg-amber-50 dark:bg-amber-950/30' : 'text-blue-600 bg-blue-50 dark:bg-blue-950/30'
              const Content = (
                <div className="px-5 py-3 flex items-start gap-3">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${severityColor}`}>
                    <s.icon size={14} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{s.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{s.description}</p>
                  </div>
                </div>
              )
              return s.to ? (
                <Link key={s.id} to={s.to} className="block hover:bg-muted/40 transition-colors">
                  {Content}
                </Link>
              ) : (
                <div key={s.id}>{Content}</div>
              )
            })}
          </div>
        </div>
      )}

      {/* Goals Progress Widget */}
      {goalsSummary && goalsSummary.length > 0 && (
        <div className="bg-card rounded-xl border border-border shadow-sm mb-5">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">{t('goals.dashboardTitle')}</p>
            <Link to="/goals" className="text-xs font-medium text-primary hover:underline">
              {t('goals.viewAll')} &rarr;
            </Link>
          </div>
          <div className="divide-y divide-border">
            {goalsSummary.map((goal) => {
              const progressColor = goal.percentage >= 100
                ? 'bg-emerald-500'
                : goal.percentage >= 60
                  ? 'bg-blue-500'
                  : goal.percentage >= 30
                    ? 'bg-amber-400'
                    : 'bg-muted-foreground/30'
              const onTrackConfig: Record<string, { cls: string; key: string }> = {
                ahead: { cls: 'text-emerald-600', key: 'goals.onTrackAhead' },
                on_track: { cls: 'text-blue-600', key: 'goals.onTrackOnTrack' },
                behind: { cls: 'text-amber-600', key: 'goals.onTrackBehind' },
                overdue: { cls: 'text-rose-600', key: 'goals.onTrackOverdue' },
                achieved: { cls: 'text-emerald-600', key: 'goals.onTrackAchieved' },
              }
              const otc = goal.on_track ? onTrackConfig[goal.on_track] : null
              const GoalIcon = (goal.icon && ICON_MAP[goal.icon]) || Target
              return (
                <div key={goal.id} className="px-5 py-3 flex items-center gap-4">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-white"
                    style={{ backgroundColor: goal.color ?? '#6B7280' }}
                  >
                    <GoalIcon size={14} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-sm font-medium text-foreground truncate">{goal.name}</span>
                      <span className="text-xs font-bold tabular-nums text-foreground shrink-0">
                        {mask(formatCurrency(goal.current_amount, goal.currency, locale))} / {mask(formatCurrency(goal.target_amount, goal.currency, locale))}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-muted/60 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${progressColor}`}
                          style={{ width: `${Math.min(goal.percentage, 100)}%` }}
                        />
                      </div>
                      <span className="text-[11px] font-bold tabular-nums text-muted-foreground shrink-0">
                        {goal.percentage.toFixed(0)}%
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-[11px] text-muted-foreground">
                      {goal.monthly_contribution != null && goal.monthly_contribution > 0 && (
                        <span className="tabular-nums">
                          {mask(formatCurrency(goal.monthly_contribution, goal.currency, locale))}{t('goals.perMonth')}
                        </span>
                      )}
                      {otc && (
                        <span className={`font-medium ${otc.cls}`}>{t(otc.key)}</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Period Transactions */}
      <div>
        <div className="bg-card rounded-xl border border-border shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <p className="text-sm font-semibold text-foreground">{t('dashboard.periodTransactions')}</p>
            <button
              onClick={() => { setTxSortDesc(v => !v); setTxPage(1) }}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <ArrowUpDown size={13} />
              {txSortDesc ? t('dashboard.sortNewest') : t('dashboard.sortOldest')}
            </button>
          </div>
          {txListLoading ? (
            <div className="p-5 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : pagedRows.length > 0 ? (
            <>
              {isMobile ? (
                <div>
                  {pagedRows.map((row) => (
                    <div
                      key={row.key}
                      className={`flex items-center gap-3 pl-3 pr-3 py-3 border-b border-border last:border-0 bg-card ${
                        row.isProjected ? '' : 'cursor-pointer active:bg-muted/60'
                      }`}
                      onClick={() => {
                        if (row.isProjected) return
                        if (row.isShared) {
                          if (row.groupId) navigate(`/groups/${row.groupId}`)
                          return
                        }
                        const tx = currentMonthTxs?.items.find((t) => t.id === row.key)
                        if (tx) { setEditingTx(tx); setDialogOpen(true) }
                      }}
                    >
                      {/* Category Icon */}
                      <div className="shrink-0">
                        <CategoryIcon icon={row.categoryIcon} color={row.categoryColor} size="md" />
                      </div>

                      {/* Content */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <p className="text-sm font-semibold text-foreground truncate leading-tight">{row.description}</p>
                          {row.groupId && (
                            <span className="inline-flex items-center text-[9px] font-semibold uppercase tracking-wide text-violet-700 bg-violet-50 border border-violet-200 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-900 px-1 py-0.5 rounded-full shrink-0">
                              {row.isShared && row.parentOwnerName
                                ? t('splitGroups.sharedShortBadgeAuthor', { author: row.parentOwnerName })
                                : row.groupName ?? t('splitGroups.sharedShortBadge')}
                            </span>
                          )}
                          {row.isProjected && (
                            <ProjectedTransactionBadge />
                          )}
                          {row.installmentNumber != null && row.totalInstallments != null && (
                            <span className="inline-flex items-center text-[9px] font-bold tabular-nums text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/20 border border-amber-200 dark:border-amber-500/30 px-1 py-0.5 rounded-full shrink-0">
                              {row.installmentNumber}/{row.totalInstallments}
                            </span>
                          )}
                          {row.showPendingBadge && (
                            <span
                              title={t('transactions.pending')}
                              className="shrink-0 inline-flex items-center justify-center rounded-full border border-amber-200 bg-amber-50 p-0.5 dark:border-amber-500/30 dark:bg-amber-500/10"
                            >
                              <Clock size={12} className="text-amber-500" role="img" aria-label={t('transactions.pending')} />
                            </span>
                          )}
                          {row.isIgnored && (
                            <EyeClosed className="h-3 w-3 text-gray-500 shrink-0" />
                          )}
                          {row.attachmentCount > 0 && (
                            <Paperclip size={11} className="text-muted-foreground shrink-0" />
                          )}
                        </div>
                        {row.accountId && (() => {
                          const acc = accountsList?.find((a) => a.id === row.accountId)
                          if (!acc) return null
                          return (
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <AccountIcon account={acc} size="xs" />
                              <span className="text-xs text-muted-foreground truncate">{getAccountName(acc)}</span>
                            </div>
                          )
                        })()}
                        {!row.accountId && (
                          <p className="text-xs text-muted-foreground mt-0.5">{formatDate(row.date, dateLocale)}</p>
                        )}
                      </div>

                      {/* Amount */}
                      <div className="shrink-0 text-right">
                        <span className={`text-sm font-bold tabular-nums ${row.isIgnored ? 'text-gray-500' : row.type === 'credit' ? 'text-emerald-600' : 'text-rose-500'}`}>
                          {mask(`${row.isIgnored ? ' ' : row.type === 'credit' ? '+' : '\u2212'}${formatCurrency(Math.abs(row.amount), row.currency, locale)}`)}
                        </span>
                        {row.isShared && row.parentTotal != null && (
                          <div className="text-[10px] text-muted-foreground tabular-nums mt-0.5">
                            {t('splitGroups.sharedRowParent', {
                              total: formatCurrency(Math.abs(row.parentTotal), row.currency, locale),
                            })}
                          </div>
                        )}
                        {!row.isShared && row.ownerShare != null && (
                          <div className="text-[10px] text-muted-foreground tabular-nums mt-0.5">
                            {t('splitGroups.ownerRowYourShare', {
                              share: formatCurrency(Math.abs(row.ownerShare), row.currency, locale),
                            })}
                          </div>
                        )}
                        {!row.isShared && row.currency !== userCurrency && row.amountPrimary != null && (
                          <div className="text-[10px] text-muted-foreground tabular-nums mt-0.5">
                            {mask(formatCurrency(Math.abs(row.amountPrimary), userCurrency, locale))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border hover:bg-transparent">
                    <TableHead className="pl-5 text-xs font-medium text-muted-foreground hidden sm:table-cell">{t('transactions.date')}</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground">{t('transactions.description')}</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground hidden sm:table-cell">{t('transactions.account')}</TableHead>
                    <TableHead className="pr-5 text-right text-xs font-medium text-muted-foreground">{t('transactions.amount')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pagedRows.map((row) => (
                    <TableRow
                      key={row.key}
                      className={`border-b border-border last:border-0 ${
                        row.isProjected
                          ? ''
                          : row.isShared
                            ? 'cursor-pointer hover:bg-muted'
                            : 'cursor-pointer hover:bg-muted'
                      }`}
                      onClick={() => {
                        if (row.isProjected) return
                        if (row.isShared) {
                          // Shared rows belong to another user — open the
                          // group instead of the (locked) edit dialog.
                          if (row.groupId) navigate(`/groups/${row.groupId}`)
                          return
                        }
                        const tx = currentMonthTxs?.items.find((t) => t.id === row.key)
                        if (tx) { setEditingTx(tx); setDialogOpen(true) }
                      }}
                    >
                      <TableCell className="py-2.5 pl-5 text-sm text-muted-foreground tabular-nums whitespace-nowrap hidden sm:table-cell">
                        {formatDate(row.date, dateLocale)}
                      </TableCell>
                      <TableCell className="py-2.5 pl-5 sm:pl-0">
                        <div className="flex items-center gap-3">
                          <CategoryIcon icon={row.categoryIcon} color={row.categoryColor} size="lg" />
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-foreground truncate">{row.description}</p>
                              {row.groupId && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300 shrink-0 uppercase tracking-wide">
                                  {row.isShared && row.parentOwnerName
                                    ? t('splitGroups.sharedShortBadgeAuthor', { author: row.parentOwnerName })
                                    : row.groupName ?? t('splitGroups.sharedShortBadge')}
                                </span>
                              )}
                              {row.isProjected && (
                                <ProjectedTransactionBadge />
                              )}
                              {row.installmentNumber != null && row.totalInstallments != null && (
                                <span className="inline-flex items-center text-[10px] font-bold tabular-nums text-amber-700 dark:text-amber-400 bg-amber-100 dark:bg-amber-500/20 border border-amber-200 dark:border-amber-500/30 px-1.5 py-0.5 rounded-full shrink-0">
                                  {row.installmentNumber}/{row.totalInstallments}
                                </span>
                              )}
                              {row.showPendingBadge && (
                                <span
                                  title={t('transactions.pending')}
                                  className="shrink-0 inline-flex items-center justify-center rounded-full border border-amber-200 bg-amber-50 p-0.5 dark:border-amber-500/30 dark:bg-amber-500/10"
                                >
                                  <Clock size={12} className="text-amber-500" role="img" aria-label={t('transactions.pending')} />
                                </span>
                              )}
                              {row.isIgnored && (
                                <span className="ml-2 inline-flex items-center gap-1 text-xs text-gray-600 font-normal bg-gray-100 border border-gray-200 rounded px-1.5 py-0.5">
                                <EyeClosed className="h-3 w-3" />
                                {t('transactions.ignored')}
                                <span title={t('transactions.ignoreTransferHint')}><HelpCircle className="h-3 w-3 text-blue-400" /></span>
                                </span>
                              )}
                              {row.attachmentCount > 0 && (
                                <Paperclip size={12} className="text-muted-foreground shrink-0" />
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground sm:hidden">{formatDate(row.date, dateLocale)}</p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5 text-sm text-muted-foreground hidden sm:table-cell">
                        {(() => {
                          const acc = row.accountId
                            ? accountsList?.find((a) => a.id === row.accountId)
                            : undefined
                          if (!acc) return <span className="text-muted-foreground">—</span>
                          return (
                            <span className="flex items-center gap-2 min-w-0">
                              <AccountIcon account={acc} size="sm" />
                              <span className="truncate">{getAccountName(acc)}</span>
                            </span>
                          )
                        })()}
                      </TableCell>
                      <TableCell className="py-2.5 pr-5 text-right">
                        <span className={`text-sm font-semibold tabular-nums ${row.isIgnored ? 'text-gray-500' : row.type === 'credit' ? 'text-emerald-600' : 'text-rose-500'}`}>
                          {mask(`${row.isIgnored ? ' ' : row.type === 'credit' ? '+' : '-'}${formatCurrency(Math.abs(row.amount), row.currency, locale)}`)}
                        </span>
                        {row.isShared && row.parentTotal != null && (
                          <span className="block text-[10px] text-muted-foreground tabular-nums">
                            {t('splitGroups.sharedRowParent', {
                              total: formatCurrency(Math.abs(row.parentTotal), row.currency, locale),
                            })}
                          </span>
                        )}
                        {!row.isShared && row.ownerShare != null && (
                          <span className="block text-[10px] text-muted-foreground tabular-nums">
                            {t('splitGroups.ownerRowYourShare', {
                              share: formatCurrency(Math.abs(row.ownerShare), row.currency, locale),
                            })}
                          </span>
                        )}
                        {!row.isShared && row.currency !== userCurrency && row.amountPrimary != null && (
                          <span className="block text-[10px] text-muted-foreground tabular-nums">
                            {mask(formatCurrency(Math.abs(row.amountPrimary), userCurrency, locale))}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              )}
              {allDisplayRows.length > 10 && (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-5 py-4 border-t border-border">
                  <div className="hidden sm:block w-32" />
                  {txTotalPages > 1 ? (
                    <div className="flex items-center justify-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={txPage <= 1}
                        onClick={() => setTxPage(txPage - 1)}
                      >
                        {t('dashboard.previous')}
                      </Button>
                      <span className="text-sm text-muted-foreground">
                        {txPage} / {txTotalPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={txPage >= txTotalPages}
                        onClick={() => setTxPage(txPage + 1)}
                      >
                        {t('dashboard.next')}
                      </Button>
                    </div>
                  ) : (
                    <div className="hidden sm:block" />
                  )}

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{t('common.rowsPerPage', 'Rows per page')}</span>
                    <Select
                      value={String(txPerPage)}
                      onValueChange={(val) => {
                        const nextLimit = Number(val)
                        setTxPerPage(nextLimit)
                        setTxPage(1)
                        try {
                          localStorage.setItem('securo.dashboard.pageSize', String(nextLimit))
                        } catch {
                          // ignored
                        }
                      }}
                    >
                      <SelectTrigger className="w-[70px] h-8 text-xs">
                        <SelectValue placeholder={txPerPage} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-muted-foreground text-sm text-center py-8">{t('dashboard.noTransactions')}</p>
          )}
        </div>
      </div>

      <TransactionDrillDown
        filter={
          drillDown
            ? {
                ...drillDown,
                // Keep drill-downs consistent with the collection-scoped cards
                // they open from (e.g. "Categorize now").
                account_ids:
                  drillDown.account_ids ?? (acctIds && acctIds.length > 0 ? acctIds : undefined),
              }
            : null
        }
        onClose={() => setDrillDown(null)}
        onTransactionClick={(tx) => { setEditingTx(tx); setDialogOpen(true) }}
      />

      <TransactionDialog
        open={dialogOpen}
        onClose={() => { setDialogOpen(false); setEditingTx(null) }}
        transaction={editingTx}
        categories={categoriesList ?? []}
        categoryGroups={categoryGroupsList ?? []}
        accounts={(accountsList ?? []).map((a: { id: string; name: string; display_name?: string | null }) => ({ id: a.id, name: getAccountName(a) }))}
        onSave={(data) => {
          if (editingTx) updateMutation.mutate({ id: editingTx.id, ...data })
        }}
        onDelete={() => {
          if (editingTx) deleteMutation.mutate(editingTx.id)
        }}
        onUnlinkTransfer={(pairId) => unlinkTransferMutation.mutate(pairId)}
        onCreateRule={(tx) => {
          setDialogOpen(false)
          setEditingTx(null)
          handleCreateRuleFromTransaction(tx)
        }}
        loading={updateMutation.isPending || deleteMutation.isPending || unlinkTransferMutation.isPending}
        error={updateMutation.error ? extractApiError(updateMutation.error) : deleteMutation.error ? extractApiError(deleteMutation.error) : null}
        isSynced={editingTx?.source === 'sync'}
      />

      <RuleDialog
        key={createRuleOpen ? 'rule-open' : 'rule-closed'}
        open={createRuleOpen}
        onClose={() => { setCreateRuleOpen(false); setCreateRuleInitialData(undefined) }}
        rule={null}
        categories={categoriesList ?? []}
        categoryGroups={categoryGroupsList ?? []}
        accounts={(accountsList ?? []).map((a: { id: string; name: string; display_name?: string | null }) => ({ id: a.id, name: getAccountName(a) }))}
        payees={payeesList ?? []}
        onSave={(data) => createRuleMutation.mutate(data as Omit<Rule, 'id' | 'user_id'>)}
        loading={createRuleMutation.isPending}
        initialData={createRuleInitialData}
      />
    </div>
  )
}
