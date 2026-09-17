import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useTheme } from 'next-themes'
import { auth as authApi, admin as adminApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { PasswordInput } from '@/components/ui/password-input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { ShellLogo } from '@/components/shell-logo'
import { isServerUnreachable } from '@/lib/auth-errors'
import { setThemeBasedOnSystem } from '@/lib/theme-utils'
import type { AxiosError } from 'axios'

export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    adminApi.defaultColors().then(({ light, dark }) => {
      setThemeBasedOnSystem(light, dark, resolvedTheme)
    }).catch(() => {})
  }, [resolvedTheme])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }
    if (password.length < 8) {
      setError(t('auth.passwordTooShort'))
      return
    }

    setIsLoading(true)
    try {
      await authApi.resetPassword(token, password)
      setDone(true)
    } catch (err) {
      const axiosErr = err as AxiosError
      if (isServerUnreachable(err)) {
        setError(t('auth.serverError'))
      } else if (axiosErr?.response?.status === 429) {
        setError(t('auth.tooManyAttempts'))
      } else {
        setError(t('auth.resetPasswordInvalidToken'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background px-4">
        <Card className="w-full max-w-[380px] shadow-sm">
          <div className="flex flex-col items-center pt-8 pb-2 px-8">
            <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <ShellLogo size={22} className="text-primary" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-center">{t('auth.resetPasswordInvalidToken')}</h1>
          </div>
          <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-6">
            <Link to="/forgot-password" className="text-sm text-primary font-medium hover:underline">
              {t('auth.forgotPassword')}
            </Link>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background px-4">
      <Card className="w-full max-w-[380px] shadow-sm">
        {done ? (
          <>
            <div className="flex flex-col items-center pt-8 pb-2 px-8">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <ShellLogo size={22} className="text-primary" />
              </div>
              <h1 className="text-xl font-semibold tracking-tight text-center">{t('auth.passwordChanged')}</h1>
            </div>
            <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-6">
              <Button className="w-full" onClick={() => navigate('/login')}>
                {t('auth.login')}
              </Button>
            </CardFooter>
          </>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col items-center pt-8 pb-2 px-8">
              <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <ShellLogo size={22} className="text-primary" />
              </div>
              <h1 className="text-xl font-semibold tracking-tight">{t('auth.resetPasswordTitle')}</h1>
              <p className="text-sm text-muted-foreground mt-1 text-center">{t('auth.resetPasswordDescription')}</p>
            </div>
            <CardContent className="space-y-4 px-8 pt-4">
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-lg">
                  {error}
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-sm">{t('auth.newPassword')}</Label>
                <PasswordInput
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirmPassword" className="text-sm">{t('auth.confirmPassword')}</Label>
                <PasswordInput
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4 px-8 pb-8 pt-2">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? t('common.loading') : t('auth.resetPasswordSubmit')}
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
