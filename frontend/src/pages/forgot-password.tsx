import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { auth as authApi, admin as adminApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { ShellLogo } from '@/components/shell-logo'
import { isServerUnreachable } from '@/lib/auth-errors'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import type { AxiosError } from 'axios'

export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const { resolvedTheme } = useTheme()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sent, setSent] = useState(false)

  useEffect(() => {
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [resolvedTheme])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await authApi.forgotPassword(email)
      // Always show the same "sent" state regardless of whether the email
      // exists — the backend responds identically either way, so this page
      // can't leak which addresses have an account.
      setSent(true)
    } catch (err) {
      const axiosErr = err as AxiosError
      if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setSent(true)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background px-4">
      <Card className="w-full max-w-[380px] shadow-sm">
        {sent ? (
          <>
            <div className="flex flex-col items-center pt-8 pb-2 px-8">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <ShellLogo size={22} className="text-primary" />
              </div>
              <h1 className="text-xl font-semibold tracking-tight text-center">{t('auth.forgotPasswordSentTitle')}</h1>
              <p className="text-sm text-muted-foreground mt-1 text-center">{t('auth.forgotPasswordSentDescription')}</p>
            </div>
            <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-6">
              <Link to="/login" className="text-sm text-primary font-medium hover:underline">
                {t('auth.backToLogin')}
              </Link>
            </CardFooter>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col items-center pt-8 pb-2 px-8">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <ShellLogo size={22} className="text-primary" />
              </div>
              <h1 className="text-xl font-semibold tracking-tight">{t('auth.forgotPassword')}</h1>
              <p className="text-sm text-muted-foreground mt-1 text-center">{t('auth.forgotPasswordDescription')}</p>
            </div>
            <CardContent className="space-y-4 px-8 pt-4">
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                  {error}
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-sm">{t('auth.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  autoFocus
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-2">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? t('common.loading') : t('auth.sendResetLink')}
              </Button>
              <Link to="/login" className="text-sm text-muted-foreground hover:text-foreground">
                {t('auth.backToLogin')}
              </Link>
            </CardFooter>
          </form>
        )}
      </Card>
    </div>
  )
}
