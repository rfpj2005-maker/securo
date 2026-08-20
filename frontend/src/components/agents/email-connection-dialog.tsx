import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { emailConnection } from '@/lib/api'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EmailConnectionDialog({ open, onOpenChange }: Props) {
  const { t } = useTranslation()
  const qc = useQueryClient()

  const [emailAddress, setEmailAddress] = useState('')
  const [imapHost, setImapHost] = useState('')
  const [imapPort, setImapPort] = useState('993')
  const [imapUseSsl, setImapUseSsl] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (open) {
      setEmailAddress('')
      setImapHost('')
      setImapPort('993')
      setImapUseSsl(true)
      setUsername('')
      setPassword('')
    }
  }, [open])

  const saveMut = useMutation({
    mutationFn: () =>
      emailConnection.connect({
        email_address: emailAddress.trim(),
        imap_host: imapHost.trim(),
        imap_port: Number(imapPort) || 993,
        imap_use_ssl: imapUseSsl,
        username: username.trim(),
        password,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-connection', 'status'] })
      onOpenChange(false)
      toast.success(t('agents.connections.email.connected', 'Email connected'))
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(detail || t('agents.connections.email.connectError', 'Could not connect — check the IMAP settings and password'))
    },
  })

  const submit = () => {
    if (!emailAddress.trim() || !imapHost.trim() || !username.trim() || !password) {
      toast.error(t('agents.connections.email.fieldsRequired', 'Fill in all fields'))
      return
    }
    saveMut.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{t('agents.connections.email.title', 'Email')}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid gap-2">
            <Label>{t('agents.connections.email.emailAddress', 'Email address')}</Label>
            <Input
              value={emailAddress}
              onChange={(e) => setEmailAddress(e.target.value)}
              placeholder="voce@ampararprotecao.com.br"
              type="email"
            />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="grid gap-2 col-span-2">
              <Label>{t('agents.connections.email.imapHost', 'IMAP server')}</Label>
              <Input value={imapHost} onChange={(e) => setImapHost(e.target.value)} placeholder="imap.hostinger.com" />
            </div>
            <div className="grid gap-2">
              <Label>{t('agents.connections.email.imapPort', 'Port')}</Label>
              <Input value={imapPort} onChange={(e) => setImapPort(e.target.value)} inputMode="numeric" />
            </div>
          </div>
          <div className="grid gap-2">
            <Label>{t('agents.connections.email.username', 'Username')}</Label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t('agents.connections.email.usernameHint', 'Usually the same as the email address')}
            />
          </div>
          <div className="grid gap-2">
            <Label>{t('agents.connections.email.password', 'Password')}</Label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={imapUseSsl} onCheckedChange={(v) => setImapUseSsl(!!v)} />
            <Label className="cursor-pointer" onClick={() => setImapUseSsl(!imapUseSsl)}>
              {t('agents.connections.email.useSsl', 'Use SSL (recommended)')}
            </Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('agents.connections.cancel')}
          </Button>
          <Button onClick={submit} disabled={saveMut.isPending}>
            {saveMut.isPending ? t('agents.connections.saving') : t('agents.connections.email.connect', 'Connect')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
